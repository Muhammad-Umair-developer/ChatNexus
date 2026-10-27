from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db
import models, schemas
from llm_service import generate_ai_response
from fastapi.responses import StreamingResponse
import json

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="ChatNexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

@app.get("/sessions/")
def get_sessions(db: Session = Depends(get_db)):
    """Fetch all chat sessions ordered by newest first."""
    return db.query(models.ChatSession).order_by(models.ChatSession.created_at.desc()).all()

@app.post("/sessions/", response_model=schemas.ChatSessionResponse)
def create_chat_session(title: str = "New Chat", db: Session = Depends(get_db)):
    new_session = models.ChatSession(title=title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@app.get("/sessions/{session_id}/messages")
def get_messages(session_id: int, db: Session = Depends(get_db)):
    """Fetch all messages for a specific session."""
    return db.query(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at).all()

@app.post("/sessions/{session_id}/messages", response_model=schemas.MessageResponse)
def add_message(session_id: int, message: schemas.MessageCreate, db: Session = Depends(get_db)):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Auto-title session if it's still named "New Chat"
    if session.title == "New Chat" and message.content:
        session.title = message.content[:30] + ("..." if len(message.content) > 30 else "")
        db.commit()

    user_msg = models.Message(session_id=session_id, role=message.role, content=message.content)
    db.add(user_msg)
    db.commit()

    history = db.query(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at).all()
    ai_text = generate_ai_response(chat_history=history[:-1], new_message=message.content)

    ai_msg = models.Message(session_id=session_id, role="assistant", content=ai_text)
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    
    return ai_msg

@app.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Deletes a chat session and cascades to its messages."""
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete associated messages first if cascade isn't set in models
    db.query(models.Message).filter(models.Message.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "Session deleted successfully"}

@app.post("/sessions/{session_id}/stream")
def stream_message(session_id: int, message: schemas.MessageCreate, db: Session = Depends(get_db)):
    """
    Streams the LLM response chunk-by-chunk using Server-Sent Events (SSE).
    """
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Auto-title session if it's still named "New Chat"
    if session.title == "New Chat" and message.content:
        session.title = message.content[:30] + ("..." if len(message.content) > 30 else "")
        db.commit()

    # Save User Message
    user_msg = models.Message(session_id=session_id, role=message.role, content=message.content)
    db.add(user_msg)
    db.commit()

    # Fetch History
    history = db.query(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at).all()

    def generate():
        full_response = ""
        from llm_service import llm 
        
        messages_payload = []
        for msg in history[:-1]:
            messages_payload.append((msg.role, msg.content))
        messages_payload.append(("user", message.content))

        for chunk in llm.stream(messages_payload):
            token = chunk.content
            if token:
                full_response += token
                # FIX: JSON encode the token to safely escape all newlines and quotes
                yield f"data: {json.dumps(token)}\n\n"

        ai_msg = models.Message(session_id=session_id, role="assistant", content=full_response)
        db.add(ai_msg)
        db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.put("/sessions/{session_id}")
def rename_session(session_id: int, title: str, db: Session = Depends(get_db)):
    """Updates the title of an existing chat session."""
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.title = title
    db.commit()
    db.refresh(session)
    return session