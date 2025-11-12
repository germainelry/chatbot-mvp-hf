"""
Demo mode restrictions middleware.
Limits usage to prevent abuse and control costs in demo environment.
"""
import os
from datetime import datetime, timedelta
from typing import Callable
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import SessionLocal
from app.models import Conversation, Message

# Demo mode configuration
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
MAX_CONVERSATIONS_PER_IP_PER_DAY = int(os.getenv("MAX_CONVERSATIONS_PER_IP_PER_DAY", "10"))
MAX_MESSAGES_PER_CONVERSATION = int(os.getenv("MAX_MESSAGES_PER_CONVERSATION", "20"))
CONVERSATION_AUTO_ARCHIVE_HOURS = int(os.getenv("CONVERSATION_AUTO_ARCHIVE_HOURS", "24"))


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded IP (from proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client
    if request.client:
        return request.client.host
    
    return "unknown"


def check_conversation_limit(request: Request, db: Session) -> bool:
    """
    Check if IP has exceeded daily conversation limit.
    Returns True if limit not exceeded, False otherwise.
    """
    if not DEMO_MODE:
        return True
    
    client_ip = get_client_ip(request)
    if client_ip == "unknown":
        return True  # Allow if IP cannot be determined
    
    # Count conversations created by this IP in the last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    count = db.query(Conversation).filter(
        and_(
            Conversation.created_at >= yesterday,
            # Note: We'd need to store IP in conversation model for this to work
            # For now, we'll use a simpler approach with tenant ID
        )
    ).count()
    
    # For now, we'll limit based on tenant ID if available
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        count = db.query(Conversation).filter(
            and_(
                Conversation.tenant_id == int(tenant_id),
                Conversation.created_at >= yesterday
            )
        ).count()
        
        if count >= MAX_CONVERSATIONS_PER_IP_PER_DAY:
            return False
    
    return True


def check_message_limit(conversation_id: int, db: Session) -> bool:
    """
    Check if conversation has exceeded message limit.
    Returns True if limit not exceeded, False otherwise.
    """
    if not DEMO_MODE:
        return True
    
    message_count = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).count()
    
    return message_count < MAX_MESSAGES_PER_CONVERSATION


def auto_archive_old_conversations(db: Session):
    """
    Auto-archive conversations older than CONVERSATION_AUTO_ARCHIVE_HOURS.
    This should be called periodically (e.g., via a background task).
    """
    if not DEMO_MODE:
        return
    
    cutoff_time = datetime.utcnow() - timedelta(hours=CONVERSATION_AUTO_ARCHIVE_HOURS)
    
    # Update old active conversations to resolved
    db.query(Conversation).filter(
        and_(
            Conversation.status == "active",
            Conversation.created_at < cutoff_time
        )
    ).update({"status": "resolved", "resolved_at": datetime.utcnow()})
    
    db.commit()


class DemoModeMiddleware(BaseHTTPMiddleware):
    """
    Demo mode middleware that enforces usage restrictions.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip demo mode checks for health and docs endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        if not DEMO_MODE:
            return await call_next(request)
        
        # Check conversation creation limit
        if request.method == "POST" and "/api/conversations" in request.url.path:
            db = SessionLocal()
            try:
                if not check_conversation_limit(request, db):
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Demo mode limit exceeded",
                            "message": f"Maximum {MAX_CONVERSATIONS_PER_IP_PER_DAY} conversations per day allowed in demo mode."
                        }
                    )
            finally:
                db.close()
        
        # Check message limit for message creation
        if request.method == "POST" and "/api/messages" in request.url.path:
            # Extract conversation_id from request body if possible
            # This is a simplified check - full implementation would parse body
            pass  # Will be handled in the route handler
        
        response = await call_next(request)
        
        # Add demo mode headers
        response.headers["X-Demo-Mode"] = "true"
        response.headers["X-Max-Conversations-Per-Day"] = str(MAX_CONVERSATIONS_PER_IP_PER_DAY)
        response.headers["X-Max-Messages-Per-Conversation"] = str(MAX_MESSAGES_PER_CONVERSATION)
        
        return response

