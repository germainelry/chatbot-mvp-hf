"""
Main FastAPI application for AI Customer Support System.
Implements RESTful API for chatbot, agent supervision, and analytics.
"""
import logging
import os

from app.database import init_db
from app.middleware.auth import check_api_key_for_docs
from app.middleware.demo_mode import DemoModeMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.routers import (
    agent_actions,
    ai,
    analytics,
    configuration,
    conversations,
    experiments,
    feedback,
    knowledge_base,
    knowledge_base_ingestion,
    messages,
)
from app.services.llm_service import OLLAMA_AVAILABLE, OLLAMA_MODEL
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
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
# Note: CORSMiddleware must be added first to ensure CORS headers are added to all responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Docs protection middleware
class DocsAuthMiddleware(BaseHTTPMiddleware):
    """Protect API documentation endpoints in production."""
    async def dispatch(self, request: Request, call_next):
        # Check if this is a docs endpoint
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            # If docs are disabled, return 404
            if not ENABLE_DOCS:
                response = Response(
                    content='{"detail":"Not Found"}',
                    status_code=404,
                    media_type="application/json"
                )
                # Ensure CORS headers are added even for error responses
                origin = request.headers.get("origin")
                if origin and origin in cors_origins:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                return response
            
            # If auth is enabled and we're in production, require API key
            if ENABLE_DOCS_AUTH and ENVIRONMENT == "production":
                # Check for API key in query parameter or header
                if not check_api_key_for_docs(request):
                    response = Response(
                        content='{"detail":"API key required. Add ?api_key=YOUR_KEY to URL or provide X-API-Key header."}',
                        status_code=401,
                        media_type="application/json"
                    )
                    # Ensure CORS headers are added even for error responses
                    origin = request.headers.get("origin")
                    if origin and origin in cors_origins:
                        response.headers["Access-Control-Allow-Origin"] = origin
                        response.headers["Access-Control-Allow-Credentials"] = "true"
                    return response
        
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

# CORS response middleware - ensures CORS headers are added to ALL responses
# This runs after other middleware to catch any responses that might have been missed
class CORSResponseMiddleware(BaseHTTPMiddleware):
    """Ensure CORS headers are added to all responses, even from middleware errors."""
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except HTTPException as http_exc:
            # Handle HTTPException specially - ensure CORS headers are added
            origin = request.headers.get("origin")
            response = JSONResponse(
                status_code=http_exc.status_code,
                content={"detail": http_exc.detail}
            )
            # Always add CORS headers if origin is present and in allowed list
            if origin:
                if origin in cors_origins:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
                else:
                    # Log if origin is not in allowed list for debugging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Origin {origin} not in allowed CORS origins: {cors_origins}")
            return response
        except Exception as e:
            # If an exception occurs, create a JSON response with CORS headers
            origin = request.headers.get("origin")
            response = JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {str(e)}"}
            )
            if origin and origin in cors_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
            return response
        
        # Ensure CORS headers are present on all responses
        origin = request.headers.get("origin")
        if origin and origin in cors_origins:
            # Always ensure CORS headers are present (even if CORS middleware added them)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
        
        # Log error responses for debugging
        if response.status_code >= 400:
            logger = logging.getLogger(__name__)
            logger.error(f"Error response {response.status_code} for {request.method} {request.url.path}")
        
        return response

app.add_middleware(CORSResponseMiddleware)

# Rate limiting middleware (applied before demo mode)
app.add_middleware(RateLimitMiddleware)

# Demo mode restrictions middleware
app.add_middleware(DemoModeMiddleware)

# Include routers
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(knowledge_base.router, prefix="/api/knowledge-base", tags=["Knowledge Base"])
app.include_router(knowledge_base_ingestion.router, prefix="/api/knowledge-base", tags=["Knowledge Base"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["Experiments"])
app.include_router(agent_actions.router, prefix="/api/agent-actions", tags=["Agent Actions"])
app.include_router(configuration.router, prefix="/api/config", tags=["Configuration"])

# Global exception handlers to ensure CORS headers are added to all error responses
# Handle FastAPI's HTTPException (most common)
@app.exception_handler(HTTPException)
async def fastapi_http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions and ensure CORS headers are present."""
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    # Add CORS headers if origin is in allowed list
    if origin and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    return response

# Handle Starlette's HTTPException (fallback)
@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions and ensure CORS headers are present."""
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    # Add CORS headers if origin is in allowed list
    if origin and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and ensure CORS headers are present."""
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )
    # Add CORS headers if origin is in allowed list
    if origin and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    return response

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions and ensure CORS headers are present."""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
    # Add CORS headers if origin is in allowed list
    if origin and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    # Optionally create tables if they don't exist
    # Set AUTO_CREATE_TABLES=false to disable (useful if managing schema via Supabase migrations)
    auto_create_tables = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"
    if auto_create_tables:
        init_db()
        print("[STARTUP] Database initialized (tables created/verified)")
    else:
        print("[STARTUP] Database connection verified (AUTO_CREATE_TABLES=false)")

    # Show available LLM providers
    from app.config import get_default_llm_config
    from app.services.llm_providers.factory import list_available_providers
    
    available_providers = list_available_providers()
    default_config = get_default_llm_config()
    
    print(f"[LLM] Available providers: {', '.join(available_providers) if available_providers else 'none'}")
    print(f"[LLM] Default provider: {default_config['provider']} ({default_config['model']})")
    
    # Legacy Ollama check for backward compatibility
    if OLLAMA_AVAILABLE:
        print(f"[LLM] Ollama also available - using {OLLAMA_MODEL}")

    print("[SERVER] Running at http://localhost:8000")
    print("[DOCS] API documentation available at http://localhost:8000/docs")

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
    from app.database import SessionLocal
    from sqlalchemy import text

    # Test database connection
    db_status = "disconnected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check API key configuration
    api_key_configured = bool(os.getenv("API_KEY"))
    
    llm_status = {
        "available": OLLAMA_AVAILABLE,
        "model": OLLAMA_MODEL if OLLAMA_AVAILABLE else "fallback",
        "type": "ollama" if OLLAMA_AVAILABLE else "rule-based"
    }
    
    overall_status = "healthy" if db_status == "connected" else "degraded"
    
    return {
        "status": overall_status,
        "database": db_status,
        "api": "operational",
        "api_key_configured": api_key_configured,
        "llm": llm_status,
        "environment": ENVIRONMENT
    }

