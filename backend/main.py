"""
main.py

FastAPI entry point for the ChatNexus API.
Provides REST endpoints for:
  - Chat session management (create, list, rename, delete with cascading).
  - Conversation history retrieval.
  - PDF document upload & pgvector indexing for RAG.
  - Server-Sent Events (SSE) token-by-token streaming with Gemini 2.5 Flash.
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.documents import Document
from sqlalchemy.orm import Session

# Ensure the backend directory is in sys.path for both module and standalone execution
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
import schemas
from database import SessionLocal, engine, get_db
from llm_service import SYSTEM_PERSONA, fallback_llm, generate_ai_response, llm
from rag import (
    delete_session_vectors,
    get_session_document_context,
    get_session_documents_info,
    get_vector_store,
    process_pdf,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChatNexusAPI")

# Ensure database tables are created on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ChatNexus API",
    description="Enterprise-grade AI Assistant API powered by FastAPI, pgvector, and Gemini 2.5 Flash",
    version="2.0.0",
)

# CORS configuration supporting standard Vite and React development ports
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for Docker / orchestration liveness probes."""
    return {"status": "ok", "service": "ChatNexus API"}


@app.get("/sessions/", response_model=List[schemas.ChatSessionResponse], tags=["Sessions"])
def get_sessions(db: Session = Depends(get_db)):
    """Fetch all chat sessions ordered by most recently created first."""
    return db.query(models.ChatSession).order_by(models.ChatSession.created_at.desc()).all()


@app.post("/sessions/", response_model=schemas.ChatSessionResponse, status_code=status.HTTP_201_CREATED, tags=["Sessions"])
def create_chat_session(
    title: str = Query("New Chat", description="Title of the new chat session"),
    db: Session = Depends(get_db),
):
    """Creates a new empty chat session."""
    new_session = models.ChatSession(title=title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@app.delete("/sessions/{session_id}", tags=["Sessions"])
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """
    Deletes a chat session, automatically cascades to all messages,
    and removes corresponding vector embeddings from pgvector.
    """
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    # 1. Clean up RAG vector embeddings for this session
    cleaned_vectors = delete_session_vectors(session_id)
    logger.info(f"Purged {cleaned_vectors} vector embeddings for session {session_id}.")

    # 2. Delete session (ORM relationship cascades to messages)
    db.delete(session)
    db.commit()

    return {"message": f"Session {session_id} and associated documents deleted successfully."}


@app.put("/sessions/{session_id}", response_model=schemas.ChatSessionResponse, tags=["Sessions"])
def rename_session(
    session_id: int,
    title: str = Query(..., min_length=1, description="New title for the chat session"),
    db: Session = Depends(get_db),
):
    """Updates the title of an existing chat session."""
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    session.title = title.strip()
    db.commit()
    db.refresh(session)
    return session


@app.get("/sessions/{session_id}/messages", response_model=List[schemas.MessageResponse], tags=["Messages"])
def get_messages(session_id: int, db: Session = Depends(get_db)):
    """Fetch all messages for a specific session ordered chronologically."""
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    return (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )


@app.post("/sessions/{session_id}/messages", response_model=schemas.MessageResponse, tags=["Messages"])
def add_message(
    session_id: int,
    message: schemas.MessageCreate,
    db: Session = Depends(get_db),
):
    """
    Standard synchronous message endpoint.
    Appends the user message, requests an AI completion, stores it, and returns the AI message.
    """
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    # Auto-generate meaningful session title from first prompt if title is default
    if session.title == "New Chat" and message.content.strip():
        preview = message.content.strip()[:30]
        session.title = preview + ("..." if len(message.content.strip()) > 30 else "")
        db.commit()

    # Commit user message
    user_msg = models.Message(
        session_id=session_id,
        role=message.role,
        content=message.content,
        file_name=getattr(message, "file_name", None),
    )
    db.add(user_msg)
    db.commit()

    # Retrieve history prior to current message for context
    history = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )
    ai_text = generate_ai_response(chat_history=history[:-1], new_message=message.content)

    # Commit assistant response
    ai_msg = models.Message(session_id=session_id, role="assistant", content=ai_text)
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    return ai_msg


