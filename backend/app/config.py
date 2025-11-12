"""
Configuration management for the application.
Loads defaults from environment variables and allows tenant-specific overrides.
"""
import os
import sys
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()


def validate_required_env_vars():
    """
    Validate required environment variables on startup.
    Fails fast if critical variables are missing in production.
    """
    is_production = os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("ENVIRONMENT") == "production"
    
    if is_production:
        required_vars = ["DATABASE_URL", "API_KEY", "FRONTEND_URL"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"ERROR: Missing required environment variables in production: {', '.join(missing_vars)}")
            sys.exit(1)
        
        # Warn if encryption keys are missing
        if not os.getenv("LLM_ENCRYPTION_KEY"):
            print("WARNING: LLM_ENCRYPTION_KEY not set. API keys will not be encrypted!")
        
        if not os.getenv("DB_ENCRYPTION_KEY"):
            print("WARNING: DB_ENCRYPTION_KEY not set. Database connection strings will not be encrypted!")
        
        # Validate API key strength (should be at least 32 characters)
        api_key = os.getenv("API_KEY", "")
        if len(api_key) < 32:
            print("WARNING: API_KEY is too short. For security, use at least 32 characters.")
            print("  Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        
        # Validate FRONTEND_URL format
        frontend_url = os.getenv("FRONTEND_URL", "")
        if frontend_url and not (frontend_url.startswith("http://") or frontend_url.startswith("https://")):
            print("WARNING: FRONTEND_URL should start with http:// or https://")
        
        # Check ENABLE_DOCS_AUTH setting
        enable_docs_auth = os.getenv("ENABLE_DOCS_AUTH", "true").lower() == "true"
        if not enable_docs_auth:
            print("WARNING: ENABLE_DOCS_AUTH is false. API documentation will be publicly accessible!")


# Validate on import (for production)
validate_required_env_vars()


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

