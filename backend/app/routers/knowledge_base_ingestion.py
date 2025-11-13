"""
Knowledge base ingestion endpoints.
Handles file uploads (PDF, CSV, documents) and processing.
"""
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import KnowledgeBase, KnowledgeBaseSource, SourceType, SourceStatus
from app.services.document_processor import process_document
from app.services.rag_service import add_article_to_vector_db
from app.services.storage_service import upload_file_to_supabase, get_supabase_client
from app.middleware.auth import require_api_key
import tempfile

router = APIRouter()


class UploadResponse(BaseModel):
    message: str
    articles_created: int
    source_id: int


@router.post("/upload/pdf", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Upload and process PDF file."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Upload to Supabase Storage (required - no local fallback)
    file_url = None
    file_path = None
    source = None
    
    try:
        # Upload to Supabase Storage
        file_url = await upload_file_to_supabase(
            file=file,
            bucket_name="knowledge-base-files",
            folder="pdfs"
        )
        # Reset file pointer for processing
        await file.seek(0)
        # Use temporary file for processing only
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            file_path = tmp_file.name
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to upload file to Supabase Storage. Please ensure SUPABASE_URL and SUPABASE_KEY are configured. Error: {str(e)}"
        )
    
    try:
        # Process PDF
        articles = process_document(file_path, file_type="pdf")
        
        # Create knowledge base source
        source_config = {
            "filename": file.filename,
            "file_url": file_url
        }
        source = KnowledgeBaseSource(
            source_type=SourceType.PDF,
            source_config=source_config,
            status=SourceStatus.PROCESSING
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        
        # Create knowledge base articles
        articles_created = 0
        for article_data in articles:
            kb_article = KnowledgeBase(
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data["tags"],
                source_id=source.id
            )
            db.add(kb_article)
            db.flush()
            
            # Generate embedding
            add_article_to_vector_db(kb_article.id, kb_article.title, kb_article.content, db)
            articles_created += 1
        
        # Update source status
        source.status = SourceStatus.ACTIVE
        source.last_synced_at = datetime.utcnow()
        db.commit()
        
        return UploadResponse(
            message=f"PDF processed successfully",
            articles_created=articles_created,
            source_id=source.id
        )
    except Exception as e:
        if source:
            source.status = SourceStatus.ERROR
            db.commit()
        # Clean up temporary file
        if file_path and file_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/upload/csv", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Upload and process CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Upload to Supabase Storage (required - no local fallback)
    file_url = None
    file_path = None
    source = None
    
    try:
        # Upload to Supabase Storage
        file_url = await upload_file_to_supabase(
            file=file,
            bucket_name="knowledge-base-files",
            folder="csvs"
        )
        # Reset file pointer for processing
        await file.seek(0)
        # Use temporary file for processing only
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            file_path = tmp_file.name
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to upload file to Supabase Storage. Please ensure SUPABASE_URL and SUPABASE_KEY are configured. Error: {str(e)}"
        )
    
    try:
        # Process CSV
        articles = process_document(file_path, file_type="csv")
        
        # Create knowledge base source
        source = KnowledgeBaseSource(
            source_type=SourceType.CSV,
            source_config={"file_url": file_url, "filename": file.filename},
            status=SourceStatus.PROCESSING
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        
        # Create knowledge base articles
        articles_created = 0
        for article_data in articles:
            kb_article = KnowledgeBase(
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data["tags"],
                source_id=source.id
            )
            db.add(kb_article)
            db.flush()
            
            # Generate embedding
            add_article_to_vector_db(kb_article.id, kb_article.title, kb_article.content, db)
            articles_created += 1
        
        # Update source status
        source.status = SourceStatus.ACTIVE
        source.last_synced_at = datetime.utcnow()
        db.commit()
        
        # Clean up temporary file
        if file_path and file_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(file_path)
            except:
                pass
        
        return UploadResponse(
            message=f"CSV processed successfully",
            articles_created=articles_created,
            source_id=source.id
        )
    except Exception as e:
        if source:
            source.status = SourceStatus.ERROR
            db.commit()
        # Clean up temporary file
        if file_path and file_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@router.post("/upload/document", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Upload and process text document (.txt, .md, .docx)."""
    allowed_extensions = ['.txt', '.md', '.markdown', '.docx']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File must be one of: {', '.join(allowed_extensions)}")
    
    # Upload to Supabase Storage (required - no local fallback)
    file_url = None
    file_path = None
    source = None
    
    try:
        # Upload to Supabase Storage
        file_url = await upload_file_to_supabase(
            file=file,
            bucket_name="knowledge-base-files",
            folder="documents"
        )
        # Reset file pointer for processing
        await file.seek(0)
        # Use temporary file for processing only
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            file_path = tmp_file.name
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to upload file to Supabase Storage. Please ensure SUPABASE_URL and SUPABASE_KEY are configured. Error: {str(e)}"
        )
    
    try:
        # Process document
        file_type = file_ext.lstrip('.')
        articles = process_document(file_path, file_type=file_type)
        
        # Create knowledge base source
        source = KnowledgeBaseSource(
            source_type=SourceType.DOCUMENT,
            source_config={"file_url": file_url, "filename": file.filename, "file_type": file_type},
            status=SourceStatus.PROCESSING
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        
        # Create knowledge base articles
        articles_created = 0
        for article_data in articles:
            kb_article = KnowledgeBase(
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data["tags"],
                source_id=source.id
            )
            db.add(kb_article)
            db.flush()
            
            # Generate embedding
            add_article_to_vector_db(kb_article.id, kb_article.title, kb_article.content, db)
            articles_created += 1
        
        # Update source status
        source.status = SourceStatus.ACTIVE
        source.last_synced_at = datetime.utcnow()
        db.commit()
        
        # Clean up temporary file
        if file_path and file_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(file_path)
            except:
                pass
        
        return UploadResponse(
            message=f"Document processed successfully",
            articles_created=articles_created,
            source_id=source.id
        )
    except Exception as e:
        if source:
            source.status = SourceStatus.ERROR
            db.commit()
        # Clean up temporary file
        if file_path and file_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

