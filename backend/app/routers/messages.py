"""
Message management endpoints.
Handles sending customer messages and agent responses.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models import Message, MessageType, Conversation

router = APIRouter()


class MessageCreate(BaseModel):
    conversation_id: int
    content: str
    message_type: MessageType
    confidence_score: Optional[float] = None
    original_ai_content: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    content: str
    message_type: MessageType
    confidence_score: Optional[float]
    created_at: datetime
    original_ai_content: Optional[str]

    class Config:
        from_attributes = True


@router.post("", response_model=MessageResponse)
async def create_message(
    message: MessageCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new message in a conversation.
    Supports all message types: customer, AI draft, agent edited, final.
    """
    # Verify conversation exists
    conversation = db.query(Conversation).filter(
        Conversation.id == message.conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create message
    db_message = Message(
        conversation_id=message.conversation_id,
        content=message.content,
        message_type=message.message_type,
        confidence_score=message.confidence_score,
        original_ai_content=message.original_ai_content
    )
    
    db.add(db_message)
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_message)
    
    return db_message


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific message by ID."""
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return message

