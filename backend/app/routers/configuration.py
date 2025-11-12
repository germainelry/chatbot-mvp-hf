"""
Configuration API endpoints.
Manages tenant settings (LLM, KB, UI).
"""
from typing import Any, Dict, Optional

from app.database import get_db
from app.middleware.tenant_middleware import get_tenant_id_from_request
from app.middleware.auth import require_api_key
from app.models import Tenant, TenantConfiguration
from app.services.llm_providers.factory import get_provider, list_available_providers
from app.services.llm_providers.encryption import encrypt_llm_config, decrypt_llm_config
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()


class TenantConfigurationResponse(BaseModel):
    tenant_id: int
    llm_provider: str
    llm_model_name: str
    llm_config: Optional[Dict[str, Any]] = None
    embedding_model: str
    tone: str
    auto_send_threshold: float
    ui_config: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class TenantConfigurationUpdate(BaseModel):
    llm_provider: Optional[str] = None
    llm_model_name: Optional[str] = None
    llm_config: Optional[Dict[str, Any]] = None
    embedding_model: Optional[str] = None
    tone: Optional[str] = None
    auto_send_threshold: Optional[float] = None
    ui_config: Optional[Dict[str, Any]] = None


class LLMTestRequest(BaseModel):
    provider: str
    model: str
    config: Optional[Dict[str, Any]] = None


@router.get("/tenant/{tenant_id}", response_model=TenantConfigurationResponse)
async def get_tenant_configuration(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get tenant configuration."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    config = db.query(TenantConfiguration).filter(
        TenantConfiguration.tenant_id == tenant_id
    ).first()
    
    if not config:
        # Create default configuration
        config = TenantConfiguration(
            tenant_id=tenant_id,
            llm_provider="ollama",
            llm_model_name="llama3.2",
            embedding_model="all-MiniLM-L6-v2",
            tone="professional",
            auto_send_threshold=0.65
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    # Decrypt API keys before returning
    decrypted_config = decrypt_llm_config(config.llm_config) if config.llm_config else None
    
    return TenantConfigurationResponse(
        tenant_id=config.tenant_id,
        llm_provider=config.llm_provider,
        llm_model_name=config.llm_model_name,
        llm_config=decrypted_config,
        embedding_model=config.embedding_model,
        tone=config.tone,
        auto_send_threshold=config.auto_send_threshold,
        ui_config=config.ui_config
    )


@router.put("/tenant/{tenant_id}", response_model=TenantConfigurationResponse)
async def update_tenant_configuration(
    tenant_id: int,
    update: TenantConfigurationUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Update tenant configuration."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    config = db.query(TenantConfiguration).filter(
        TenantConfiguration.tenant_id == tenant_id
    ).first()
    
    if not config:
        # Create new configuration
        config = TenantConfiguration(tenant_id=tenant_id)
        db.add(config)
    
    # Update fields
    if update.llm_provider is not None:
        config.llm_provider = update.llm_provider
    if update.llm_model_name is not None:
        config.llm_model_name = update.llm_model_name
    if update.llm_config is not None:
        # Encrypt API keys before storing
        config.llm_config = encrypt_llm_config(update.llm_config)
    if update.embedding_model is not None:
        config.embedding_model = update.embedding_model
    if update.tone is not None:
        config.tone = update.tone
    if update.auto_send_threshold is not None:
        config.auto_send_threshold = update.auto_send_threshold
    if update.ui_config is not None:
        config.ui_config = update.ui_config
    
    db.commit()
    db.refresh(config)
    
    # Decrypt API keys before returning
    decrypted_config = decrypt_llm_config(config.llm_config) if config.llm_config else None
    
    return TenantConfigurationResponse(
        tenant_id=config.tenant_id,
        llm_provider=config.llm_provider,
        llm_model_name=config.llm_model_name,
        llm_config=decrypted_config,
        embedding_model=config.embedding_model,
        tone=config.tone,
        auto_send_threshold=config.auto_send_threshold,
        ui_config=config.ui_config
    )


@router.get("/llm-providers")
async def list_llm_providers():
    """List available LLM providers."""
    providers = list_available_providers()
    return {"providers": providers}


@router.get("/llm-models/{provider}")
async def list_llm_models(provider: str):
    """List available models for a provider."""
    provider_lower = provider.lower()
    
    # Static model lists for local providers
    static_models = {
        "ollama": ["llama3.2", "mistral", "llama2", "codellama", "llama3.1", "gemma"],
        "huggingface": [
            "mistralai/Mistral-7B-Instruct-v0.2",
            "meta-llama/Llama-2-7b-chat-hf",
            "microsoft/DialoGPT-medium"
        ],
        "huggingface_inference": [
            "mistralai/Mistral-7B-Instruct-v0.2",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "meta-llama/Llama-2-7b-chat-hf",
            "google/flan-t5-large",
            "microsoft/DialoGPT-large"
        ],
        "huggingface_api": [
            "mistralai/Mistral-7B-Instruct-v0.2",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "meta-llama/Llama-2-7b-chat-hf",
            "google/flan-t5-large",
            "microsoft/DialoGPT-large"
        ]
    }
    
    # Cloud provider models
    if provider_lower == "openai":
        return {
            "models": [
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k"
            ]
        }
    elif provider_lower == "anthropic":
        return {
            "models": [
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
        }
    
    # Return static models for local providers
    return {"models": static_models.get(provider_lower, [])}


@router.post("/test-llm")
async def test_llm_connection(
    test_request: LLMTestRequest,
    api_key: str = Depends(require_api_key)
):
    """Test LLM connection."""
    provider = get_provider(test_request.provider, {
        "model": test_request.model,
        **(test_request.config or {})
    })
    
    if not provider:
        raise HTTPException(status_code=400, detail=f"Provider {test_request.provider} not available")
    
    if not provider.is_available():
        raise HTTPException(status_code=400, detail=f"Provider {test_request.provider} is not available")
    
    try:
        # Test with a simple prompt
        response = await provider.generate_response(
            prompt="Say 'Hello, world!'",
            system_prompt="You are a helpful assistant."
        )
        return {
            "success": True,
            "message": "LLM connection successful",
            "test_response": response[:100]  # First 100 chars
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM test failed: {str(e)}")


@router.get("/embedding-models")
async def list_embedding_models():
    """List available embedding models from sentence-transformers."""
    models = [
        {
            "name": "all-MiniLM-L6-v2",
            "description": "Fast, efficient model (384 dimensions)",
            "use_case": "General purpose, fast embeddings"
        },
        {
            "name": "all-mpnet-base-v2",
            "description": "Higher quality model (768 dimensions)",
            "use_case": "Better accuracy, slower"
        },
        {
            "name": "paraphrase-MiniLM-L6-v2",
            "description": "Optimized for semantic similarity (384 dimensions)",
            "use_case": "Semantic similarity tasks"
        },
        {
            "name": "multi-qa-MiniLM-L6-cos-v1",
            "description": "Optimized for Q&A tasks (384 dimensions)",
            "use_case": "Question answering"
        }
    ]
    return {"models": models}

