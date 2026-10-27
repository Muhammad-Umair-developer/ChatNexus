"""
schemas.py

Pydantic validation schemas for ChatNexus API requests and responses.
Uses Pydantic v2 ConfigDict for clean SQLAlchemy ORM serialization.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MessageBase(BaseModel):
    """Common message attributes."""
    role: str = Field(..., description="Message author role: 'user' or 'assistant'")
    content: str = Field(..., description="The message text content")
    file_name: Optional[str] = Field(None, description="Optional attached document name")


class MessageCreate(MessageBase):
    """Schema for submitting a new message."""
    pass


class MessageResponse(MessageBase):
    """Schema for returning message records to the frontend."""
    id: int
    session_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionCreate(BaseModel):
    """Schema for creating a new chat session."""
    title: Optional[str] = Field("New Chat", description="Initial session title")


class ChatSessionResponse(BaseModel):
    """Schema for returning session details with optional child messages."""
    id: int
    title: str
    created_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    """Response payload returned after document indexing into pgvector."""
    filename: str
    chunks_count: int
    message: str