"""
Tenant management endpoints.
Handles tenant CRUD operations for admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Tenant, TenantConfiguration
from app.middleware.auth import require_api_key

router = APIRouter()


class TenantCreate(BaseModel):
    name: str
    slug: str
    is_active: int = 1


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[int] = None


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=TenantResponse)
async def create_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Create a new tenant."""
    # Check if slug already exists
    existing = db.query(Tenant).filter(Tenant.slug == tenant.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Tenant with slug '{tenant.slug}' already exists")
    
    db_tenant = Tenant(
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active
    )
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    
    # Create default configuration for tenant
    default_config = TenantConfiguration(
        tenant_id=db_tenant.id,
        llm_provider="ollama",
        llm_model_name="llama3.2",
        embedding_model="all-MiniLM-L6-v2",
        tone="professional",
        auto_send_threshold=0.65
    )
    db.add(default_config)
    db.commit()
    
    return TenantResponse(
        id=db_tenant.id,
        name=db_tenant.name,
        slug=db_tenant.slug,
        is_active=db_tenant.is_active,
        created_at=db_tenant.created_at,
        updated_at=db_tenant.updated_at
    )


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    db: Session = Depends(get_db)
):
    """List all tenants."""
    tenants = db.query(Tenant).all()
    return [
        TenantResponse(
            id=t.id,
            name=t.name,
            slug=t.slug,
            is_active=t.is_active,
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in tenants
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at
    )


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    update: TenantUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Update a tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if update.name is not None:
        tenant.name = update.name
    if update.slug is not None:
        # Check if slug already exists (excluding current tenant)
        existing = db.query(Tenant).filter(Tenant.slug == update.slug, Tenant.id != tenant_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Tenant with slug '{update.slug}' already exists")
        tenant.slug = update.slug
    if update.is_active is not None:
        tenant.is_active = update.is_active
    
    tenant.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tenant)
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at
    )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Delete a tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    db.delete(tenant)
    db.commit()
    
    return {"message": "Tenant deleted successfully"}

