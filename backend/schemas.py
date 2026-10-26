from pydantic import BaseModel
from datetime import datetime
from typing import List

# 1. Base classes define common attributes to keep code DRY
class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(MessageBase):
    pass

# 2. Response schemas dictate exactly what the API returns, filtering out sensitive DB fields
class MessageResponse(MessageBase):
    id: int
    session_id: int
    created_at: datetime

    class Config:
        # Allows Pydantic to read data directly from SQLAlchemy ORM models
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True