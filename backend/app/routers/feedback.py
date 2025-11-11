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
from app.models import Feedback, FeedbackRating, Conversation, Message, TrainingData
from app.services.evaluation_service import evaluate_ai_response, save_evaluation_metrics
from app.services.data_logging_service import log_agent_action

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
    
    # Calculate and save evaluation metrics if agent correction is provided
    if feedback.agent_correction and feedback.message_id:
        message = db.query(Message).filter(Message.id == feedback.message_id).first()
        if message:
            # Use original AI content if available (for edited messages), otherwise use current content
            ai_response_content = message.original_ai_content if message.original_ai_content else message.content
            
            # Evaluate AI response against agent correction
            eval_metrics = evaluate_ai_response(
                ai_response=ai_response_content,
                agent_correction=feedback.agent_correction
            )
            
            # Save evaluation metrics
            save_evaluation_metrics(
                message_id=feedback.message_id,
                conversation_id=feedback.conversation_id,
                bleu_score=eval_metrics.get("bleu_score"),
                semantic_similarity=eval_metrics.get("semantic_similarity"),
                csat_score=None,
                db=db
            )
            
            # Create training data entry if correction provided
            if feedback.agent_correction:
                training_data = TrainingData(
                    feedback_id=db_feedback.id,
                    conversation_id=feedback.conversation_id,
                    message_id=feedback.message_id,
                    original_ai_response=ai_response_content,
                    agent_correction=feedback.agent_correction,
                    intent=message.intent,
                    processed=0
                )
                db.add(training_data)
                db.commit()
    
    # Automatically log agent action based on feedback rating
    action_type_map = {
        FeedbackRating.HELPFUL: 'approve',
        FeedbackRating.NOT_HELPFUL: 'reject',
        FeedbackRating.NEEDS_IMPROVEMENT: 'edit' if feedback.agent_correction else None
    }
    
    action_type = action_type_map.get(feedback.rating)
    if action_type:
        try:
            log_agent_action(
                action_type=action_type,
                conversation_id=feedback.conversation_id,
                message_id=feedback.message_id,
                action_data={
                    'rating': feedback.rating.value,
                    'has_correction': bool(feedback.agent_correction)
                },
                db=db
            )
        except Exception as e:
            # Don't fail feedback submission if action logging fails
            print(f"Failed to auto-log agent action: {e}")
    
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


@router.post("/retrain")
async def trigger_retraining(
    db: Session = Depends(get_db)
):
    """
    Manually trigger retraining pipeline.
    Processes feedback and updates models.
    """
    from app.services.retraining_service import process_retraining
    
    results = process_retraining(db)
    return results


@router.get("/training-data/export")
async def export_training_data(
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Export training data in JSONL format.
    """
    from app.services.retraining_service import export_training_data_jsonl
    
    jsonl_data = export_training_data_jsonl(db, limit=limit)
    return {"data": jsonl_data, "format": "jsonl"}

