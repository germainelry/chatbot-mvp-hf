"""
Knowledge base management endpoints.
Allows agents to add/update information for AI reference.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import KnowledgeBase

router = APIRouter()


class KnowledgeBaseCreate(BaseModel):
    title: str
    content: str
    category: str
    tags: Optional[str] = ""


class KnowledgeBaseUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    tags: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=KnowledgeBaseResponse)
async def create_article(
    article: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """Create a new knowledge base article."""
    db_article = KnowledgeBase(
        title=article.title,
        content=article.content,
        category=article.category,
        tags=article.tags
    )
    
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    
    return db_article


@router.get("", response_model=List[KnowledgeBaseResponse])
async def get_articles(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all knowledge base articles with optional filtering."""
    query = db.query(KnowledgeBase)
    
    if category:
        query = query.filter(KnowledgeBase.category == category)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (KnowledgeBase.title.like(search_term)) |
            (KnowledgeBase.content.like(search_term)) |
            (KnowledgeBase.tags.like(search_term))
        )
    
    articles = query.order_by(KnowledgeBase.updated_at.desc()).all()
    return articles


@router.get("/{article_id}", response_model=KnowledgeBaseResponse)
async def get_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific knowledge base article."""
    article = db.query(KnowledgeBase).filter(KnowledgeBase.id == article_id).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article


@router.put("/{article_id}", response_model=KnowledgeBaseResponse)
async def update_article(
    article_id: int,
    update: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """Update a knowledge base article."""
    article = db.query(KnowledgeBase).filter(KnowledgeBase.id == article_id).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if update.title is not None:
        article.title = update.title
    if update.content is not None:
        article.content = update.content
    if update.category is not None:
        article.category = update.category
    if update.tags is not None:
        article.tags = update.tags
    
    article.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(article)
    
    return article


@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Delete a knowledge base article."""
    article = db.query(KnowledgeBase).filter(KnowledgeBase.id == article_id).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    db.delete(article)
    db.commit()
    
    return {"message": "Article deleted successfully"}

