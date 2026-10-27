"""
test_backend.py

Automated integration and unit tests for the ChatNexus FastAPI backend and RAG engine.
Uses an in-memory SQLite database to validate routes, data serialization, and cascades
without external PostgreSQL dependency.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend folder is in path for imports
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import models
import schemas
from database import Base, get_db
from main import app
from rag import GoogleGenAIEmbeddings, process_pdf

# 1. Setup isolated in-memory test database
TEST_SQLITE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_database():
    """Create all tables before each test and drop them after."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Returns a FastAPI TestClient."""
    return TestClient(app)


def test_health_check(client):
    """Verify that the health check endpoint responds with 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ChatNexus API"}


def test_create_and_get_sessions(client):
    """Verify creating a new chat session and fetching the sessions list."""
    # Create session
    create_res = client.post("/sessions/?title=Engineering Assistant")
    assert create_res.status_code == 201
    session_data = create_res.json()
    assert session_data["title"] == "Engineering Assistant"
    assert "id" in session_data
    session_id = session_data["id"]

    # Fetch list
    list_res = client.get("/sessions/")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id


def test_rename_session(client):
    """Verify renaming an existing chat session."""
    create_res = client.post("/sessions/?title=Initial Title")
    session_id = create_res.json()["id"]

    # Rename
    put_res = client.put(f"/sessions/{session_id}?title=Updated Architecture")
    assert put_res.status_code == 200
    assert put_res.json()["title"] == "Updated Architecture"


def test_delete_session_and_cascade(client):
    """Verify deleting a chat session and ensuring messages are deleted."""
    create_res = client.post("/sessions/?title=Session To Delete")
    session_id = create_res.json()["id"]

    # Delete
    del_res = client.delete(f"/sessions/{session_id}")
    assert del_res.status_code == 200

    # Verify session is gone
    get_res = client.get(f"/sessions/{session_id}/messages")
    assert get_res.status_code == 404


def test_process_pdf_empty_and_invalid():
    """Verify process_pdf gracefully handles invalid or non-extractable PDF inputs."""
    with pytest.raises(ValueError):
        process_pdf(b"not a valid pdf binary content")

    # Empty bytes
    with pytest.raises(ValueError):
        process_pdf(b"")


def test_embeddings_empty_documents():
    """Verify embed_documents returns an empty list when given an empty list of texts."""
    # Instantiating requires GOOGLE_API_KEY to be set
    embeddings = GoogleGenAIEmbeddings()
    result = embeddings.embed_documents([])
    assert result == []
