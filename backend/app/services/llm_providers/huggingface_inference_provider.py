"""
HuggingFace Inference API Provider.
Uses HuggingFace Inference API for free cloud-based LLM inference.
Free tier: 30,000 requests/month.
"""
import os
from typing import Dict, Optional
import httpx

from app.services.llm_providers.base import LLMProvider

# HuggingFace Inference API will be optional
HF_INFERENCE_AVAILABLE = False
try:
    from huggingface_hub import InferenceClient
    HF_INFERENCE_AVAILABLE = True
except ImportError:
    pass


class HuggingFaceInferenceProvider(LLMProvider):
    """
    HuggingFace Inference API provider for cloud-based LLM inference.
    Free tier available - no API key required for public models.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize HuggingFace Inference API provider.
        
        Args:
            config: Configuration dict with:
                - model: Model name (default: "mistralai/Mistral-7B-Instruct-v0.2")
                - api_key: Optional HuggingFace API key (for private models or higher rate limits)
                - base_url: Optional custom Inference API endpoint
        """
        self.config = config or {}
        self.model = self.config.get(
            "model",
            os.getenv("HF_INFERENCE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
        )
        self.api_key = self.config.get("api_key") or os.getenv("HUGGINGFACE_API_KEY")
        self.base_url = self.config.get("base_url") or os.getenv("HF_INFERENCE_BASE_URL")
        
        self.client = None
        if HF_INFERENCE_AVAILABLE:
            try:
                client_kwargs = {}
                if self.api_key:
                    client_kwargs["token"] = self.api_key
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                
                self.client = InferenceClient(**client_kwargs)
            except Exception as e:
                print(f"Error initializing HuggingFace Inference client: {e}")
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> str:
        """
        Generate response using HuggingFace Inference API.
        """
        if not self.is_available():
            raise Exception("HuggingFace Inference API is not available")
        
        # Merge config
        merged_config = {**self.config, **(config or {})}
        model = merged_config.get("model", self.model)
        system_prompt = system_prompt or merged_config.get("system_prompt", "You are a helpful assistant.")
        
        # Build full prompt
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
        
        try:
            # Use Inference API for text generation
            if self.client:
                response = self.client.text_generation(
                    full_prompt,
                    model=model,
                    max_new_tokens=merged_config.get("max_tokens", 512),
                    temperature=merged_config.get("temperature", 0.7),
                    top_p=merged_config.get("top_p", 0.95),
                    return_full_text=False  # Don't return the prompt
                )
                return response.strip()
            else:
                # Fallback to direct HTTP API call
                return await self._generate_via_http(full_prompt, model, merged_config)
        except Exception as e:
            raise Exception(f"HuggingFace Inference API generation failed: {e}")
    
    async def _generate_via_http(
        self,
        prompt: str,
        model: str,
        config: Dict
    ) -> str:
        """
        Fallback method using direct HTTP API calls.
        """
        api_url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": config.get("max_tokens", 512),
                "temperature": config.get("temperature", 0.7),
                "top_p": config.get("top_p", 0.95),
                "return_full_text": False
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    return result[0]["generated_text"].strip()
                elif "text" in result[0]:
                    return result[0]["text"].strip()
            elif isinstance(result, dict):
                if "generated_text" in result:
                    return result["generated_text"].strip()
                elif "text" in result:
                    return result["text"].strip()
            
            raise Exception("Unexpected response format from HuggingFace Inference API")
    
    def is_available(self) -> bool:
        """
        Check if HuggingFace Inference API is available.
        No API key required for public models.
        """
        if not HF_INFERENCE_AVAILABLE:
            return False
        
        # Client initialization is optional (works without API key for public models)
        return True
    
    def get_provider_name(self) -> str:
        return "huggingface_inference"
    
    def get_default_config(self) -> Dict:
        return {
            "model": self.model,
            "api_key": self.api_key if self.api_key else "",
            "base_url": self.base_url
        }

