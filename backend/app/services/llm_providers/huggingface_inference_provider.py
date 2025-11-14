"""
HuggingFace Inference API Provider.
Uses HuggingFace Inference API for serverless LLM inference.
API key required - get free token at https://huggingface.co/settings/tokens
"""
import logging
import os
from typing import Dict, Optional

from app.services.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)

# HuggingFace Inference API will be optional
HF_INFERENCE_AVAILABLE = False
try:
    from huggingface_hub import InferenceClient
    HF_INFERENCE_AVAILABLE = True
except ImportError:
    pass


class HuggingFaceInferenceProvider(LLMProvider):
    """
    HuggingFace Inference API provider for serverless LLM inference.
    API key required - users get free monthly credits ($0.10 free tier, $2.00 PRO tier).
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
        # Support both HF_TOKEN (preferred) and HUGGINGFACE_API_KEY environment variables
        self.api_key = (
            self.config.get("api_key") 
            or os.getenv("HF_TOKEN") 
            or os.getenv("HUGGINGFACE_API_KEY")
        )
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
    
    def _is_instruction_model(self, model: str) -> bool:
        """
        Detect if model is instruction-tuned based on model name.
        Instruction models typically have keywords like 'instruct', 'chat', '-it', 'it-'
        """
        model_lower = model.lower()
        instruction_keywords = ['instruct', 'chat', '-it', 'it-']
        return any(keyword in model_lower for keyword in instruction_keywords)
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> str:
        """
        Generate response using HuggingFace Inference API.
        Automatically selects the correct method (chat vs text_generation) based on model type.
        """
        if not self.is_available():
            raise Exception("HuggingFace Inference API is not available. Install huggingface_hub: pip install huggingface_hub")
        
        if not self.client:
            raise Exception("HuggingFace InferenceClient not initialized. Install huggingface_hub: pip install huggingface_hub")
        
        # Merge config
        merged_config = {**self.config, **(config or {})}
        model = merged_config.get("model", self.model)
        system_prompt = system_prompt or merged_config.get("system_prompt", "You are a helpful assistant.")
        
        logger.info(
            f"[HuggingFace Inference] Generating response - Model: {model}, "
            f"Prompt Length: {len(prompt)}, Has System Prompt: {bool(system_prompt)}"
        )
        
        # Get API key from merged config (may override instance-level key)
        api_key = merged_config.get("api_key") or self.api_key
        if not api_key:
            # Try environment variables again in case they were set after initialization
            api_key = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        
        # Re-initialize client if API key changed or client doesn't exist
        if api_key and (not self.client or api_key != self.api_key):
            try:
                client_kwargs = {"token": api_key}
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                self.client = InferenceClient(**client_kwargs)
                self.api_key = api_key
                logger.info(f"[HuggingFace Inference] Client re-initialized with new API key")
            except Exception as e:
                logger.error(f"[HuggingFace Inference] Error re-initializing client: {e}")
        
        # Require API key for HuggingFace Inference API
        if not api_key:
            error_msg = (
                "HuggingFace API key is required. "
                "Get a free token at https://huggingface.co/settings/tokens "
                "(free tier: $0.10/month credits, PRO: $2.00/month credits)"
            )
            logger.error(f"[HuggingFace Inference] API key missing for model: {model}")
            raise Exception(error_msg)
        
        # Determine if this is an instruction-tuned model
        is_instruction = self._is_instruction_model(model)
        logger.debug(f"[HuggingFace Inference] Model type - Model: {model}, Is Instruction: {is_instruction}")
        
        try:
            # For instruction-tuned models, try chat_completion API first
            # This is the recommended method for models like Qwen2.5-7B-Instruct
            if is_instruction:
                try:
                    # Format messages for chat completion
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})
                    
                    # Use chat_completion API for instruction models
                    response = self.client.chat_completion(
                        messages=messages,
                        model=model,
                        max_tokens=merged_config.get("max_tokens", 512),
                        temperature=merged_config.get("temperature", 0.7),
                        top_p=merged_config.get("top_p", 0.95),
                    )
                    
                    # Handle chat completion response
                    if isinstance(response, dict):
                        if "choices" in response and len(response["choices"]) > 0:
                            choice = response["choices"][0]
                            if "message" in choice:
                                content = choice["message"].get("content", "")
                                return content.strip()
                            elif "text" in choice:
                                return str(choice["text"]).strip()
                        elif "generated_text" in response:
                            return str(response["generated_text"]).strip()
                        elif "text" in response:
                            return str(response["text"]).strip()
                    elif hasattr(response, 'choices') and len(response.choices) > 0:
                        choice = response.choices[0]
                        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                            return str(choice.message.content).strip()
                    elif isinstance(response, str):
                        return response.strip()
                    
                    # Fallback: try to extract text from response
                    return str(response).strip()
                    
                except Exception as chat_error:
                    # If chat_completion fails, fall back to text_generation
                    # Log the error but don't fail yet - try text_generation
                    error_msg = str(chat_error)
                    # Only fall back if it's not an auth/rate limit error
                    if "401" not in error_msg and "429" not in error_msg and "unauthorized" not in error_msg.lower():
                        # Fall through to text_generation
                        pass
                    else:
                        # Re-raise auth/rate limit errors immediately
                        raise
            
            # Use text_generation API for non-instruction models or as fallback
            # Format prompt for text generation
            if "qwen" in model.lower():
                # Qwen models work with simple prompt format
                formatted_prompt = prompt
                if system_prompt:
                    formatted_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                # For other models, use standard format
                if system_prompt:
                    formatted_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
                else:
                    formatted_prompt = prompt
            
            response = self.client.text_generation(
                formatted_prompt,
                model=model,
                max_new_tokens=merged_config.get("max_tokens", 512),
                temperature=merged_config.get("temperature", 0.7),
                top_p=merged_config.get("top_p", 0.95),
                return_full_text=False,
                do_sample=True
            )
            
            # Handle different response types
            if isinstance(response, str):
                return response.strip()
            elif hasattr(response, 'generated_text'):
                return str(response.generated_text).strip()
            elif isinstance(response, dict):
                # Handle dict responses
                if "generated_text" in response:
                    return str(response["generated_text"]).strip()
                elif "text" in response:
                    return str(response["text"]).strip()
            else:
                return str(response).strip()
                    
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Log the full original error for debugging
            logger.error(f"[HuggingFace Inference] API error - Model: {model}, Error Type: {error_type}, Error: {error_msg}")
            
            # Provide helpful error messages with actual error details
            # Check for specific error patterns first
            if "503" in error_msg or "loading" in error_msg.lower() or "model is currently loading" in error_msg.lower():
                raise Exception(f"Model {model} is currently loading. Please wait 30-60 seconds and try again. This is normal for models that haven't been used recently.")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise Exception(
                    f"Rate limit reached. Your API key credits may be exhausted. "
                    f"Check your usage at https://huggingface.co/settings/billing. "
                    f"Free tier: $0.10/month, PRO: $2.00/month"
                )
            elif "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid token" in error_msg.lower() or "authentication" in error_msg.lower():
                raise Exception(
                    f"Invalid or missing API key. Please check your HuggingFace API key. "
                    f"Make sure you've set HF_TOKEN or HUGGINGFACE_API_KEY environment variable, "
                    f"or provided it in the config. Get a token at https://huggingface.co/settings/tokens"
                )
            elif "404" in error_msg or "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise Exception(f"Model {model} not found. Check the model ID at https://huggingface.co/models")
            elif "not supported" in error_msg.lower() or "unsupported" in error_msg.lower():
                # This error might be misleading - show the actual error message
                raise Exception(
                    f"API error for model {model}: {error_msg}. "
                    f"This might indicate the model requires a different API method or your API key doesn't have access. "
                    f"Check the model page at https://huggingface.co/{model} and verify your API key at https://huggingface.co/settings/tokens"
                )
            else:
                # Return full error message for debugging - don't hide the actual error
                raise Exception(f"HuggingFace Inference API error for {model} ({error_type}): {error_msg}")
    
    def is_available(self) -> bool:
        """
        Check if HuggingFace Inference API is available.
        Requires huggingface_hub package and API key.
        """
        if not HF_INFERENCE_AVAILABLE:
            return False
        
        # API key is required
        return True
    
    def get_provider_name(self) -> str:
        return "huggingface_inference"
    
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
            "api_key": self.api_key if self.api_key else "",
            "base_url": self.base_url
        }

