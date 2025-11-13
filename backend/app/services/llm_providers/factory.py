"""
LLM Provider Factory.
Creates and manages LLM provider instances.
"""
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from app.services.llm_providers.base import LLMProvider

# Registry of available providers - lazy loaded to avoid circular imports
_PROVIDER_REGISTRY: Dict[str, type] = {}




# Provider metadata with detailed information
PROVIDER_METADATA = {
    "huggingface_inference": {
        "display_name": "HuggingFace Inference API",
        "description": "Serverless inference API for open-source models. One API key works for all models.",
        "cost": "Free tier available ($0.10/month credits)",
        "environments": ["cloud", "local"],
        "requires_api_key": True,
        "setup_complexity": "easy",
        "setup_steps": [
            "Sign up at huggingface.co (free account)",
            "Go to Settings → Access Tokens",
            "Create new token with 'Read' permission",
            "Copy token and paste below",
            "Select a model from the list and test connection"
        ],
        "signup_url": "https://huggingface.co/settings/tokens",
        "paid_models": [
            "mistralai/Mistral-7B-Instruct-v0.2",
            "meta-llama/Llama-3.1-8B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "meta-llama/Llama-3.2-1B-Instruct",
            "Qwen/Qwen2.5-1.5B-Instruct",
            "google/gemma-2b-it",
            "tiiuae/falcon-7b-instruct"
        ]
    },
    "openai": {
        "display_name": "OpenAI",
        "description": "Latest GPT models with API key",
        "cost": "Paid",
        "environments": ["cloud", "local"],
        "requires_api_key": True,
        "setup_complexity": "easy",
        "setup_steps": [
            "Sign up at platform.openai.com",
            "Navigate to API Keys section",
            "Create new secret key",
            "Enter key below and test"
        ],
        "signup_url": "https://platform.openai.com/api-keys",
        "paid_models": ["gpt-4o", "gpt-4o-mini"],
        "validation_regex": r"^sk-[a-zA-Z0-9]{48}$"
    },
    "anthropic": {
        "display_name": "Anthropic Claude",
        "description": "Claude 3.5 Sonnet and Haiku with API key",
        "cost": "Paid",
        "environments": ["cloud", "local"],
        "requires_api_key": True,
        "setup_complexity": "easy",
        "setup_steps": [
            "Sign up at console.anthropic.com",
            "Navigate to API Keys",
            "Create new key",
            "Enter key below and test"
        ],
        "signup_url": "https://console.anthropic.com/settings/keys",
        "paid_models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
        "validation_regex": r"^sk-ant-[a-zA-Z0-9\-_]{95,}$"
    }
}


def get_provider_metadata(provider_name: str) -> Optional[Dict]:
    """
    Get metadata for a provider.
    
    Args:
        provider_name: Name of the provider
        
    Returns:
        Provider metadata dict or None if not found
    """
    provider_lower = provider_name.lower()
    if provider_lower not in PROVIDER_METADATA:
        return None
    
    metadata = PROVIDER_METADATA[provider_lower].copy()
    return metadata


def _load_providers():
    """Lazy load providers to avoid circular imports."""
    if not _PROVIDER_REGISTRY:
        # Load HuggingFace Inference API provider (serverless, requires API key)
        try:
            from app.services.llm_providers.huggingface_inference_provider import (
                HuggingFaceInferenceProvider,
            )
            _PROVIDER_REGISTRY["huggingface_inference"] = HuggingFaceInferenceProvider
        except ImportError:
            pass
        
        # Load cloud providers (paid options)
        try:
            from app.services.llm_providers.openai_provider import OpenAIProvider
            _PROVIDER_REGISTRY["openai"] = OpenAIProvider
        except ImportError:
            pass
        
        try:
            from app.services.llm_providers.anthropic_provider import AnthropicProvider
            _PROVIDER_REGISTRY["anthropic"] = AnthropicProvider
        except ImportError:
            pass


def get_provider(provider_name: str, config: Optional[Dict] = None) -> Optional["LLMProvider"]:
    """
    Get an LLM provider instance.
    
    Args:
        provider_name: Name of the provider (e.g., "ollama", "huggingface")
        config: Provider-specific configuration
    
    Returns:
        LLMProvider instance or None if provider not found
    """
    _load_providers()
    provider_class = _PROVIDER_REGISTRY.get(provider_name.lower())
    
    if not provider_class:
        return None
    
    try:
        provider = provider_class(config or {})
        return provider if provider.is_available() else None
    except Exception as e:
        print(f"Error initializing provider {provider_name}: {e}")
        return None


def list_available_providers() -> list[str]:
    """
    List all registered provider names.
    
    Returns:
        List of provider names
    """
    _load_providers()
    return list(_PROVIDER_REGISTRY.keys())


def register_provider(name: str, provider_class: type):
    """
    Register a new provider class.
    
    Args:
        name: Provider name
        provider_class: Provider class that implements LLMProvider
    """
    _PROVIDER_REGISTRY[name.lower()] = provider_class

