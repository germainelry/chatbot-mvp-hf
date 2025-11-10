"""
Conversation management endpoints.
Handles customer conversation lifecycle and status management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import Conversation, ConversationStatus, Message

router = APIRouter()


class ConversationCreate(BaseModel):
    customer_id: str


class ConversationUpdate(BaseModel):
    status: Optional[ConversationStatus] = None


class MessageResponse(BaseModel):
    id: int
    content: str
    message_type: str
    confidence_score: Optional[float]
    created_at: datetime
    original_ai_content: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    customer_id: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    message_count: int = 0
    last_message: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db)
):
    """Create a new customer conversation."""
    db_conversation = Conversation(
        customer_id=conversation.customer_id,
        status=ConversationStatus.ACTIVE
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    
    return ConversationResponse(
        id=db_conversation.id,
        customer_id=db_conversation.customer_id,
        status=db_conversation.status,
        created_at=db_conversation.created_at,
        updated_at=db_conversation.updated_at,
        resolved_at=db_conversation.resolved_at,
        message_count=0,
        last_message=None
    )


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    status: Optional[ConversationStatus] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all conversations with optional status filter."""
    query = db.query(Conversation)
    
    if status:
        query = query.filter(Conversation.status == status)
    
    conversations = query.order_by(Conversation.updated_at.desc()).limit(limit).all()
    
    # Enrich with message count and last message
    result = []
    for conv in conversations:
        messages = db.query(Message).filter(Message.conversation_id == conv.id).all()
        last_msg = messages[-1].content if messages else None
        
        result.append(ConversationResponse(
            id=conv.id,
            customer_id=conv.customer_id,
            status=conv.status,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            resolved_at=conv.resolved_at,
            message_count=len(messages),
            last_message=last_msg
        ))
    
    return result


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific conversation by ID."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).all()
    last_msg = messages[-1].content if messages else None
    
    return ConversationResponse(
        id=conversation.id,
        customer_id=conversation.customer_id,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        resolved_at=conversation.resolved_at,
        message_count=len(messages),
        last_message=last_msg
    )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Get all messages for a conversation."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    return messages


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update: ConversationUpdate,
    db: Session = Depends(get_db)
):
    """Update conversation status (e.g., resolve, escalate)."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if update.status:
        conversation.status = update.status
        if update.status == ConversationStatus.RESOLVED:
            conversation.resolved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conversation)
    
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).all()
    last_msg = messages[-1].content if messages else None
    
    return ConversationResponse(
        id=conversation.id,
        customer_id=conversation.customer_id,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        resolved_at=conversation.resolved_at,
        message_count=len(messages),
        last_message=last_msg
    )

