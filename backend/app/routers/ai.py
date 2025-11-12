"""
AI service endpoints.
Handles LLM response generation with confidence scoring.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.services.llm_service import generate_ai_response  # Keep for backward compatibility
from app.services.agent_orchestrator import orchestrate_response
from app.middleware.tenant_middleware import get_tenant_id_from_request
from app.middleware.auth import require_api_key

router = APIRouter()


class AIGenerateRequest(BaseModel):
    conversation_id: int
    user_message: str


class AIGenerateResponse(BaseModel):
    response: str
    confidence_score: float
    matched_articles: List[dict] = []
    reasoning: Optional[str] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    agent_type: Optional[str] = None


@router.post("/generate", response_model=AIGenerateResponse)
async def generate_response(
    http_request: Request,
    request: AIGenerateRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key),
    use_orchestrator: bool = True  # Use multi-agent orchestrator by default
):
    """
    Generate AI response for customer message using multi-agent orchestrator.
    Returns response with confidence score, intent, and agent type for HITL decision-making.
    
    Confidence scoring logic:
    - High (>0.8): Knowledge base match, can auto-send
    - Medium (0.5-0.8): Partial match, queue for review
    - Low (<0.5): No match, requires agent intervention
    """
    try:
        tenant_id = get_tenant_id_from_request(http_request)
        
        if use_orchestrator:
            # Use multi-agent orchestrator
            result = await orchestrate_response(
                conversation_id=request.conversation_id,
                user_message=request.user_message,
                db=db,
                tenant_id=tenant_id
            )
            return AIGenerateResponse(
                response=result["response"],
                confidence_score=result["confidence_score"],
                matched_articles=result.get("matched_articles", []),
                reasoning=result.get("reasoning", "Multi-agent orchestration"),
                intent=result.get("intent"),
                intent_confidence=result.get("intent_confidence"),
                agent_type=result.get("agent_type")
            )
        else:
            # Fallback to original single-agent approach
            result = await generate_ai_response(
                conversation_id=request.conversation_id,
                user_message=request.user_message,
                db=db,
                tenant_id=tenant_id
            )
            return AIGenerateResponse(
                response=result["response"],
                confidence_score=result["confidence_score"],
                matched_articles=result.get("matched_articles", []),
                reasoning=result.get("reasoning", "Single-agent LLM"),
                intent=None,
                intent_confidence=None,
                agent_type=None
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

