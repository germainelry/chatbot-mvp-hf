"""
Analytics endpoints for dashboard metrics.
Tracks key product metrics for AI system performance.
"""
from datetime import date, datetime, timedelta
from typing import List

from app.database import get_db
from app.models import (
    Conversation,
    ConversationStatus,
    Feedback,
    FeedbackRating,
    Message,
    MessageType,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Date, Integer, case, cast, func
from sqlalchemy.orm import Session

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


class DailyMetrics(BaseModel):
    date: str
    total_conversations: int
    resolved_conversations: int
    escalated_conversations: int
    avg_confidence_score: float
    helpful_feedback: int
    not_helpful_feedback: int
    needs_improvement_feedback: int


class TimeSeriesResponse(BaseModel):
    metrics: List[DailyMetrics]


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


@router.get("/time-series", response_model=TimeSeriesResponse)
async def get_time_series_metrics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get daily aggregated metrics for time-series visualization.
    Returns metrics for the last N days (default 30), or all available data if less exists.
    """
    # Find the earliest conversation date to ensure we show all data
    earliest_conv = db.query(func.min(Conversation.created_at)).scalar()
    
    # Calculate date range
    end_date = datetime.utcnow().date()
    
    if earliest_conv:
        # Get the earliest conversation date
        earliest_date = earliest_conv.date() if isinstance(earliest_conv, datetime) else earliest_conv
        
        # Use the earlier of: (earliest conversation date) or (today - requested days)
        # This ensures we show all data while respecting the requested range
        calculated_start = end_date - timedelta(days=days - 1)
        start_date = min(earliest_date, calculated_start)
        
        # Calculate actual number of days
        actual_days = (end_date - start_date).days + 1
        
        # Cap at reasonable maximum (90 days) to prevent performance issues
        if actual_days > 90:
            start_date = end_date - timedelta(days=89)  # Show last 90 days
            actual_days = 90
    else:
        # No conversations exist, use default range
        start_date = end_date - timedelta(days=days - 1)
        actual_days = days
    
    # Generate all dates in range (to fill gaps)
    date_list = [start_date + timedelta(days=x) for x in range(actual_days)]
    
    # Get daily conversation counts - get all conversations and filter by date range
    # This avoids timezone issues with date casting
    all_convs = db.query(Conversation).all()
    
    # Group by date (using UTC date to match created_at)
    conv_dict = {}
    for conv in all_convs:
        conv_date = conv.created_at.date() if isinstance(conv.created_at, datetime) else conv.created_at
        # Only include if within our date range
        if start_date <= conv_date <= end_date:
            if conv_date not in conv_dict:
                conv_dict[conv_date] = {'total': 0, 'resolved': 0, 'escalated': 0}
            conv_dict[conv_date]['total'] += 1
            if conv.status == ConversationStatus.RESOLVED:
                conv_dict[conv_date]['resolved'] += 1
            elif conv.status == ConversationStatus.ESCALATED:
                conv_dict[conv_date]['escalated'] += 1
    
    # Get daily average confidence scores - process all messages
    all_messages = db.query(Message).filter(
        Message.confidence_score.isnot(None)
    ).all()
    
    # Group by date and calculate averages
    confidence_by_date = {}
    for msg in all_messages:
        msg_date = msg.created_at.date() if isinstance(msg.created_at, datetime) else msg.created_at
        if start_date <= msg_date <= end_date:
            if msg_date not in confidence_by_date:
                confidence_by_date[msg_date] = []
            confidence_by_date[msg_date].append(msg.confidence_score)
    
    # Calculate averages
    confidence_dict = {
        date: sum(scores) / len(scores) if scores else 0.0
        for date, scores in confidence_by_date.items()
    }
    
    # Get daily feedback counts - process all feedback
    all_feedback = db.query(Feedback).all()
    
    # Group by date
    feedback_dict = {}
    for fb in all_feedback:
        fb_date = fb.created_at.date() if isinstance(fb.created_at, datetime) else fb.created_at
        if start_date <= fb_date <= end_date:
            if fb_date not in feedback_dict:
                feedback_dict[fb_date] = {'helpful': 0, 'not_helpful': 0, 'needs_improvement': 0}
            if fb.rating == FeedbackRating.HELPFUL:
                feedback_dict[fb_date]['helpful'] += 1
            elif fb.rating == FeedbackRating.NOT_HELPFUL:
                feedback_dict[fb_date]['not_helpful'] += 1
            elif fb.rating == FeedbackRating.NEEDS_IMPROVEMENT:
                feedback_dict[fb_date]['needs_improvement'] += 1
    
    # Build response with all dates (filling gaps with zeros)
    metrics = []
    for d in date_list:
        conv_data = conv_dict.get(d, {'total': 0, 'resolved': 0, 'escalated': 0})
        avg_conf = confidence_dict.get(d, 0.0)
        feedback_data = feedback_dict.get(d, {'helpful': 0, 'not_helpful': 0, 'needs_improvement': 0})
        
        metrics.append(DailyMetrics(
            date=d.isoformat(),
            total_conversations=conv_data['total'],
            resolved_conversations=conv_data['resolved'],
            escalated_conversations=conv_data['escalated'],
            avg_confidence_score=round(avg_conf, 3) if avg_conf else 0.0,
            helpful_feedback=feedback_data['helpful'],
            not_helpful_feedback=feedback_data['not_helpful'],
            needs_improvement_feedback=feedback_data['needs_improvement']
        ))
    
    return TimeSeriesResponse(metrics=metrics)

