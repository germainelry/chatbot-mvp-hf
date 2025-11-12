"""
Message management endpoints.
Handles sending customer messages and agent responses.
"""
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models import Conversation, Message, MessageType
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()


class MessageCreate(BaseModel):
    conversation_id: int
    content: str
    message_type: MessageType
    confidence_score: Optional[float] = None
    original_ai_content: Optional[str] = None
    intent: Optional[str] = None
    agent_type: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    content: str
    message_type: MessageType
    confidence_score: Optional[float]
    intent: Optional[str] = None
    agent_type: Optional[str] = None
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
        original_ai_content=message.original_ai_content,
        intent=message.intent,
        agent_type=message.agent_type
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


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    message_type: Optional[MessageType] = None
    confidence_score: Optional[float] = None
    original_ai_content: Optional[str] = None
    intent: Optional[str] = None
    agent_type: Optional[str] = None


@router.patch("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: int,
    update: MessageUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing message.
    Used to convert ai_draft to final/agent_edited when agent approves.
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Track if this is an edit (has original_ai_content and is being changed to agent_edited)
    is_edit = False
    original_ai_content = None
    
    # Update fields if provided
    if update.content is not None:
        message.content = update.content
    if update.message_type is not None:
        message.message_type = update.message_type
    if update.confidence_score is not None:
        message.confidence_score = update.confidence_score
    if update.original_ai_content is not None:
        message.original_ai_content = update.original_ai_content
        original_ai_content = update.original_ai_content
    elif message.original_ai_content:
        # Use existing original_ai_content if update doesn't provide it
        original_ai_content = message.original_ai_content
    if update.intent is not None:
        message.intent = update.intent
    if update.agent_type is not None:
        message.agent_type = update.agent_type
    
    # Check if this is an edit: message has original_ai_content and type is agent_edited
    final_message_type = update.message_type if update.message_type is not None else message.message_type
    if original_ai_content and final_message_type == MessageType.AGENT_EDITED and message.content:
        is_edit = True
    
    # Update conversation timestamp
    conversation = db.query(Conversation).filter(
        Conversation.id == message.conversation_id
    ).first()
    if conversation:
        conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    
    # Automatically calculate evaluation metrics when a message is edited
    if is_edit and original_ai_content and message.content:
        try:
            from app.services.evaluation_service import evaluate_ai_response, save_evaluation_metrics
            
            # Compare original AI response with agent's edited version
            eval_metrics = evaluate_ai_response(
                ai_response=original_ai_content,
                agent_correction=message.content
            )
            
            # Save evaluation metrics
            save_evaluation_metrics(
                message_id=message.id,
                conversation_id=message.conversation_id,
                bleu_score=eval_metrics.get("bleu_score"),
                semantic_similarity=eval_metrics.get("semantic_similarity"),
                csat_score=None,
                db=db
            )
        except Exception as e:
            # Don't fail message update if evaluation calculation fails
            print(f"Failed to calculate evaluation metrics for edited message: {e}")
    
    return message

