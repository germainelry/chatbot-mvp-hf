"""
AI service endpoints.
Handles LLM response generation with confidence scoring.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.services.llm_service import generate_ai_response

router = APIRouter()


class AIGenerateRequest(BaseModel):
    conversation_id: int
    user_message: str


class AIGenerateResponse(BaseModel):
    response: str
    confidence_score: float
    matched_articles: List[dict] = []
    reasoning: Optional[str] = None


@router.post("/generate", response_model=AIGenerateResponse)
async def generate_response(
    request: AIGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate AI response for customer message.
    Returns response with confidence score for HITL decision-making.
    
    Confidence scoring logic:
    - High (>0.8): Knowledge base match, can auto-send
    - Medium (0.5-0.8): Partial match, queue for review
    - Low (<0.5): No match, requires agent intervention
    """
    try:
        result = await generate_ai_response(
            conversation_id=request.conversation_id,
            user_message=request.user_message,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

