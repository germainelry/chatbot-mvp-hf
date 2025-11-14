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
from app.middleware.auth import require_api_key

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
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
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
    # Note: This is for POST-SEND feedback corrections (alternative/better responses).
    # PRE-SEND edits (when agent edits before sending) automatically calculate metrics
    # in the message update endpoint.
    if feedback.agent_correction and feedback.message_id:
        message = db.query(Message).filter(Message.id == feedback.message_id).first()
        if message:
            # Use original AI content if available (for edited messages), otherwise use current content
            # This ensures we compare against the original AI draft, not the edited version
            ai_response_content = message.original_ai_content if message.original_ai_content else message.content
            
            # Evaluate AI response against agent correction
            # This allows agents to provide an alternative/better response in feedback
            # even if they already edited the message before sending
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


# Note: GET /feedback, GET /feedback/{id}, POST /retrain, and GET /training-data/export
# endpoints have been removed as they are not used by the frontend.
# Frontend uses /analytics/feedback-history for feedback display.

