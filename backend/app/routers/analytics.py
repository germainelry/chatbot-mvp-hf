"""
Analytics endpoints for dashboard metrics.
Tracks key product metrics for AI system performance.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List

from app.database import get_db
from app.models import (
    Conversation, ConversationStatus, Message, 
    Feedback, FeedbackRating, MessageType
)

router = APIRouter()


class MetricsResponse(BaseModel):
    total_conversations: int
    active_conversations: int
    resolved_conversations: int
    escalated_conversations: int
    resolution_rate: float  # % resolved
    escalation_rate: float  # % escalated (deflection rate inverse)
    avg_confidence_score: float
    total_feedback: int
    helpful_feedback: int
    not_helpful_feedback: int
    feedback_sentiment: float  # % helpful


class FeedbackSummary(BaseModel):
    id: int
    conversation_id: int
    rating: str
    agent_correction: str
    notes: str
    created_at: str


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: Session = Depends(get_db)):
    """
    Calculate key product metrics for AI customer support system.
    
    Critical metrics for PM role:
    - Deflection Rate: % of conversations handled without escalation
    - Resolution Rate: % of conversations successfully resolved
    - Confidence Scores: AI model quality indicator
    - Feedback Sentiment: Agent satisfaction with AI responses
    """
    
    # Total conversations
    total_convs = db.query(func.count(Conversation.id)).scalar()
    
    # Active conversations
    active_convs = db.query(func.count(Conversation.id)).filter(
        Conversation.status == ConversationStatus.ACTIVE
    ).scalar()
    
    # Resolved conversations
    resolved_convs = db.query(func.count(Conversation.id)).filter(
        Conversation.status == ConversationStatus.RESOLVED
    ).scalar()
    
    # Escalated conversations
    escalated_convs = db.query(func.count(Conversation.id)).filter(
        Conversation.status == ConversationStatus.ESCALATED
    ).scalar()
    
    # Calculate rates
    resolution_rate = (resolved_convs / total_convs * 100) if total_convs > 0 else 0
    escalation_rate = (escalated_convs / total_convs * 100) if total_convs > 0 else 0
    
    # Average confidence score
    avg_confidence = db.query(func.avg(Message.confidence_score)).filter(
        Message.confidence_score.isnot(None)
    ).scalar() or 0.0
    
    # Feedback metrics
    total_feedback = db.query(func.count(Feedback.id)).scalar()
    
    helpful_feedback = db.query(func.count(Feedback.id)).filter(
        Feedback.rating == FeedbackRating.HELPFUL
    ).scalar()
    
    not_helpful_feedback = db.query(func.count(Feedback.id)).filter(
        Feedback.rating == FeedbackRating.NOT_HELPFUL
    ).scalar()
    
    feedback_sentiment = (helpful_feedback / total_feedback * 100) if total_feedback > 0 else 0
    
    return MetricsResponse(
        total_conversations=total_convs or 0,
        active_conversations=active_convs or 0,
        resolved_conversations=resolved_convs or 0,
        escalated_conversations=escalated_convs or 0,
        resolution_rate=round(resolution_rate, 2),
        escalation_rate=round(escalation_rate, 2),
        avg_confidence_score=round(avg_confidence, 2),
        total_feedback=total_feedback or 0,
        helpful_feedback=helpful_feedback or 0,
        not_helpful_feedback=not_helpful_feedback or 0,
        feedback_sentiment=round(feedback_sentiment, 2)
    )


@router.get("/feedback-history", response_model=List[FeedbackSummary])
async def get_feedback_history(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get recent feedback for review."""
    feedback = db.query(Feedback).order_by(
        Feedback.created_at.desc()
    ).limit(limit).all()
    
    return [
        FeedbackSummary(
            id=f.id,
            conversation_id=f.conversation_id,
            rating=f.rating.value,
            agent_correction=f.agent_correction or "",
            notes=f.notes or "",
            created_at=f.created_at.isoformat()
        )
        for f in feedback
    ]

