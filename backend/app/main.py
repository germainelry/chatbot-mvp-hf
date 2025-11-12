"""
Main FastAPI application for AI Customer Support System.
Implements RESTful API for chatbot, agent supervision, and analytics.
"""
import os

from app.database import init_db
from app.middleware.auth import check_api_key_for_docs
from app.middleware.demo_mode import DemoModeMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.tenant_middleware import TenantMiddleware
from app.routers import (
    agent_actions,
    ai,
    analytics,
    configuration,
    conversations,
    database_rag,
    experiments,
    feedback,
    knowledge_base,
    knowledge_base_ingestion,
    messages,
    tenants,
)
from app.services.llm_service import OLLAMA_AVAILABLE, OLLAMA_MODEL
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

# Determine if docs should be enabled
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
# In production, check ENABLE_DOCS env var; in development, always enable
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").lower() == "true" if ENVIRONMENT == "production" else True
ENABLE_DOCS_AUTH = os.getenv("ENABLE_DOCS_AUTH", "true").lower() == "true"

# Initialize FastAPI app with conditional docs
app = FastAPI(
    title="AI Customer Support Assistant",
    description="Human-in-the-Loop AI chatbot system with agent supervision",
    version="1.0.0",
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None
)

# Get CORS origins - in production, use FRONTEND_URL; in development, use CORS_ORIGINS
FRONTEND_URL = os.getenv("FRONTEND_URL")
if ENVIRONMENT == "production" and FRONTEND_URL:
    # In production, only allow the specific frontend URL
    cors_origins = [FRONTEND_URL]
else:
    # In development, allow localhost origins
    cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

# CORS configuration with environment-based origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Tenant-ID", "X-Tenant-Slug"],
)

# Docs protection middleware
class DocsAuthMiddleware(BaseHTTPMiddleware):
    """Protect API documentation endpoints in production."""
    async def dispatch(self, request: Request, call_next):
        # Check if this is a docs endpoint
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            # If docs are disabled, return 404
            if not ENABLE_DOCS:
                return Response(
                    content='{"detail":"Not Found"}',
                    status_code=404,
                    media_type="application/json"
                )
            
            # If auth is enabled and we're in production, require API key
            if ENABLE_DOCS_AUTH and ENVIRONMENT == "production":
                # Check for API key in query parameter or header
                if not check_api_key_for_docs(request):
                    return Response(
                        content='{"detail":"API key required. Add ?api_key=YOUR_KEY to URL or provide X-API-Key header."}',
                        status_code=401,
                        media_type="application/json"
                    )
        
        return await call_next(request)

app.add_middleware(DocsAuthMiddleware)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Always set these security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Only add HSTS if using HTTPS (production)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy - configurable via environment variable
        # Set ENABLE_CSP=false to disable CSP (useful for debugging)
        enable_csp = os.getenv("ENABLE_CSP", "true").lower() == "true"
        
        if enable_csp:
            # For docs pages, allow CDN resources for Swagger UI
            # Note: 'unsafe-inline' and 'unsafe-eval' are required for Swagger UI
            # This is acceptable for documentation pages but not ideal for production APIs
            if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                    "script-src-elem 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "style-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
                    "font-src 'self' data: https://cdn.jsdelivr.net;"
                )
            else:
                # Stricter CSP for API endpoints (JSON responses don't need scripts/styles)
                # This prevents XSS attacks on API responses
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "script-src 'none'; "
                    "style-src 'none'; "
                    "img-src 'none'; "
                    "font-src 'none';"
                )
        
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware (applied before demo mode)
app.add_middleware(RateLimitMiddleware)

# Demo mode restrictions middleware
app.add_middleware(DemoModeMiddleware)

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

