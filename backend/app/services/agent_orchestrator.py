"""
Agent Orchestrator - Coordinates multi-agent system.
Routes messages to appropriate agents based on intent classification.
"""
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.services.router_agent import classify_intent, should_escalate
from app.services.knowledge_agent import handle_knowledge_query
from app.services.escalation_agent import handle_escalation, get_escalation_reason


async def orchestrate_response(
    conversation_id: int,
    user_message: str,
    db: Session,
    tenant_id: Optional[int] = None
) -> Dict:
    """
    Main orchestration function.
    Routes user message through router → knowledge/escalation agent.
    """
    # Step 1: Router classifies intent
    intent_result = classify_intent(user_message)
    intent = intent_result["intent"]
    confidence = intent_result["confidence"]
    
    # Step 2: Check if escalation is needed
    if should_escalate(intent, confidence, user_message):
        # Route to escalation agent
        escalation_reason = get_escalation_reason(intent, confidence, user_message)
        result = await handle_escalation(
            conversation_id=conversation_id,
            user_message=user_message,
            escalation_reason=escalation_reason,
            db=db
        )
        result["intent"] = intent
        result["intent_confidence"] = confidence
        return result
    
    # Step 3: Route to knowledge agent for FAQ/order inquiries
    if intent in ["faq", "order_inquiry", "general"]:
        result = await handle_knowledge_query(
            user_message=user_message,
            conversation_id=conversation_id,
            db=db,
            tenant_id=tenant_id
        )
        result["intent"] = intent
        result["intent_confidence"] = confidence
        return result
    
    # Step 4: Technical support - try knowledge agent first, but lower threshold
    if intent == "technical_support":
        result = await handle_knowledge_query(
            user_message=user_message,
            conversation_id=conversation_id,
            db=db,
            tenant_id=tenant_id
        )
        # Lower confidence threshold for technical support
        if result["confidence_score"] < 0.6:
            # Escalate if confidence is low
            escalation_reason = f"Technical support query with low confidence ({result['confidence_score']:.2f})"
            result = await handle_escalation(
                conversation_id=conversation_id,
                user_message=user_message,
                escalation_reason=escalation_reason,
                db=db
            )
        result["intent"] = intent
        result["intent_confidence"] = confidence
        return result
    
    # Default: route to knowledge agent
    result = await handle_knowledge_query(
        user_message=user_message,
        conversation_id=conversation_id,
        db=db,
        tenant_id=tenant_id
    )
    result["intent"] = intent
    result["intent_confidence"] = confidence
    return result

