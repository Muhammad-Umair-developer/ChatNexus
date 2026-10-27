"""
database.py

Database configuration, SQLAlchemy engine initialization, and session dependency.
Supports PostgreSQL with pgvector for ChatNexus chat history and RAG embeddings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Environment discovery: Check backend/.env first, then root .env
current_dir = Path(__file__).resolve().parent
backend_env = current_dir / ".env"
root_env = current_dir.parent / ".env"

if backend_env.exists():
    load_dotenv(backend_env)
elif root_env.exists():
    load_dotenv(root_env)
else:
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise EnvironmentError(
        "DATABASE_URL is not set in the environment or .env file. "
        "Please provide a valid PostgreSQL connection string, e.g., "
        "'postgresql+psycopg2://user:postgres@127.0.0.1:5433/chatnexus'."
    )

# 2. Initialize SQLAlchemy engine
# pool_pre_ping checks connection liveness before executing queries, preventing stale connection errors
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# 3. Session factory for thread-safe session instances
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Declarative Base for ORM entity definitions
Base = declarative_base()


def get_db():
    """
    FastAPI dependency yielding a SQLAlchemy session.
    Ensures the session is cleanly closed when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()