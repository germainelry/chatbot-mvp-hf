"""
Feedback collection endpoints.
Critical for RLHF and model improvement workflows.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models import Feedback, FeedbackRating, Conversation

router = APIRouter()


class FeedbackCreate(BaseModel):
    conversation_id: int
    message_id: Optional[int] = None
    rating: FeedbackRating
    agent_correction: Optional[str] = None
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    conversation_id: int
    message_id: Optional[int]
    rating: FeedbackRating
    agent_correction: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=FeedbackResponse)
async def create_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    Submit agent feedback on AI responses.
    Used for training data collection and model improvement.
    """
    # Verify conversation exists
    conversation = db.query(Conversation).filter(
        Conversation.id == feedback.conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create feedback entry
    db_feedback = Feedback(
        conversation_id=feedback.conversation_id,
        message_id=feedback.message_id,
        rating=feedback.rating,
        agent_correction=feedback.agent_correction,
        notes=feedback.notes
    )
    
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    
    return db_feedback


@router.get("", response_model=List[FeedbackResponse])
async def get_all_feedback(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent feedback for analytics."""
    feedback = db.query(Feedback).order_by(
        Feedback.created_at.desc()
    ).limit(limit).all()
    
    return feedback


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db)
):
    """Get specific feedback entry."""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return feedback

