"""
Ollama LLM Provider implementation.
Supports local Ollama models (Llama, Mistral, etc.)
"""
import os
import logging
from typing import Dict, Optional

from app.services.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)

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
        
        logger.info(
            f"[Ollama] Generating response - Model: {model}, "
            f"Base URL: {self.base_url}, Prompt Length: {len(prompt)}, "
            f"Has System Prompt: {bool(system_prompt)}"
        )
        
        try:
            logger.debug(f"[Ollama] Calling API - Model: {model}, Base URL: {self.base_url}")
            
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
            
            response_text = response['message']['content']
            logger.info(f"[Ollama] Generation successful - Model: {model}, Response Length: {len(response_text) if response_text else 0}")
            
            return response_text
        except Exception as e:
            error_msg = f"Ollama generation failed for model {model}: {e}"
            logger.error(f"[Ollama] {error_msg}", exc_info=True)
            raise Exception(error_msg)
    
    def is_available(self) -> bool:
        """
        Check if Ollama is available.
        Returns True if available, False otherwise.
        For detailed information, use get_availability_info().
        """
        available, _ = self.get_availability_info()
        return available
    
    def get_availability_info(self) -> tuple[bool, str]:
        """
        Check Ollama with detailed setup guidance.
        Returns tuple of (is_available, message).
        """
        from app.config import is_cloud_environment
        
        if not OLLAMA_AVAILABLE:
            return (False, 
                    "❌ Ollama Python package not installed.\n"
                    "Install with: pip install ollama")
        
        # Check for cloud environment
        if is_cloud_environment() and ("localhost" in self.base_url or "127.0.0.1" in self.base_url):
            return (False, 
                    "❌ Ollama requires localhost and won't work in cloud deployments.\n"
                    "💡 Try HuggingFace Inference instead (free, no setup):\n"
                    "   1. Select 'HuggingFace Inference API' as provider\n"
                    "   2. Choose a free model (Mistral 7B recommended)\n"
                    "   3. Test connection - works immediately!")
        
        # Try to connect and list models
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.ok:
                models = response.json().get("models", [])
                if not models:
                    return (False, 
                            "⚠️ Ollama is running but no models installed.\n"
                            "Run: ollama pull llama3.2")
                return (True, f"✅ Ollama running with {len(models)} model(s)")
            return (False, f"⚠️ Ollama returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            return (False, 
                    "❌ Can't connect to Ollama. Setup needed:\n"
                    "   1. Install from https://ollama.ai/download\n"
                    "   2. Start service: ollama serve\n"
                    "   3. Pull a model: ollama pull llama3.2\n"
                    "   4. Test connection again")
        except Exception as e:
            return (False, f"❌ Error: {str(e)}")
    
    def get_provider_name(self) -> str:
        return "ollama"
    
    def get_active_model(self) -> str:
        """
        Get the model currently being used by this provider.
        
        Returns:
            Model name string
        """
        return self.model
    
    def get_default_config(self) -> Dict:
        return {
            "model": self.model,
            "base_url": self.base_url
        }

