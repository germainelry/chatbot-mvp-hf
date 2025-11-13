"""
Knowledge Agent - Handles FAQ and knowledge base queries.
Extracted from llm_service, specialized for knowledge retrieval.
"""
import os
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.llm_service import (
    generate_ai_response,
    generate_ollama_response,
    generate_fallback_response,
    OLLAMA_AVAILABLE,
    OLLAMA_MODEL,
    AUTO_SEND_THRESHOLD
)
from app.services.rag_service import search_knowledge_base_vector

# Re-export for convenience
def calculate_confidence_score(matched_articles: List[Dict], query: str) -> float:
    """Calculate confidence score based on knowledge base matches."""
    if not matched_articles:
        return 0.3
    
    # Use similarity if available (from vector search), otherwise match_score
    best_score = matched_articles[0].get("similarity") or matched_articles[0].get("match_score", 0)
    
    if best_score > 0.7:
        return 0.85
    elif best_score > 0.5:
        return 0.65
    elif best_score > 0.3:
        return 0.4
    else:
        return 0.3


async def handle_knowledge_query(
    user_message: str,
    conversation_id: int,
    db: Session,
    tenant_id: Optional[int] = None
) -> Dict:
    """
    Handle knowledge base query using RAG.
    Returns response with confidence score.
    
    Args:
        user_message: User's message
        conversation_id: Conversation ID
        db: Database session
        tenant_id: Deprecated - kept for backward compatibility
    """
    # Search knowledge base
    matched_articles = search_knowledge_base_vector(user_message, db, top_k=3, tenant_id=None)
    
    # Calculate confidence
    confidence = calculate_confidence_score(matched_articles, user_message)
    
    # Use LLM service
    result = await generate_ai_response(
        conversation_id=conversation_id,
        user_message=user_message,
        db=db,
        tenant_id=None
    )
    
    # Add agent type
    result["agent_type"] = "knowledge"
    return result

