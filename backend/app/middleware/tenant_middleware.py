"""
Tenant middleware for multi-tenant architecture.
Extracts tenant context from requests and validates tenant access.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from app.database import SessionLocal
from app.models import Tenant


def get_tenant_from_request(request: Request) -> Optional[str]:
    """
    Extract tenant identifier from request.
    Supports multiple methods:
    1. X-Tenant-ID header (preferred)
    2. X-Tenant-Slug header
    3. Query parameter: ?tenant_id=...
    4. Path parameter (if using subdomain routing)
    """
    # Method 1: Header
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id
    
    tenant_slug = request.headers.get("X-Tenant-Slug")
    if tenant_slug:
        return tenant_slug
    
    # Method 2: Query parameter
    tenant_id = request.query_params.get("tenant_id")
    if tenant_id:
        return tenant_id
    
    tenant_slug = request.query_params.get("tenant_slug")
    if tenant_slug:
        return tenant_slug
    
    # Method 3: Subdomain (if using subdomain routing)
    # host = request.headers.get("host", "")
    # if "." in host:
    #     subdomain = host.split(".")[0]
    #     return subdomain
    
    return None


def get_tenant_id(tenant_identifier: str, db: Session) -> Optional[int]:
    """
    Resolve tenant identifier to tenant ID.
    Supports both ID and slug.
    """
    # Try as ID first
    try:
        tenant_id = int(tenant_identifier)
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant:
            return tenant.id
    except ValueError:
        pass
    
    # Try as slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_identifier).first()
    if tenant:
        return tenant.id
    
    return None


def validate_tenant(tenant_id: int, db: Session) -> Tenant:
    """
    Validate tenant exists and is active.
    Raises HTTPException if invalid.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found"
        )
    
    if tenant.is_active != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant is inactive"
        )
    
    return tenant


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant context.
    Injects tenant_id into request.state for use in routes.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip tenant validation for health checks, docs, and tenant management
        skip_paths = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
        if request.url.path.startswith("/api/tenants"):
            # Tenant management endpoints don't require tenant context
            return await call_next(request)
        if request.url.path in skip_paths:
            return await call_next(request)
        
        # Extract tenant identifier
        tenant_identifier = get_tenant_from_request(request)
        
        if tenant_identifier:
            # Resolve to tenant ID
            db = SessionLocal()
            try:
                tenant_id = get_tenant_id(tenant_identifier, db)
                
                if tenant_id:
                    # Validate tenant
                    tenant = validate_tenant(tenant_id, db)
                    # Inject into request state
                    request.state.tenant_id = tenant_id
                    request.state.tenant = tenant
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Tenant not found: {tenant_identifier}"
                    )
            finally:
                db.close()
        else:
            # No tenant specified - use default tenant (ID=1) for backward compatibility
            # In production, you might want to require tenant for all requests
            db = SessionLocal()
            try:
                # Try to find default tenant by ID=1 or slug="default"
                default_tenant = db.query(Tenant).filter(
                    (Tenant.id == 1) | (Tenant.slug == "default")
                ).first()
                
                if default_tenant:
                    request.state.tenant_id = default_tenant.id
                    request.state.tenant = default_tenant
                else:
                    # No default tenant exists - create one on the fly for backward compatibility
                    try:
                        default_tenant = Tenant(
                            name="Default Tenant",
                            slug="default",
                            is_active=1
                        )
                        db.add(default_tenant)
                        db.commit()
                        db.refresh(default_tenant)
                        
                        # Create default configuration
                        from app.models import TenantConfiguration
                        default_config = TenantConfiguration(
                            tenant_id=default_tenant.id,
                            llm_provider="ollama",
                            llm_model_name="llama3.2",
                            embedding_model="all-MiniLM-L6-v2",
                            tone="professional",
                            auto_send_threshold=0.65
                        )
                        db.add(default_config)
                        db.commit()
                        
                        request.state.tenant_id = default_tenant.id
                        request.state.tenant = default_tenant
                    except Exception as e:
                        # If creation fails, allow request with None tenant_id
                        # Routes will need to handle this gracefully
                        request.state.tenant_id = None
                        request.state.tenant = None
            finally:
                db.close()
        
        response = await call_next(request)
        return response


def get_tenant_id_from_request(request: Request) -> Optional[int]:
    """
    Helper function to get tenant_id from request state.
    Use this in route handlers.
    """
    return getattr(request.state, "tenant_id", None)


def get_tenant_from_request_state(request: Request) -> Optional[Tenant]:
    """
    Helper function to get tenant object from request state.
    Use this in route handlers.
    """
    return getattr(request.state, "tenant", None)

