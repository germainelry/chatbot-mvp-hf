"""
RAG service for vector embeddings and semantic search.
Uses sentence-transformers for embeddings and ChromaDB for vector storage.
"""
import os
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

# Try to import sentence-transformers, fallback if not available
EMBEDDING_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    print("⚠️  sentence-transformers or chromadb not available, using fallback")

# Initialize embedding models (lazy loading, cached per model name)
_embedding_models = {}  # Cache for multiple models: {model_name: SentenceTransformer}
_chroma_client = None
_chroma_collections = {}  # Cache for tenant-specific collections

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


def get_embedding_model(model_name: Optional[str] = None):
    """
    Lazy load the embedding model.
    
    Args:
        model_name: Name of the embedding model to load. If None, uses default.
    
    Returns:
        SentenceTransformer model or None if not available
    """
    global _embedding_models
    if not EMBEDDING_AVAILABLE:
        return None
    
    # Use provided model name or default
    model_name = model_name or DEFAULT_EMBEDDING_MODEL
    
    # Check cache
    if model_name in _embedding_models:
        return _embedding_models[model_name]
    
    # Load model
    try:
        print(f"Loading embedding model: {model_name}")
        model = SentenceTransformer(model_name)
        _embedding_models[model_name] = model
        return model
    except Exception as e:
        print(f"Error loading embedding model {model_name}: {e}")
        # Fallback to default if specified model fails
        if model_name != DEFAULT_EMBEDDING_MODEL:
            return get_embedding_model(DEFAULT_EMBEDDING_MODEL)
        return None


