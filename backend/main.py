from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, get_db
import models, schemas
from llm_service import generate_ai_response

# Initialize database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ChatNexus API")

@app.post("/sessions/", response_model=schemas.ChatSessionResponse)
def create_chat_session(title: str, db: Session = Depends(get_db)):
    """
    Creates a new chat session.
    Time Complexity: O(1) insertion.
    """
    new_session = models.ChatSession(title=title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@app.post("/sessions/{session_id}/messages", response_model=schemas.MessageResponse)
def add_message(session_id: int, message: schemas.MessageCreate, db: Session = Depends(get_db)):
    """
    Appends a message, queries the LLM, and saves the response.
    """
    # 1. Verify session exists
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 2. Save User Message
    user_msg = models.Message(session_id=session_id, role=message.role, content=message.content)
    db.add(user_msg)
    db.commit()

    # 3. Fetch History & Generate AI Response
    history = db.query(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at).all()
    ai_text = generate_ai_response(chat_history=history[:-1], new_message=message.content)

    # 4. Save AI Message
    ai_msg = models.Message(session_id=session_id, role="assistant", content=ai_text)
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    
    return ai_msg