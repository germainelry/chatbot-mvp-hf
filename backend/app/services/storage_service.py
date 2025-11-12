"""
Supabase Storage service for file uploads.
Handles file storage in Supabase Storage buckets.
"""
import os
from typing import Optional
from fastapi import UploadFile

# Try to import Supabase (optional dependency)
SUPABASE_AVAILABLE = False
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    pass

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# Signed URL expiration in seconds (default: 1 year for knowledge base files)
SIGNED_URL_EXPIRATION = int(os.getenv("SIGNED_URL_EXPIRATION", "31536000"))  # 1 year

_supabase_client: Optional[object] = None


def get_supabase_client() -> Optional[object]:
    """Get or create Supabase client."""
    global _supabase_client
    
    if not SUPABASE_AVAILABLE:
        return None
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    
    if _supabase_client is None:
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"Error creating Supabase client: {e}")
            return None
    
    return _supabase_client


async def upload_file_to_supabase(
    file: UploadFile,
    bucket_name: str,
    tenant_id: Optional[int] = None,
    folder: Optional[str] = None,
    use_signed_url: bool = True
) -> Optional[str]:
    """
    Upload a file to Supabase Storage.
    
    Args:
        file: FastAPI UploadFile object
        bucket_name: Name of the storage bucket
        tenant_id: Optional tenant ID for folder organization
        folder: Optional folder path within bucket
        use_signed_url: If True, generate signed URL (for private buckets). If False, use public URL (for public buckets).
    
    Returns:
        Signed URL or public URL of uploaded file, or None if upload failed
    """
    if not SUPABASE_AVAILABLE:
        raise Exception("Supabase package not installed. Install with: pip install supabase")
    
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase client not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
    
    # Build file path
    file_path_parts = []
    if tenant_id:
        file_path_parts.append(f"tenant_{tenant_id}")
    if folder:
        file_path_parts.append(folder)
    file_path_parts.append(file.filename)
    file_path = "/".join(file_path_parts)
    
    # Read file content
    file_content = await file.read()
    
    try:
        # Upload file
        response = client.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type or "application/octet-stream"}
        )
        
        # Generate signed URL for private buckets, or public URL for public buckets
        if use_signed_url:
            # For private buckets, generate a signed URL
            signed_url_response = client.storage.from_(bucket_name).create_signed_url(
                path=file_path,
                expires_in=SIGNED_URL_EXPIRATION
            )
            signed_url = signed_url_response.get("signedURL")
            if not signed_url:
                raise Exception("Failed to generate signed URL. Make sure you're using the service role key (not anon key) for private buckets.")
            return signed_url
        else:
            # For public buckets, use public URL
            public_url_response = client.storage.from_(bucket_name).get_public_url(file_path)
            return public_url_response
        
    except Exception as e:
        print(f"Error uploading file to Supabase: {e}")
        raise Exception(f"Failed to upload file: {e}")


def delete_file_from_supabase(
    file_path: str,
    bucket_name: str
) -> bool:
    """
    Delete a file from Supabase Storage.
    
    Args:
        file_path: Path to file in bucket
        bucket_name: Name of the storage bucket
    
    Returns:
        True if deletion successful, False otherwise
    """
    if not SUPABASE_AVAILABLE:
        return False
    
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        client.storage.from_(bucket_name).remove([file_path])
        return True
    except Exception as e:
        print(f"Error deleting file from Supabase: {e}")
        return False


def get_signed_url(
    file_path: str,
    bucket_name: str,
    expires_in: Optional[int] = None
) -> Optional[str]:
    """
    Get a signed URL for a file in Supabase Storage.
    Useful for generating new signed URLs when stored URLs expire.
    
    Args:
        file_path: Path to file in bucket
        bucket_name: Name of the storage bucket
        expires_in: URL expiration time in seconds (default: uses SIGNED_URL_EXPIRATION env var or 1 year)
    
    Returns:
        Signed URL, or None if failed
    """
    if not SUPABASE_AVAILABLE:
        return None
    
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        expiration = expires_in if expires_in is not None else SIGNED_URL_EXPIRATION
        response = client.storage.from_(bucket_name).create_signed_url(
            path=file_path,
            expires_in=expiration
        )
        signed_url = response.get("signedURL")
        if not signed_url:
            print("Warning: Failed to generate signed URL. Make sure you're using the service role key (not anon key) for private buckets.")
        return signed_url
    except Exception as e:
        print(f"Error creating signed URL: {e}")
        return None

