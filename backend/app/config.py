"""
Configuration management for the application.
Loads defaults from environment variables and allows tenant-specific overrides.
"""
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


def get_default_llm_config() -> Dict:
    """
    Get default LLM configuration from environment variables.
    
    Returns:
        Dictionary with default LLM settings
    """
    return {
        "provider": os.getenv("DEFAULT_LLM_PROVIDER", "ollama"),
        "model": os.getenv("DEFAULT_LLM_MODEL", "llama3.2"),
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        "auto_send_threshold": float(os.getenv("AUTO_SEND_THRESHOLD", "0.65")),
        "tone": os.getenv("DEFAULT_TONE", "professional"),
    }


def get_tone_prompt(tone: str) -> str:
    """
    Get system prompt based on tone configuration.
    
    Args:
        tone: Tone setting (professional, casual, friendly)
    
    Returns:
        System prompt string
    """
    tone_prompts = {
        "professional": "You are a professional customer support assistant. Maintain a formal, courteous, and helpful tone. Use clear and concise language.",
        "casual": "You are a friendly and approachable customer support assistant. Use a relaxed, conversational tone while remaining helpful and informative.",
        "friendly": "You are a warm and helpful customer support assistant. Use a friendly, empathetic tone. Show genuine care for the customer's needs.",
    }
    
    return tone_prompts.get(tone.lower(), tone_prompts["professional"])