def get_chroma_collection(tenant_id: Optional[int] = None):
    """
    Initialize and return ChromaDB collection.
    
    Args:
        tenant_id: Deprecated - kept for backward compatibility
    """
    global _chroma_client, _chroma_collections
    if not EMBEDDING_AVAILABLE:
        return None
    
    if _chroma_client is None:
        # Use persistent storage in backend directory
        chroma_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")
        os.makedirs(chroma_path, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    
    # Use global collection name
    collection_name = "knowledge_base"
    
    # Check cache
    if collection_name in _chroma_collections:
        return _chroma_collections[collection_name]
    
    # Get or create collection
    try:
        collection = _chroma_client.get_collection(collection_name)
    except:
        collection = _chroma_client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    _chroma_collections[collection_name] = collection
    return collection


def generate_embedding(text: str, model_name: Optional[str] = None) -> Optional[List[float]]:
    """
    Generate vector embedding for text.
    
    Args:
        text: Text to embed
        model_name: Name of the embedding model to use. If None, uses default.
    
    Returns:
        Embedding vector or None if embeddings are not available.
    """
    if not EMBEDDING_AVAILABLE:
        return None
    
    model = get_embedding_model(model_name)
    if model is None:
        return None
    
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    vec1_array = np.array(vec1)
    vec2_array = np.array(vec2)
    
    dot_product = np.dot(vec1_array, vec2_array)
    norm1 = np.linalg.norm(vec1_array)
    norm2 = np.linalg.norm(vec2_array)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def search_knowledge_base_vector(query: str, db: Session, top_k: int = 3, tenant_id: Optional[int] = None, embedding_model_name: Optional[str] = None) -> List[Dict]:
    """
    Search knowledge base using vector similarity.
    Falls back to keyword search if embeddings are not available.
    
    Args:
        query: Search query
        db: Database session
        top_k: Number of results to return
        tenant_id: Deprecated - kept for backward compatibility
        embedding_model_name: Name of embedding model to use. If None, uses default.
    """
    if not EMBEDDING_AVAILABLE:
        # Fallback to keyword search
        return search_knowledge_base_keyword(query, db, top_k, tenant_id=None)
    
    collection = get_chroma_collection(tenant_id=None)
    if collection is None:
        return search_knowledge_base_keyword(query, db, top_k, tenant_id=None)
    
    # Generate query embedding
    query_embedding = generate_embedding(query, model_name=embedding_model_name)
    if query_embedding is None:
        return search_knowledge_base_keyword(query, db, top_k, tenant_id=None)
    
    try:
        # Search in ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Map results to article format
        matched_articles = []
        if results['ids'] and len(results['ids'][0]) > 0:
            from app.models import KnowledgeBase
            
            for i, article_id in enumerate(results['ids'][0]):
                # Get article from database
                article = db.query(KnowledgeBase).filter(KnowledgeBase.id == int(article_id)).first()
                
                if article:
                    distance = results['distances'][0][i] if 'distances' in results else 0.0
                    similarity = 1.0 - distance  # Convert distance to similarity
                    
                    matched_articles.append({
                        "id": article.id,
                        "title": article.title,
                        "content": article.content,
                        "category": article.category,
                        "match_score": similarity,
                        "similarity": similarity
                    })
        
        # If no results from ChromaDB, fallback to keyword search
        if not matched_articles:
            return search_knowledge_base_keyword(query, db, top_k, tenant_id=None)
        
        return matched_articles
    
    except Exception as e:
        print(f"Error in vector search: {e}")
        return search_knowledge_base_keyword(query, db, top_k, tenant_id=None)


def search_knowledge_base_keyword(query: str, db: Session, top_k: int = 3, tenant_id: Optional[int] = None) -> List[Dict]:
    """
    Fallback keyword-based search.
    
    Args:
        query: Search query
        db: Database session
        top_k: Number of results to return
        tenant_id: Deprecated - kept for backward compatibility
    """
    from app.models import KnowledgeBase
    
    query_lower = query.lower()
    all_articles = db.query(KnowledgeBase).all()
    
    matched_articles = []
    for article in all_articles:
        article_text = f"{article.title} {article.content} {article.tags}".lower()
        query_words = set(query_lower.split())
        article_words = set(article_text.split())
        common_words = query_words.intersection(article_words)
        
        if common_words:
            match_score = len(common_words) / len(query_words) if query_words else 0
            matched_articles.append({
                "id": article.id,
                "title": article.title,
                "content": article.content,
                "category": article.category,
                "match_score": match_score,
                "similarity": match_score
            })
    
    matched_articles.sort(key=lambda x: x["match_score"], reverse=True)
    return matched_articles[:top_k]


def add_article_to_vector_db(article_id: int, title: str, content: str, db: Session, tenant_id: Optional[int] = None, embedding_model_name: Optional[str] = None):
    """
    Add or update article in vector database.
    
    Args:
        article_id: Article ID
        title: Article title
        content: Article content
        db: Database session
        tenant_id: Deprecated - kept for backward compatibility
        embedding_model_name: Name of embedding model to use. If None, uses default.
    """
    if not EMBEDDING_AVAILABLE:
        return
    
    collection = get_chroma_collection(tenant_id=None)
    if collection is None:
        return
    
    # Generate embedding for article
    article_text = f"{title} {content}"
    embedding = generate_embedding(article_text, model_name=embedding_model_name)
    
    if embedding is None:
        return
    
    try:
        # Add to ChromaDB
        collection.upsert(
            ids=[str(article_id)],
            embeddings=[embedding],
            documents=[article_text],
            metadatas=[{"article_id": article_id, "title": title}]
        )
        
        # Also update embedding in Supabase PostgreSQL
        from app.models import KnowledgeBase
        article = db.query(KnowledgeBase).filter_by(id=article_id).first()
        if article:
            article.embedding = embedding
            db.commit()
    except Exception as e:
        print(f"Error adding article to vector DB: {e}")


def initialize_vector_db(db: Session):
    """
    Initialize vector database with existing knowledge base articles.
    """
    if not EMBEDDING_AVAILABLE:
        return
    
    from app.models import KnowledgeBase
    
    articles = db.query(KnowledgeBase).all()
    collection = get_chroma_collection()
    
    if collection is None:
        return
    
    try:
        # Clear existing collection
        try:
            _chroma_client.delete_collection("knowledge_base")
        except:
            pass
        
        _chroma_collection = _chroma_client.create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Add all articles
        for article in articles:
            add_article_to_vector_db(article.id, article.title, article.content, db)
        
        print(f"✅ Initialized vector DB with {len(articles)} articles")
    except Exception as e:
        print(f"Error initializing vector DB: {e}")

