"""
Anthropic Claude LLM Provider implementation.
Supports Claude models via Anthropic API.
"""
import os
from typing import Dict, Optional

from app.services.llm_providers.base import LLMProvider

# Anthropic will be optional - fallback if not available
ANTHROPIC_AVAILABLE = False
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass


class AnthropicProvider(LLMProvider):
    """
    Anthropic provider for cloud-based LLM inference.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Anthropic provider.
        
        Args:
            config: Configuration dict with:
                - model: Model name (default: "claude-3-5-sonnet-20241022")
                - api_key: Anthropic API key (required)
        """
        self.config = config or {}
        self.model = self.config.get("model", os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"))
        self.api_key = self.config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing Anthropic client: {e}")
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> str:
        """
        Generate response using Anthropic API.
        """
        if not self.is_available():
            raise Exception("Anthropic is not available")
        
        # Merge config
        merged_config = {**self.config, **(config or {})}
        model = merged_config.get("model", self.model)
        system_prompt = system_prompt or merged_config.get("system_prompt", "You are a helpful assistant.")
        
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=merged_config.get("max_tokens", 1024),
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=merged_config.get("temperature", 0.7)
            )
            
            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return ""
        except Exception as e:
            raise Exception(f"Anthropic generation failed: {e}")
    
    def is_available(self) -> bool:
        """
        Check if Anthropic is available and configured.
        """
        if not ANTHROPIC_AVAILABLE:
            return False
        
        if not self.api_key:
            return False
        
        if not self.client:
            return False
        
        return True
    
    def get_provider_name(self) -> str:
        return "anthropic"
    
    def get_default_config(self) -> Dict:
        return {
            "model": self.model,
            "api_key": self.api_key if self.api_key else ""
        }

