"""
Hugging Face Transformers LLM Provider implementation.
Supports local inference using transformers library.
"""
from typing import Dict, Optional
import os

from app.services.llm_providers.base import LLMProvider

# Hugging Face will be optional
HF_AVAILABLE = False
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
    HF_AVAILABLE = True
except ImportError:
    pass


class HuggingFaceProvider(LLMProvider):
    """
    Hugging Face provider for local LLM inference.
    Uses transformers library for on-device inference.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Hugging Face provider.
        
        Args:
            config: Configuration dict with:
                - model: Model name (default: "mistralai/Mistral-7B-Instruct-v0.2")
                - device: Device to use ("cpu", "cuda", "auto")
                - max_length: Maximum generation length
        """
        self.config = config or {}
        self.model_name = self.config.get(
            "model",
            os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
        )
        self.device = self.config.get("device", "auto")
        self.max_length = self.config.get("max_length", 512)
        
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        
        # Lazy loading - models are loaded on first use
        self._initialized = False
    
    def _initialize(self):
        """Lazy initialization of model."""
        if self._initialized or not HF_AVAILABLE:
            return
        
        try:
            # Determine device
            if self.device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = self.device
            
            # Load tokenizer and model
            print(f"Loading Hugging Face model: {self.model_name} on {device}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                low_cpu_mem_usage=True
            )
            
            if device == "cpu":
                self.model = self.model.to(device)
            
            # Create pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1,
                max_length=self.max_length
            )
            
            self._initialized = True
            print(f"✅ Hugging Face model loaded successfully")
        except Exception as e:
            print(f"Error loading Hugging Face model: {e}")
            self._initialized = False
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> str:
        """
        Generate response using Hugging Face transformers.
        """
        if not self.is_available():
            raise Exception("Hugging Face is not available")
        
        # Initialize if needed
        if not self._initialized:
            self._initialize()
        
        if not self._initialized or not self.pipeline:
            raise Exception("Failed to initialize Hugging Face model")
        
        # Merge config
        merged_config = {**self.config, **(config or {})}
        max_length = merged_config.get("max_length", self.max_length)
        
        # Build full prompt
        system_prompt = system_prompt or "You are a helpful assistant."
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
        
        try:
            # Generate response
            results = self.pipeline(
                full_prompt,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Extract generated text
            generated_text = results[0]['generated_text']
            
            # Remove the prompt from the response
            response = generated_text[len(full_prompt):].strip()
            
            return response
        except Exception as e:
            raise Exception(f"Hugging Face generation failed: {e}")
    
    def is_available(self) -> bool:
        """
        Check if Hugging Face is available.
        """
        if not HF_AVAILABLE:
            return False
        
        # Try to initialize (this will fail if model can't be loaded)
        if not self._initialized:
            try:
                self._initialize()
            except:
                return False
        
        return self._initialized
    
    def get_provider_name(self) -> str:
        return "huggingface"
    
    def get_default_config(self) -> Dict:
        return {
            "model": self.model_name,
            "device": self.device,
            "max_length": self.max_length
        }

