"""
Agent actions logging endpoints.
Allows frontend to log agent actions for analytics and performance tracking.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models import AgentAction
from app.services.data_logging_service import log_agent_action
from app.middleware.auth import require_api_key

router = APIRouter()


class AgentActionCreate(BaseModel):
    action_type: str  # approve, reject, edit, escalate
    conversation_id: Optional[int] = None
    message_id: Optional[int] = None
    action_data: Optional[Dict[str, Any]] = None


class AgentActionResponse(BaseModel):
    id: int
    conversation_id: Optional[int]
    message_id: Optional[int]
    action_type: str
    action_data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=AgentActionResponse)
async def create_agent_action(
    action: AgentActionCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """
    Log an agent action (approve, reject, edit, escalate).
    Used for analytics and agent performance tracking.
    """
    # Validate action_type
    valid_actions = ['approve', 'reject', 'edit', 'escalate']
    if action.action_type not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action_type. Must be one of: {', '.join(valid_actions)}"
        )
    
    # Log the action
    agent_action = log_agent_action(
        action_type=action.action_type,
        conversation_id=action.conversation_id,
        message_id=action.message_id,
        action_data=action.action_data,
        db=db
    )
    
    if not agent_action:
        raise HTTPException(
            status_code=500,
            detail="Failed to log agent action"
        )
    
    # Parse action_data from JSON string if it exists
    action_data_dict = None
    if agent_action.action_data:
        if isinstance(agent_action.action_data, str):
            try:
                action_data_dict = json.loads(agent_action.action_data)
            except json.JSONDecodeError:
                action_data_dict = None
        else:
            action_data_dict = agent_action.action_data
    
    return AgentActionResponse(
        id=agent_action.id,
        conversation_id=agent_action.conversation_id,
        message_id=agent_action.message_id,
        action_type=agent_action.action_type,
        action_data=action_data_dict,
        created_at=agent_action.created_at
    )

