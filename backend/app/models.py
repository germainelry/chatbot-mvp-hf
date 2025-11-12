"""
Database models for AI Customer Support System.
Designed to support Human-in-the-Loop workflows and feedback collection.
"""
import enum
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship


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


class AgentType(str, enum.Enum):
    """Types of agents in the multi-agent system."""
    ROUTER = "router"
    KNOWLEDGE = "knowledge"
    ESCALATION = "escalation"


class SourceType(str, enum.Enum):
    """Types of knowledge base sources."""
    MANUAL = "manual"
    PDF = "pdf"
    CSV = "csv"
    DATABASE = "database"
    DOCUMENT = "document"


class SourceStatus(str, enum.Enum):
    """Status of knowledge base source."""
    ACTIVE = "active"
    PROCESSING = "processing"
    ERROR = "error"


class Tenant(Base):
    """
    Tenant/Client model for multi-tenant architecture.
    Each client gets isolated configuration and data.
    """
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)  # Unique identifier
    is_active = Column(Integer, default=1)  # 0 = inactive, 1 = active
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    configuration = relationship("TenantConfiguration", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    knowledge_sources = relationship("KnowledgeBaseSource", back_populates="tenant", cascade="all, delete-orphan")
    database_connections = relationship("DatabaseConnection", back_populates="tenant", cascade="all, delete-orphan")


class TenantConfiguration(Base):
    """
    Per-tenant configuration settings.
    Stores LLM, UI, and operational settings for each tenant.
    """
    __tablename__ = "tenant_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), unique=True, nullable=False, index=True)
    llm_provider = Column(String, default="ollama")  # ollama, huggingface, etc.
    llm_model_name = Column(String, default="llama3.2")  # Model name
    llm_config = Column(JSON, nullable=True)  # API keys, endpoints, parameters
    embedding_model = Column(String, default="all-MiniLM-L6-v2")  # Embedding model for RAG
    tone = Column(String, default="professional")  # professional, casual, friendly
    auto_send_threshold = Column(Float, default=0.65)  # Confidence threshold
    ui_config = Column(JSON, nullable=True)  # colors, logo_url, brand_name
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="configuration")


class KnowledgeBaseSource(Base):
    """
    Tracks knowledge base sources per tenant.
    Supports multiple sources: manual entries, files, databases.
    """
    __tablename__ = "knowledge_base_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    source_type = Column(Enum(SourceType), nullable=False, index=True)
    source_config = Column(JSON, nullable=True)  # File path, DB connection, etc.
    status = Column(Enum(SourceStatus), default=SourceStatus.ACTIVE, index=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="knowledge_sources")


class DatabaseConnection(Base):
    """
    Stores database connections for RAG integration.
    Encrypted connection strings for security.
    """
    __tablename__ = "database_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    connection_name = Column(String, nullable=False)
    db_type = Column(String, nullable=False)  # postgresql, mysql, sqlite
    connection_string = Column(Text, nullable=False)  # Encrypted connection string
    tables_config = Column(JSON, nullable=True)  # Which tables/columns to use
    is_active = Column(Integer, default=1)  # 0 = inactive, 1 = active
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="database_connections")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(String, index=True)  # Session-based for MVP
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    csat_score = Column(Integer, nullable=True)  # Customer satisfaction score (1-5)
    experiment_id = Column(Integer, nullable=True, index=True)  # For A/B testing
    
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
    intent = Column(String, nullable=True, index=True)  # Intent classification result
    agent_type = Column(String, nullable=True, index=True)  # Which agent handled this message
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # For tracking AI drafts that were edited by agents
    original_ai_content = Column(Text, nullable=True)  # Store original AI draft if edited
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class KnowledgeBase(Base):
    """
    Knowledge base articles for RAG implementation.
    Uses vector embeddings for semantic search.
    """
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String, index=True)
    tags = Column(String)  # Comma-separated for MVP
    embedding = Column(JSON, nullable=True)  # Vector embedding stored as JSON array
    source_id = Column(Integer, ForeignKey("knowledge_base_sources.id"), nullable=True)  # Link to source
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Feedback(Base):
    """
    Agent feedback on AI responses - critical for RLHF and model improvement.
    Tracks corrections, ratings, and provides training data.
    """
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
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
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    total_conversations = Column(Integer, default=0)
    resolved_conversations = Column(Integer, default=0)
    escalated_conversations = Column(Integer, default=0)
    avg_confidence_score = Column(Float, default=0.0)
    helpful_feedback_count = Column(Integer, default=0)
    not_helpful_feedback_count = Column(Integer, default=0)
    avg_response_time_seconds = Column(Float, default=0.0)


class EvaluationMetrics(Base):
    """
    Evaluation metrics for AI responses.
    Tracks BLEU scores, semantic similarity, and other quality metrics.
    """
    __tablename__ = "evaluation_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    bleu_score = Column(Float, nullable=True)  # BLEU score vs agent correction
    semantic_similarity = Column(Float, nullable=True)  # Cosine similarity of embeddings
    csat_score = Column(Integer, nullable=True)  # Customer satisfaction (1-5)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class TrainingData(Base):
    """
    Training data for model improvement.
    Stores feedback in training-ready format for retraining.
    """
    __tablename__ = "training_data"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback.id"), nullable=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    original_ai_response = Column(Text, nullable=False)  # Original AI response
    agent_correction = Column(Text, nullable=False)  # Agent's corrected version
    intent = Column(String, nullable=True)  # Intent classification
    processed = Column(Integer, default=0)  # 0 = not processed, 1 = processed for retraining
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)


class Correction(Base):
    """
    Tracks agent edits to AI drafts with diff information.
    """
    __tablename__ = "corrections"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    original_content = Column(Text, nullable=False)
    corrected_content = Column(Text, nullable=False)
    diff_summary = Column(Text, nullable=True)  # Human-readable diff summary
    reason = Column(Text, nullable=True)  # Why the correction was made
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AgentAction(Base):
    """
    Logs all agent actions for analytics and retraining.
    """
    __tablename__ = "agent_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    action_type = Column(String, nullable=False, index=True)  # approve, reject, edit, escalate
    action_data = Column(JSON, nullable=True)  # Additional action metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ModelVersion(Base):
    """
    Tracks model versions for A/B testing.
    """
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)  # Model configuration (embedding model, prompts, thresholds)
    is_active = Column(Integer, default=0)  # 0 = inactive, 1 = active
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Experiment(Base):
    """
    A/B testing experiments.
    """
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    variant_a_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True)
    variant_b_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True)
    traffic_split = Column(Float, default=0.5)  # 0.5 = 50/50 split
    status = Column(String, default="active")  # active, completed, paused
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

