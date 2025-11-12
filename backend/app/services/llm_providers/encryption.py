"""
Encryption utility for LLM API keys.
Uses Fernet symmetric encryption to secure API keys in database.
"""
import os
from cryptography.fernet import Fernet
from typing import Optional

# Get encryption key from environment variable
_encryption_key = os.getenv("LLM_ENCRYPTION_KEY")

# Generate a key if not provided (for development only - should be set in production)
if not _encryption_key:
    # In production, this should fail if key is not set
    if os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("ENVIRONMENT") == "production":
        raise ValueError("LLM_ENCRYPTION_KEY environment variable must be set in production")
    # For development, generate a temporary key (will be different each time)
    _encryption_key = Fernet.generate_key().decode()
    print("⚠️  WARNING: LLM_ENCRYPTION_KEY not set. Generated temporary key for development only.")

ENCRYPTION_KEY = _encryption_key


def get_fernet() -> Fernet:
    """Get Fernet cipher instance."""
    key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key before storing in database.
    
    Args:
        api_key: Plain text API key
    
    Returns:
        Encrypted API key string
    """
    if not api_key:
        return ""
    
    try:
        f = get_fernet()
        encrypted = f.encrypt(api_key.encode())
        return encrypted.decode()
    except Exception as e:
        print(f"Error encrypting API key: {e}")
        raise ValueError(f"Failed to encrypt API key: {e}")


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key from database.
    
    Args:
        encrypted_key: Encrypted API key string
    
    Returns:
        Decrypted plain text API key
    """
    if not encrypted_key:
        return ""
    
    try:
        f = get_fernet()
        decrypted = f.decrypt(encrypted_key.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"Error decrypting API key: {e}")
        # If decryption fails, return empty string (key may be unencrypted from old data)
        return ""


def encrypt_llm_config(config: dict) -> dict:
    """
    Encrypt API keys in LLM configuration dictionary.
    
    Args:
        config: LLM configuration dictionary that may contain 'api_key'
    
    Returns:
        Configuration dictionary with encrypted API key
    """
    if not config:
        return config
    
    encrypted_config = config.copy()
    
    # Encrypt api_key if present
    if "api_key" in encrypted_config and encrypted_config["api_key"]:
        # Check if already encrypted (starts with 'gAAAAAB' for Fernet)
        if not encrypted_config["api_key"].startswith("gAAAAAB"):
            encrypted_config["api_key"] = encrypt_api_key(encrypted_config["api_key"])
    
    return encrypted_config


def decrypt_llm_config(config: dict) -> dict:
    """
    Decrypt API keys in LLM configuration dictionary.
    
    Args:
        config: LLM configuration dictionary with encrypted 'api_key'
    
    Returns:
        Configuration dictionary with decrypted API key
    """
    if not config:
        return config
    
    decrypted_config = config.copy()
    
    # Decrypt api_key if present
    if "api_key" in decrypted_config and decrypted_config["api_key"]:
        decrypted_config["api_key"] = decrypt_api_key(decrypted_config["api_key"])
    
    return decrypted_config

