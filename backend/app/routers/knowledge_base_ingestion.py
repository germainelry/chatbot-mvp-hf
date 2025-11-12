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
from app.middleware.tenant_middleware import get_tenant_id_from_request
from fastapi import Request

router = APIRouter()

# File upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class UploadResponse(BaseModel):
    message: str
    articles_created: int
    source_id: int


@router.post("/upload/pdf", response_model=UploadResponse)
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process PDF file."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{tenant_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process PDF
        articles = process_document(file_path, file_type="pdf")
        
        # Create knowledge base source
        source = KnowledgeBaseSource(
            tenant_id=tenant_id,
            source_type=SourceType.PDF,
            source_config={"file_path": file_path, "filename": file.filename},
            status=SourceStatus.PROCESSING
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        
        # Create knowledge base articles
        articles_created = 0
        for article_data in articles:
            kb_article = KnowledgeBase(
                tenant_id=tenant_id,
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data["tags"],
                source_id=source.id
            )
            db.add(kb_article)
            db.flush()
            
            # Generate embedding
            add_article_to_vector_db(kb_article.id, kb_article.title, kb_article.content, db, tenant_id=tenant_id)
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
        source.status = SourceStatus.ERROR
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/upload/csv", response_model=UploadResponse)
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process CSV file."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{tenant_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process CSV
        articles = process_document(file_path, file_type="csv")
        
        # Create knowledge base source
        source = KnowledgeBaseSource(
            tenant_id=tenant_id,
            source_type=SourceType.CSV,
            source_config={"file_path": file_path, "filename": file.filename},
            status=SourceStatus.PROCESSING
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        
        # Create knowledge base articles
        articles_created = 0
        for article_data in articles:
            kb_article = KnowledgeBase(
                tenant_id=tenant_id,
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data["tags"],
                source_id=source.id
            )
            db.add(kb_article)
            db.flush()
            
            # Generate embedding
            add_article_to_vector_db(kb_article.id, kb_article.title, kb_article.content, db, tenant_id=tenant_id)
            articles_created += 1
        
        # Update source status
        source.status = SourceStatus.ACTIVE
        source.last_synced_at = datetime.utcnow()
        db.commit()
        
        return UploadResponse(
            message=f"CSV processed successfully",
            articles_created=articles_created,
            source_id=source.id
        )
    except Exception as e:
        source.status = SourceStatus.ERROR
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@router.post("/upload/document", response_model=UploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process text document (.txt, .md, .docx)."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    allowed_extensions = ['.txt', '.md', '.markdown', '.docx']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File must be one of: {', '.join(allowed_extensions)}")
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{tenant_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process document
        file_type = file_ext.lstrip('.')
        articles = process_document(file_path, file_type=file_type)
        
        # Create knowledge base source
        source = KnowledgeBaseSource(
            tenant_id=tenant_id,
            source_type=SourceType.DOCUMENT,
            source_config={"file_path": file_path, "filename": file.filename, "file_type": file_type},
            status=SourceStatus.PROCESSING
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        
        # Create knowledge base articles
        articles_created = 0
        for article_data in articles:
            kb_article = KnowledgeBase(
                tenant_id=tenant_id,
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data["tags"],
                source_id=source.id
            )
            db.add(kb_article)
            db.flush()
            
            # Generate embedding
            add_article_to_vector_db(kb_article.id, kb_article.title, kb_article.content, db, tenant_id=tenant_id)
            articles_created += 1
        
        # Update source status
        source.status = SourceStatus.ACTIVE
        source.last_synced_at = datetime.utcnow()
        db.commit()
        
        return UploadResponse(
            message=f"Document processed successfully",
            articles_created=articles_created,
            source_id=source.id
        )
    except Exception as e:
        source.status = SourceStatus.ERROR
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

