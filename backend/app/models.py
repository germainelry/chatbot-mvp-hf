"""
Database models for AI Customer Support System.
Designed to support Human-in-the-Loop workflows and feedback collection.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class ConversationStatus(str, enum.Enum):
    """Status of customer conversation - critical for metrics tracking."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"  # When AI confidence is low or agent manually escalates


class MessageType(str, enum.Enum):
    """Message types for HITL workflow tracking."""
    CUSTOMER = "customer"
    AI_DRAFT = "ai_draft"  # AI generated, awaiting agent review
    AGENT_EDITED = "agent_edited"  # Agent modified AI draft
    FINAL = "final"  # Final response sent to customer
    AGENT_ONLY = "agent_only"  # Human agent response (no AI involvement)


class FeedbackRating(str, enum.Enum):
    """Agent feedback on AI responses - used for model improvement."""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    NEEDS_IMPROVEMENT = "needs_improvement"


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, index=True)  # Session-based for MVP
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), nullable=False, index=True)
    confidence_score = Column(Float, nullable=True)  # AI confidence (0-1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # For tracking AI drafts that were edited by agents
    original_ai_content = Column(Text, nullable=True)  # Store original AI draft if edited
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class KnowledgeBase(Base):
    """
    Knowledge base articles for RAG implementation.
    In production, would use vector embeddings for semantic search.
    For MVP, using simple keyword matching.
    """
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String, index=True)
    tags = Column(String)  # Comma-separated for MVP
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Feedback(Base):
    """
    Agent feedback on AI responses - critical for RLHF and model improvement.
    Tracks corrections, ratings, and provides training data.
    """
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    message_id = Column(Integer, nullable=True)  # Optional link to specific message
    rating = Column(Enum(FeedbackRating), nullable=False, index=True)
    agent_correction = Column(Text, nullable=True)  # What agent would have said instead
    notes = Column(Text, nullable=True)  # Additional agent comments
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="feedback")


class Metrics(Base):
    """
    Pre-computed metrics for dashboard performance.
    In production, would use time-series DB or analytics service.
    """
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    total_conversations = Column(Integer, default=0)
    resolved_conversations = Column(Integer, default=0)
    escalated_conversations = Column(Integer, default=0)
    avg_confidence_score = Column(Float, default=0.0)
    helpful_feedback_count = Column(Integer, default=0)
    not_helpful_feedback_count = Column(Integer, default=0)
    avg_response_time_seconds = Column(Float, default=0.0)

