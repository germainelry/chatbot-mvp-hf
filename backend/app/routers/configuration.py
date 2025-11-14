"""
Configuration API endpoints.
Manages tenant settings (LLM, KB, UI).
"""
from typing import Any, Dict, Optional

from app.database import get_db
from app.middleware.auth import require_api_key
from app.models import TenantConfiguration
from app.services.llm_providers.encryption import decrypt_llm_config, encrypt_llm_config
from app.services.llm_providers.factory import get_provider, list_available_providers
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()


class ConfigurationResponse(BaseModel):
    llm_provider: str
    llm_model_name: str
    llm_config: Optional[Dict[str, Any]] = None
    embedding_model: str
    tone: str
    auto_send_threshold: float
    ui_config: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class ConfigurationUpdate(BaseModel):
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


@router.get("", response_model=ConfigurationResponse)
async def get_configuration(
    db: Session = Depends(get_db)
):
    """Get global configuration - OPTIMIZED for fast response."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from app.config import get_default_llm_config

        # OPTIMIZED: Simple, fast database query
        config = db.query(TenantConfiguration).first()
        
        if not config:
            # Create default configuration
            default_llm_config = get_default_llm_config()
            config = TenantConfiguration(
                llm_provider=default_llm_config["provider"],
                llm_model_name=default_llm_config["model"],
                embedding_model=default_llm_config["embedding_model"],
                tone=default_llm_config["tone"],
                auto_send_threshold=default_llm_config["auto_send_threshold"]
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        
        # OPTIMIZED: Skip provider migration check - only do on startup or update
        # This saves ~200-500ms per request by avoiding expensive provider enumeration
        
        # Decrypt API keys before returning
        decrypted_config = None
        if config.llm_config and isinstance(config.llm_config, dict):
            try:
                decrypted_config = decrypt_llm_config(config.llm_config)
            except Exception:
                # Silently ignore decryption errors
                pass
        
        # Build response with safe defaults
        auto_send_threshold = 0.65
        if config.auto_send_threshold is not None:
            try:
                auto_send_threshold = float(config.auto_send_threshold)
            except (ValueError, TypeError):
                pass
        
        return ConfigurationResponse(
            llm_provider=config.llm_provider or "huggingface_inference",
            llm_model_name=config.llm_model_name or "mistralai/Mistral-7B-Instruct-v0.2",
            llm_config=decrypted_config,
            embedding_model=config.embedding_model or "all-MiniLM-L6-v2",
            tone=config.tone or "professional",
            auto_send_threshold=auto_send_threshold,
            ui_config=config.ui_config if config.ui_config else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.put("", response_model=ConfigurationResponse)
async def update_configuration(
    update: ConfigurationUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Update global configuration."""
    # Get or create a single global configuration
    config = db.query(TenantConfiguration).first()
    
    if not config:
        # Create new configuration
        from app.config import get_default_llm_config
        default_llm_config = get_default_llm_config()
        config = TenantConfiguration(
            llm_provider=default_llm_config["provider"],
            llm_model_name=default_llm_config["model"],
            embedding_model=default_llm_config["embedding_model"],
            tone=default_llm_config["tone"],
            auto_send_threshold=default_llm_config["auto_send_threshold"]
        )
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
    
    return ConfigurationResponse(
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
    
    # HuggingFace Inference models (require API key)
    if provider_lower == "huggingface_inference":
        return {
            "models": [
                "mistralai/Mistral-7B-Instruct-v0.2",
                "meta-llama/Llama-3.1-8B-Instruct",
                "Qwen/Qwen2.5-7B-Instruct",
                "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "meta-llama/Llama-3.2-1B-Instruct",
                "Qwen/Qwen2.5-1.5B-Instruct",
                "google/gemma-2b-it",
                "tiiuae/falcon-7b-instruct"
            ]
        }
    
    # OpenAI models
    elif provider_lower == "openai":
        return {"models": ["gpt-4o", "gpt-4o-mini"]}
    
    # Anthropic models
    elif provider_lower == "anthropic":
        return {"models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]}
    
    return {"models": []}


@router.post("/test-llm")
async def test_llm_connection(
    test_request: LLMTestRequest,
    api_key: str = Depends(require_api_key)
):
    """Test LLM connection with detailed error messages and model information."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(
        f"[LLM Test] Testing connection - Provider: {test_request.provider}, "
        f"Model: {test_request.model}"
    )
    
    provider_config = {
        "model": test_request.model,
        **(test_request.config or {})
    }
    
    provider = get_provider(test_request.provider, provider_config)
    
    if not provider:
        logger.warning(
            f"[LLM Test] Provider not available - Provider: {test_request.provider}, "
            f"Model: {test_request.model}"
        )
        raise HTTPException(status_code=400, detail=f"Provider {test_request.provider} not available")
    
    # Get actual model being used
    actual_model = test_request.model
    if hasattr(provider, 'get_active_model'):
        try:
            actual_model = provider.get_active_model()
        except:
            pass
    elif hasattr(provider, 'model'):
        actual_model = getattr(provider, 'model', test_request.model)
    elif hasattr(provider, 'model_name'):
        actual_model = getattr(provider, 'model_name', test_request.model)
    
    # Check availability
    if hasattr(provider, 'get_availability_info'):
        available, message = provider.get_availability_info()
        if not available:
            logger.warning(
                f"[LLM Test] Provider not available - Provider: {test_request.provider}, "
                f"Model: {test_request.model}, Message: {message}"
            )
            raise HTTPException(status_code=400, detail=message)
    elif not provider.is_available():
        logger.warning(
            f"[LLM Test] Provider not available - Provider: {test_request.provider}, "
            f"Model: {test_request.model}"
        )
        raise HTTPException(status_code=400, detail=f"Provider {test_request.provider} is not available")
    
    try:
        # Test with a simple prompt
        logger.info(
            f"[LLM Test] Generating test response - Provider: {test_request.provider}, "
            f"Model: {actual_model}"
        )
        response = await provider.generate_response(
            prompt="Say 'Hello, world!'",
            system_prompt="You are a helpful assistant."
        )
        
        response_preview = response[:100] if response else ""
        logger.info(
            f"[LLM Test] Test successful - Provider: {test_request.provider}, "
            f"Model: {actual_model}, Response Length: {len(response) if response else 0}"
        )
        
        return {
            "success": True,
            "message": f"Connection successful to {actual_model}",
            "test_response": response_preview,
            "provider": test_request.provider,
            "configured_model": test_request.model,
            "actual_model_used": actual_model,
            "model_match": (actual_model == test_request.model),
            "response_length": len(response) if response else 0
        }
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        logger.error(
            f"[LLM Test] Test failed - Provider: {test_request.provider}, "
            f"Model: {actual_model}, Error Type: {error_type}, Error: {error_msg}",
            exc_info=True
        )
        # Return the full error message (already formatted by the provider)
        raise HTTPException(
            status_code=500, 
            detail=f"Model {actual_model}: {error_msg}"
        )


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


@router.get("/environment")
async def get_environment_info():
    """Get current environment and recommended defaults."""
    from app.config import get_default_llm_config
    
    defaults = get_default_llm_config()
    
    return {
        "default_provider": defaults["provider"],
        "default_model": defaults["model"]
    }


@router.get("/llm-provider-info/{provider}")
async def get_llm_provider_info(provider: str):
    """Get detailed information about an LLM provider including available models."""
    from app.services.llm_providers.factory import (
        get_provider_metadata,
        list_available_providers,
    )

    # Check if provider exists in available providers
    available_providers = list_available_providers()
    if provider.lower() not in [p.lower() for p in available_providers]:
        # Return empty/default metadata instead of 404 to avoid error logs
        # Frontend will handle missing provider gracefully
        return {
            "display_name": provider,
            "description": f"Provider {provider} is not available",
            "cost": "Unknown",
            "environments": [],
            "requires_api_key": False,
            "setup_complexity": "unknown",
            "setup_steps": [],
            "paid_models": []
        }
    
    metadata = get_provider_metadata(provider)
    if not metadata:
        # Fallback to default if metadata not found
        return {
            "display_name": provider,
            "description": f"Provider {provider} configuration",
            "cost": "Unknown",
            "environments": [],
            "requires_api_key": False,
            "setup_complexity": "unknown",
            "setup_steps": [],
            "paid_models": []
        }
    
    return metadata


# Note: GET /available-models/{provider} endpoint removed as duplicate of /llm-models/{provider}

