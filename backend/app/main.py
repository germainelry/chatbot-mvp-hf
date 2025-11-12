"""
Main FastAPI application for AI Customer Support System.
Implements RESTful API for chatbot, agent supervision, and analytics.
"""
from app.database import init_db
from app.routers import ai, analytics, conversations, feedback, knowledge_base, messages, experiments, agent_actions
from app.routers import configuration, knowledge_base_ingestion, database_rag, tenants
from app.services.llm_service import OLLAMA_AVAILABLE, OLLAMA_MODEL
from app.middleware.tenant_middleware import TenantMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="AI Customer Support Assistant",
    description="Human-in-the-Loop AI chatbot system with agent supervision",
    version="1.0.0"
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant middleware for multi-tenant support
app.add_middleware(TenantMiddleware)

# Include routers
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(knowledge_base.router, prefix="/api/knowledge-base", tags=["Knowledge Base"])
app.include_router(knowledge_base_ingestion.router, prefix="/api/knowledge-base", tags=["Knowledge Base"])
app.include_router(database_rag.router, prefix="/api/knowledge-base", tags=["Knowledge Base"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["Experiments"])
app.include_router(agent_actions.router, prefix="/api/agent-actions", tags=["Agent Actions"])
app.include_router(configuration.router, prefix="/api/config", tags=["Configuration"])
app.include_router(tenants.router, prefix="/api/tenants", tags=["Tenants"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    print("🚀 Database initialized")
    
    # Show LLM status
    if OLLAMA_AVAILABLE:
        print(f"🤖 Ollama available - using {OLLAMA_MODEL}")
    else:
        print("⚠️  Ollama not available - using fallback responses")
    
    print("📊 Server running at http://localhost:8000")
    print("📖 API docs available at http://localhost:8000/docs")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "AI Customer Support Assistant API",
        "version": "1.0.0",
        "llm_mode": "ollama" if OLLAMA_AVAILABLE else "fallback"
    }

@app.get("/health")
async def health_check():
    """Detailed health check for monitoring."""
    llm_status = {
        "available": OLLAMA_AVAILABLE,
        "model": OLLAMA_MODEL if OLLAMA_AVAILABLE else "fallback",
        "type": "ollama" if OLLAMA_AVAILABLE else "rule-based"
    }
    
    return {
        "status": "healthy",
        "database": "connected",
        "api": "operational",
        "llm": llm_status
    }

