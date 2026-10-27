"""
models.py

SQLAlchemy ORM models for ChatNexus.
Defines chat sessions and individual conversation messages with relationship mappings.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class ChatSession(Base):
    """
    Represents an isolated chat session / conversation thread.
    Automatically cascades deletion to all child messages.
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, default="New Chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Bi-directional relationship with Message; cascades deletion cleanly
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """
    Represents an individual message (user query or assistant response) within a session.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    file_name = Column(String, nullable=True)  # Attached document name if uploaded
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Reference back to the parent session
    session = relationship("ChatSession", back_populates="messages")