"""
OpenAI LLM Provider implementation.
Supports GPT-4, GPT-3.5, and other OpenAI models via API.
"""
import os
from typing import Dict, Optional

from app.services.llm_providers.base import LLMProvider

# OpenAI will be optional - fallback if not available
OPENAI_AVAILABLE = False
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    pass


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider for cloud-based LLM inference.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            config: Configuration dict with:
                - model: Model name (default: "gpt-3.5-turbo")
                - api_key: OpenAI API key (required)
                - base_url: Optional custom base URL (for Azure OpenAI)
        """
        self.config = config or {}
        self.model = self.config.get("model", os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
        self.api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.base_url = self.config.get("base_url") or os.getenv("OPENAI_BASE_URL")
        
        self.client = None
        if OPENAI_AVAILABLE and self.api_key:
            try:
                client_kwargs = {"api_key": self.api_key}
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                self.client = OpenAI(**client_kwargs)
            except Exception as e:
                print(f"Error initializing OpenAI client: {e}")
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> str:
        """
        Generate response using OpenAI API.
        """
        if not self.is_available():
            raise Exception("OpenAI is not available")
        
        # Merge config
        merged_config = {**self.config, **(config or {})}
        model = merged_config.get("model", self.model)
        system_prompt = system_prompt or merged_config.get("system_prompt", "You are a helpful assistant.")
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=merged_config.get("temperature", 0.7),
                max_tokens=merged_config.get("max_tokens", 1000)
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI generation failed: {e}")
    
    def is_available(self) -> bool:
        """
        Check if OpenAI is available and configured.
        """
        if not OPENAI_AVAILABLE:
            return False
        
        if not self.api_key:
            return False
        
        if not self.client:
            return False
        
        # Try a simple API call to verify connection
        try:
            # Just check if client is initialized, don't make actual call
            return True
        except:
            return False
    
    def get_provider_name(self) -> str:
        return "openai"
    
    def get_default_config(self) -> Dict:
        return {
            "model": self.model,
            "api_key": self.api_key if self.api_key else "",
            "base_url": self.base_url
        }

