"""
Conversation management endpoints.
Handles customer conversation lifecycle and status management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import Conversation, ConversationStatus, Message
from app.middleware.tenant_middleware import get_tenant_id_from_request
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
    request: Request,
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Create a new customer conversation."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    db_conversation = Conversation(
        tenant_id=tenant_id,
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
    request: Request,
    status: Optional[ConversationStatus] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all conversations with optional status filter."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    query = db.query(Conversation).filter(Conversation.tenant_id == tenant_id)
    
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
    request: Request,
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific conversation by ID."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id
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
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Update conversation status (e.g., resolve, escalate)."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
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

