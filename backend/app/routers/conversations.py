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
from app.middleware.auth import require_api_key

router = APIRouter()


class ConversationCreate(BaseModel):
    customer_id: str


class ConversationUpdate(BaseModel):
    status: Optional[ConversationStatus] = None
    csat_score: Optional[int] = None  # Customer satisfaction score (1-5)


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
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
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
    customer_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all conversations with optional status and customer_id filters."""
    query = db.query(Conversation)
    
    if status:
        query = query.filter(Conversation.status == status)
    
    if customer_id:
        query = query.filter(Conversation.customer_id == customer_id)
    
    conversations = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()
    
    # Optimize: Batch load messages for all conversations to avoid N+1 queries
    conversation_ids = [conv.id for conv in conversations]
    messages_by_conv = {}
    if conversation_ids:
        all_messages = db.query(Message).filter(
            Message.conversation_id.in_(conversation_ids)
        ).order_by(Message.created_at).all()
        
        # Group messages by conversation_id
        for msg in all_messages:
            if msg.conversation_id not in messages_by_conv:
                messages_by_conv[msg.conversation_id] = []
            messages_by_conv[msg.conversation_id].append(msg)
    
    # Enrich with message count and last message
    result = []
    for conv in conversations:
        messages = messages_by_conv.get(conv.id, [])
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
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
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
    # Verify conversation exists
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
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
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Update conversation status (e.g., resolve, escalate)."""
    # Verify conversation exists
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if update.status:
        conversation.status = update.status
        if update.status == ConversationStatus.RESOLVED:
            conversation.resolved_at = datetime.utcnow()
    
    if update.csat_score is not None:
        # Validate CSAT score (1-5)
        if 1 <= update.csat_score <= 5:
            conversation.csat_score = update.csat_score
            # Save evaluation metric
            from app.services.evaluation_service import save_evaluation_metrics
            save_evaluation_metrics(
                message_id=None,
                conversation_id=conversation.id,
                bleu_score=None,
                semantic_similarity=None,
                csat_score=update.csat_score,
                db=db
            )
    
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

