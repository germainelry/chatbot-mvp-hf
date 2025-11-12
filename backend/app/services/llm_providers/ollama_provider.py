"""
Ollama LLM Provider implementation.
Supports local Ollama models (Llama, Mistral, etc.)
"""
import os
from typing import Dict, Optional

from app.services.llm_providers.base import LLMProvider

# Ollama will be optional - fallback if not available
OLLAMA_AVAILABLE = False
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    pass


class OllamaProvider(LLMProvider):
    """
    Ollama provider for local LLM inference.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Ollama provider.
        
        Args:
            config: Configuration dict with:
                - model: Model name (default: "llama3.2")
                - base_url: Ollama API base URL (default: "http://localhost:11434")
        """
        self.config = config or {}
        self.model = self.config.get("model", os.getenv("OLLAMA_MODEL", "llama3.2"))
        self.base_url = self.config.get("base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        
        # Set base URL if provided
        if self.base_url and OLLAMA_AVAILABLE:
            try:
                ollama.Client(host=self.base_url)
            except:
                pass
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> str:
        """
        Generate response using Ollama.
        """
        if not self.is_available():
            raise Exception("Ollama is not available")
        
        # Merge config
        merged_config = {**self.config, **(config or {})}
        model = merged_config.get("model", self.model)
        system_prompt = system_prompt or merged_config.get("system_prompt", "You are a helpful assistant.")
        
        try:
            # Use the base_url if configured
            if self.base_url and self.base_url != "http://localhost:11434":
                client = ollama.Client(host=self.base_url)
                response = client.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
            else:
                response = ollama.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
            
            return response['message']['content']
        except Exception as e:
            raise Exception(f"Ollama generation failed: {e}")
    
    def is_available(self) -> bool:
        """
        Check if Ollama is available.
        """
        if not OLLAMA_AVAILABLE:
            return False
        
        # Try to list models to verify connection
        try:
            if self.base_url and self.base_url != "http://localhost:11434":
                client = ollama.Client(host=self.base_url)
                client.list()  # Test connection
            else:
                ollama.list()  # Test connection
            return True
        except:
            return False
    
    def get_provider_name(self) -> str:
        return "ollama"
    
    def get_default_config(self) -> Dict:
        return {
            "model": self.model,
            "base_url": self.base_url
        }