@app.post(
    "/sessions/{session_id}/upload",
    response_model=schemas.DocumentUploadResponse,
    tags=["RAG Documents"],
)
async def upload_document(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Receives an uploaded PDF, extracts text, chunks it, and indexes
    the vector embeddings into pgvector tagged with this session_id.
    """
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF files are supported.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        chunks = process_pdf(file_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading PDF: {exc}",
        )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF contains no extractable text (it may be a scanned image or empty).",
        )

    docs = [
        Document(
            page_content=chunk,
            metadata={"session_id": session_id, "filename": file.filename},
        )
        for chunk in chunks
    ]

    try:
        vector_store = get_vector_store()
        vector_store.add_documents(docs)
    except Exception as exc:
        logger.error(f"Failed to embed documents into pgvector: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector indexing failed: {exc}",
        )

    # Auto-update session title if default
    if session.title in ("New Chat", "New Document Chat") or session.title.startswith("New "):
        clean_name = file.filename.rsplit(".", 1)[0]
        session.title = f"Doc: {clean_name[:24]}"
        db.commit()

    return schemas.DocumentUploadResponse(
        filename=file.filename,
        chunks_count=len(chunks),
        message=f"Successfully indexed {len(chunks)} chunks into pgvector for session {session_id}.",
    )


@app.get("/sessions/{session_id}/documents", tags=["RAG Documents"])
def get_session_documents(session_id: int, db: Session = Depends(get_db)):
    """Fetch distinct uploaded documents indexed for this session."""
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    return get_session_documents_info(session_id)


@app.post("/sessions/{session_id}/stream", tags=["Streaming"])
def stream_message(
    session_id: int,
    message: schemas.MessageCreate,
    db: Session = Depends(get_db),
):
    """
    Streams the LLM response token-by-token using Server-Sent Events (SSE).
    Injects RAG context retrieved from pgvector if relevant documents were uploaded.
    """
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    # Auto-generate meaningful session title from first prompt
    if session.title == "New Chat" and message.content.strip():
        preview = message.content.strip()[:30]
        session.title = preview + ("..." if len(message.content.strip()) > 30 else "")
        db.commit()

    # Commit the incoming user message
    user_msg = models.Message(
        session_id=session_id,
        role=message.role,
        content=message.content,
        file_name=getattr(message, "file_name", None),
    )
    db.add(user_msg)
    db.commit()

    # Snapshot history prior to current message
    history_records = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )
    # Exclude the latest user message which we will append explicitly
    past_messages = [(msg.role, msg.content) for msg in history_records[:-1]]

    def generate():
        """
        Generator executing inside the StreamingResponse.
        Uses a dedicated SessionLocal instance to ensure connection safety across generator scope.
        """
        full_response = ""
        context = ""

        # 1. Retrieve Comprehensive Document Context (100% recall for resumes & short docs)
        try:
            context = get_session_document_context(session_id, message.content)
        except Exception as exc:
            logger.warning(f"Document context retrieval failed: {exc}")
            context = ""

        # 2. Build Payload with System Persona & Strict Anti-Hallucination Guardrails
        messages_payload = []
        if context:
            system_instruction = (
                f"{SYSTEM_PERSONA}\n\n"
                "====================================================================\n"
                "VERIFIED DOCUMENT CONTENT (UPLOADED RESUME / FILE):\n"
                f"{context}\n"
                "====================================================================\n\n"
                "STRICT GROUNDING & ZERO-HALLUCINATION INSTRUCTIONS:\n"
                "1. EXCLUSIVELY rely on the verified document context above to answer all questions.\n"
                "2. Do NOT extrapolate, invent, hallucinate, or make assumptions. Every single fact, skill, date, company name, degree, institution, metric, or detail must be directly and explicitly stated in the context.\n"
                "3. If the user asks for information NOT contained in the document (such as undisclosed contact details, unlisted technologies, GPA, or references), you MUST explicitly state: 'The uploaded document does not mention [topic].' Do NOT attempt to guess or invent an answer.\n"
                "4. Completeness: When asked to list or summarize experience, skills, projects, or education, review the entire document context carefully so no factual information is omitted.\n"
                "5. Structure: Provide well-formatted, professional responses using Markdown bullet points and headers."
            )
        else:
            system_instruction = SYSTEM_PERSONA

        messages_payload.append(("system", system_instruction))

        # Re-attach past conversation history
        for role, content in past_messages:
            messages_payload.append((role, content))

        # Append latest user prompt
        messages_payload.append(("user", message.content))

        # 3. Stream Response Chunks with automatic fallback on quota limits
        try:
            for chunk in llm.stream(messages_payload):
                token = chunk.content if isinstance(chunk.content, str) else str(chunk.content or "")
                if token:
                    full_response += token
                    yield f"data: {json.dumps(token)}\n\n"
        except Exception as exc:
            if ("RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)) and not full_response:
                logger.warning("Primary LLM quota reached, switching to fallback model...")
                try:
                    for chunk in fallback_llm.stream(messages_payload):
                        token = chunk.content if isinstance(chunk.content, str) else str(chunk.content or "")
                        if token:
                            full_response += token
                            yield f"data: {json.dumps(token)}\n\n"
                except Exception as fb_exc:
                    logger.error(f"Fallback LLM failed: {fb_exc}", exc_info=True)
                    err_msg = f"API Quota Limit: {str(fb_exc)}"
                    full_response = err_msg
                    yield f"data: {json.dumps(err_msg)}\n\n"
            else:
                logger.error(f"Error during LLM streaming: {exc}", exc_info=True)
                err_msg = f"Streaming Error: {str(exc)}"
                full_response = err_msg
                yield f"data: {json.dumps(err_msg)}\n\n"

        # 4. Commit complete assistant response to database using dedicated session
        generator_db = SessionLocal()
        try:
            if full_response.strip():
                ai_msg = models.Message(
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                )
                generator_db.add(ai_msg)
                generator_db.commit()
        except Exception as exc:
            logger.error(f"Failed to persist assistant response: {exc}", exc_info=True)
            generator_db.rollback()
        finally:
            generator_db.close()

    return StreamingResponse(generate(), media_type="text/event-stream")