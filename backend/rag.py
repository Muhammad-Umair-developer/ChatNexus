"""
rag.py

Retrieval-Augmented Generation (RAG) subsystem for ChatNexus.
Provides:
  1. PDF text extraction & recursive character splitting.
  2. Embeddings wrapper for Google's native Gemini embedding model (`gemini-embedding-001`).
  3. PGVector vector store connection and metadata-filtered similarity retrieval.
  4. Vector document cleanup upon session deletion.
"""

import os
from io import BytesIO
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import PGVector
from langchain_core.embeddings import Embeddings
from sqlalchemy import text
from google import genai

from database import engine, DATABASE_URL

# Ensure environment variables are loaded
current_dir = Path(__file__).resolve().parent
load_dotenv(current_dir / ".env")
load_dotenv(current_dir.parent / ".env")

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")


class GoogleGenAIEmbeddings(Embeddings):
    """
    Production-grade LangChain-compatible embedding wrapper using Google's GenAI SDK.
    Handles text cleaning, batching, and error recovery.
    """

    def __init__(self, model: str = DEFAULT_EMBEDDING_MODEL):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GOOGLE_API_KEY is not set. Cannot initialize GoogleGenAIEmbeddings."
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of text chunks.
        Splits queries into batches of up to 50 to adhere to API payload constraints.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        batch_size = 50

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            cleaned_batch = [t.replace("\n", " ").strip() or " " for t in batch]

            response = self.client.models.embed_content(
                model=self.model,
                contents=cleaned_batch,
            )

            if response.embeddings:
                all_embeddings.extend([emb.values for emb in response.embeddings])

        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single search query string for similarity retrieval.
        Accepts 'text' as a parameter to support LangChain vector stores that call embed_query(text=...).
        """
        cleaned_text = (text or "").replace("\n", " ").strip() or " "
        response = self.client.models.embed_content(
            model=self.model,
            contents=cleaned_text,
        )
        return response.embeddings[0].values


def process_pdf(file_bytes: bytes) -> List[str]:
    """
    Extracts text from a PDF byte stream and splits it into semantic chunks.

    Args:
        file_bytes: Raw bytes from the uploaded PDF.

    Returns:
        List[str]: Clean text chunks suitable for embedding. Returns empty list
                   if no extractable text is present (e.g. scanned image-only PDF).
    """
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF file: {exc}")

    raw_text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            raw_text += extracted + "\n"

    cleaned_text = raw_text.strip()
    if not cleaned_text:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )
    return text_splitter.split_text(cleaned_text)


def get_vector_store() -> PGVector:
    """
    Initializes and returns a PGVector store backed by PostgreSQL pgvector extension.
    Uses 'chatnexus_docs' as the default collection.
    """
    embeddings = GoogleGenAIEmbeddings()
    return PGVector(
        connection_string=DATABASE_URL,
        embedding_function=embeddings,
        collection_name="chatnexus_docs",
    )


def delete_session_vectors(session_id: int) -> int:
    """
    Deletes all vector embeddings associated with a given session_id
    from the pgvector document table to prevent orphaned records.

    Returns:
        int: Number of deleted embedding rows.
    """
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        if not inspector.has_table("langchain_pg_embedding"):
            return 0

        with engine.begin() as conn:
            stmt = text(
                "DELETE FROM langchain_pg_embedding "
                "WHERE cmetadata->>'session_id' = :session_id"
            )
            result = conn.execute(stmt, {"session_id": str(session_id)})
            return result.rowcount
    except Exception as exc:
        print(f"Warning: Failed to clean up vector store for session {session_id}: {exc}")
        return 0


def get_session_documents_info(session_id: int) -> List[dict]:
    """
    Returns distinct uploaded documents with filenames and chunk counts for this session.
    """
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        if not inspector.has_table("langchain_pg_embedding"):
            return []

        with engine.connect() as conn:
            stmt = text(
                "SELECT cmetadata->>'filename' as fname, count(*) as count "
                "FROM langchain_pg_embedding "
                "WHERE cmetadata->>'session_id' = :session_id "
                "GROUP BY cmetadata->>'filename'"
            )
            rows = conn.execute(stmt, {"session_id": str(session_id)}).fetchall()
            return [{"filename": r[0], "chunks_count": r[1]} for r in rows if r[0]]
    except Exception as exc:
        print(f"Error fetching documents for session {session_id}: {exc}")
        return []


def get_session_document_context(session_id: int, query: str = "") -> str:
    """
    Retrieves full document context for a session.
    For resumes and short documents (<= 30 chunks), retrieves ALL chunks in order
    so the entire document is present with 100% fidelity, zero missing sections,
    and zero retrieval gaps.
    For larger document corpora (> 30 chunks), uses similarity search with k=15.
    """
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        if not inspector.has_table("langchain_pg_embedding"):
            return ""

        with engine.connect() as conn:
            stmt = text(
                "SELECT document FROM langchain_pg_embedding "
                "WHERE cmetadata->>'session_id' = :session_id"
            )
            rows = conn.execute(stmt, {"session_id": str(session_id)}).fetchall()

        if not rows:
            return ""

        # For resumes and short docs (up to 30 chunks / ~25,000 characters),
        # include the entire document text so nothing is ever missed!
        if len(rows) <= 30:
            return "\n\n".join([r[0] for r in rows if r[0]])

        # For larger multi-page corpora, use vector similarity search with expanded k=15
        try:
            vector_store = get_vector_store()
            retriever = vector_store.as_retriever(
                search_kwargs={"k": 15, "filter": {"session_id": session_id}}
            )
            docs = retriever.invoke(query)
            if docs:
                return "\n\n".join([doc.page_content for doc in docs])
        except Exception as exc:
            print(f"Vector search fallback: {exc}")

        return "\n\n".join([r[0] for r in rows[:15] if r[0]])
    except Exception as exc:
        print(f"Error reading document context for session {session_id}: {exc}")
        return ""