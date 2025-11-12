"""
Base LLM Provider interface.
All LLM providers must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Each provider (Ollama, Hugging Face, etc.) implements this interface.
    """
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt/message
            system_prompt: System prompt for context
            config: Provider-specific configuration (model name, temperature, etc.)
        
        Returns:
            Generated response text
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and configured.
        
        Returns:
            True if provider is available, False otherwise
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the provider.
        
        Returns:
            Provider name (e.g., "ollama", "huggingface")
        """
        pass
    
    def get_default_config(self) -> Dict:
        """
        Get default configuration for this provider.
        Can be overridden by subclasses.
        
        Returns:
            Default configuration dictionary
        """
        return {}

