"""
LLM Provider Factory.
Creates and manages LLM provider instances.
"""
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from app.services.llm_providers.base import LLMProvider

# Registry of available providers - lazy loaded to avoid circular imports
_PROVIDER_REGISTRY: Dict[str, type] = {}


def _load_providers():
    """Lazy load providers to avoid circular imports."""
    if not _PROVIDER_REGISTRY:
        from app.services.llm_providers.huggingface_provider import HuggingFaceProvider
        from app.services.llm_providers.ollama_provider import OllamaProvider
        
        _PROVIDER_REGISTRY["ollama"] = OllamaProvider
        _PROVIDER_REGISTRY["huggingface"] = HuggingFaceProvider
        
        # Try to load cloud providers (optional)
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

