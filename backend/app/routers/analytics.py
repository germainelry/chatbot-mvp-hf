"""
Analytics endpoints for dashboard metrics.
Tracks key product metrics for AI system performance.
"""
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

from app.database import get_db
from app.models import (
    Conversation,
    ConversationStatus,
    Feedback,
    FeedbackRating,
    Message,
    MessageType,
    EvaluationMetrics,
)
from app.services.evaluation_service import aggregate_evaluation_metrics
from app.services.data_logging_service import get_agent_performance_metrics
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
    Calculate key enterprise metrics for AI customer support system.

    OPTIMIZED: Reduced from 9+ queries to 3 queries for faster performance.

    Critical metrics for enterprise AI chatbot:
    - Resolution Rate: % of conversations successfully resolved
    - Escalation Rate: % requiring human intervention
    - Deflection Rate: % handled by AI (inverse of escalation)
    - Confidence Scores: AI model quality indicator
    - Feedback Sentiment: Agent satisfaction with AI responses
    """

    # QUERY 1: Single query for all conversation counts by status (was 4 queries)
    status_counts = db.query(
        func.count(Conversation.id).label('total'),
        func.sum(case((Conversation.status == ConversationStatus.ACTIVE, 1), else_=0)).label('active'),
        func.sum(case((Conversation.status == ConversationStatus.RESOLVED, 1), else_=0)).label('resolved'),
        func.sum(case((Conversation.status == ConversationStatus.ESCALATED, 1), else_=0)).label('escalated')
    ).first()

    total_convs = int(status_counts.total or 0)
    active_convs = int(status_counts.active or 0)
    resolved_convs = int(status_counts.resolved or 0)
    escalated_convs = int(status_counts.escalated or 0)

    # Calculate rates
    resolution_rate = (resolved_convs / total_convs * 100) if total_convs > 0 else 0
    escalation_rate = (escalated_convs / total_convs * 100) if total_convs > 0 else 0

    # QUERY 2: Average confidence score
    avg_confidence = db.query(func.avg(Message.confidence_score)).filter(
        Message.confidence_score.isnot(None)
    ).scalar() or 0.0

    # QUERY 3: Single query for all feedback counts (was 3 queries)
    feedback_counts = db.query(
        func.count(Feedback.id).label('total'),
        func.sum(case((Feedback.rating == FeedbackRating.HELPFUL, 1), else_=0)).label('helpful'),
        func.sum(case((Feedback.rating == FeedbackRating.NOT_HELPFUL, 1), else_=0)).label('not_helpful')
    ).first()

    total_feedback = int(feedback_counts.total or 0)
    helpful_feedback = int(feedback_counts.helpful or 0)
    not_helpful_feedback = int(feedback_counts.not_helpful or 0)

    feedback_sentiment = (helpful_feedback / total_feedback * 100) if total_feedback > 0 else 0

    return MetricsResponse(
        total_conversations=total_convs,
        active_conversations=active_convs,
        resolved_conversations=resolved_convs,
        escalated_conversations=escalated_convs,
        resolution_rate=round(resolution_rate, 2),
        escalation_rate=round(escalation_rate, 2),
        avg_confidence_score=round(avg_confidence, 2),
        total_feedback=total_feedback,
        helpful_feedback=helpful_feedback,
        not_helpful_feedback=not_helpful_feedback,
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
    
    # Convert dates to datetime for SQL comparison
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Get daily conversation counts using SQL aggregation
    # Filter by date range at database level and group by date
    conv_counts = db.query(
        func.date(Conversation.created_at).label('date'),
        func.count(Conversation.id).label('total'),
        func.sum(case((Conversation.status == ConversationStatus.RESOLVED, 1), else_=0)).label('resolved'),
        func.sum(case((Conversation.status == ConversationStatus.ESCALATED, 1), else_=0)).label('escalated')
    ).filter(
        Conversation.created_at >= start_datetime,
        Conversation.created_at < end_datetime + timedelta(days=1)
    ).group_by(
        func.date(Conversation.created_at)
    ).all()
    
    # Build conversation dictionary from SQL results
    conv_dict = {}
    for row in conv_counts:
        conv_date = row.date if isinstance(row.date, date) else row.date.date()
        conv_dict[conv_date] = {
            'total': row.total or 0,
            'resolved': int(row.resolved or 0),
            'escalated': int(row.escalated or 0)
        }
    
    # Get daily average confidence scores using SQL aggregation
    confidence_avg = db.query(
        func.date(Message.created_at).label('date'),
        func.avg(Message.confidence_score).label('avg_confidence')
    ).filter(
        Message.confidence_score.isnot(None),
        Message.created_at >= start_datetime,
        Message.created_at < end_datetime + timedelta(days=1)
    ).group_by(
        func.date(Message.created_at)
    ).all()
    
    # Build confidence dictionary from SQL results
    confidence_dict = {}
    for row in confidence_avg:
        conf_date = row.date if isinstance(row.date, date) else row.date.date()
        confidence_dict[conf_date] = float(row.avg_confidence or 0.0)
    
    # Get daily feedback counts using SQL aggregation
    feedback_counts = db.query(
        func.date(Feedback.created_at).label('date'),
        func.sum(case((Feedback.rating == FeedbackRating.HELPFUL, 1), else_=0)).label('helpful'),
        func.sum(case((Feedback.rating == FeedbackRating.NOT_HELPFUL, 1), else_=0)).label('not_helpful'),
        func.sum(case((Feedback.rating == FeedbackRating.NEEDS_IMPROVEMENT, 1), else_=0)).label('needs_improvement')
    ).filter(
        Feedback.created_at >= start_datetime,
        Feedback.created_at < end_datetime + timedelta(days=1)
    ).group_by(
        func.date(Feedback.created_at)
    ).all()
    
    # Build feedback dictionary from SQL results
    feedback_dict = {}
    for row in feedback_counts:
        fb_date = row.date if isinstance(row.date, date) else row.date.date()
        feedback_dict[fb_date] = {
            'helpful': int(row.helpful or 0),
            'not_helpful': int(row.not_helpful or 0),
            'needs_improvement': int(row.needs_improvement or 0)
        }
    
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


class EvaluationMetricsResponse(BaseModel):
    avg_bleu_score: Optional[float]
    avg_semantic_similarity: Optional[float]
    avg_csat: Optional[float]
    deflection_rate: float
    total_evaluations: int
    total_csat_responses: int


@router.get("/evaluation", response_model=EvaluationMetricsResponse)
async def get_evaluation_metrics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get evaluation metrics including BLEU scores, semantic similarity, and CSAT.
    """
    metrics = aggregate_evaluation_metrics(db, days=days)
    return EvaluationMetricsResponse(**metrics)


class AgentPerformanceResponse(BaseModel):
    total_actions: int
    approval_rate: float
    correction_frequency: int
    action_breakdown: Dict[str, int]


@router.get("/agent-performance", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get agent performance metrics including approval rate and correction frequency.
    """
    metrics = get_agent_performance_metrics(db, days=days)
    return AgentPerformanceResponse(**metrics)

