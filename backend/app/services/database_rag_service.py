"""
Database RAG service for connecting SQL databases and syncing to knowledge base.
Converts database rows into knowledge base articles for RAG.
"""
import json
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, inspect, text
from cryptography.fernet import Fernet
import os
import base64

from app.models import DatabaseConnection, KnowledgeBase, KnowledgeBaseSource, SourceType, SourceStatus, TenantConfiguration
from app.services.rag_service import add_article_to_vector_db


# Encryption key for database connections (should be in env var in production)
# Generate a key if not provided
_encryption_key = os.getenv("DB_ENCRYPTION_KEY")
if not _encryption_key:
    _encryption_key = Fernet.generate_key().decode()
ENCRYPTION_KEY = _encryption_key


def encrypt_connection_string(connection_string: str) -> str:
    """
    Encrypt database connection string.
    
    Args:
        connection_string: Plain text connection string
    
    Returns:
        Encrypted connection string
    """
    try:
        key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
        f = Fernet(key)
        encrypted = f.encrypt(connection_string.encode())
        return encrypted.decode()
    except Exception as e:
        print(f"Error encrypting connection string: {e}")
        return connection_string  # Return unencrypted if encryption fails


def decrypt_connection_string(encrypted_string: str) -> str:
    """
    Decrypt database connection string.
    
    Args:
        encrypted_string: Encrypted connection string
    
    Returns:
        Decrypted connection string
    """
    try:
        key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_string.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"Error decrypting connection string: {e}")
        return encrypted_string  # Return as-is if decryption fails


def build_connection_string(db_type: str, host: str, port: int, database: str, username: str, password: str) -> str:
    """
    Build database connection string based on database type.
    
    Args:
        db_type: Database type (postgresql, mysql, sqlite, supabase)
        host: Database host
        port: Database port
        database: Database name
        username: Username
        password: Password
    
    Returns:
        Connection string
    """
    if db_type == "postgresql" or db_type == "supabase":
        # Supabase uses PostgreSQL connection string format
        # If host contains .supabase.co, it's a Supabase connection
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "mysql":
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "sqlite":
        return f"sqlite:///{database}"
    else:
        raise Exception(f"Unsupported database type: {db_type}")


def get_database_tables(connection_string: str, db_type: str) -> List[Dict[str, any]]:
    """
    Get list of tables from database.
    
    Args:
        connection_string: Database connection string
        db_type: Database type
    
    Returns:
        List of table information dictionaries
    """
    try:
        engine = create_engine(connection_string)
        inspector = inspect(engine)
        
        tables = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            tables.append({
                "name": table_name,
                "columns": [col["name"] for col in columns]
            })
        
        return tables
    except Exception as e:
        raise Exception(f"Error getting database tables: {e}")


def sync_database_table_to_kb(
    db_connection: DatabaseConnection,
    table_name: str,
    columns: List[str],
    tenant_id: int,
    db: Session
) -> int:
    """
    Sync a database table to knowledge base.
    Converts each row into a knowledge base article.
    
    Args:
        db_connection: Database connection object
        table_name: Table name to sync
        columns: Columns to include
        tenant_id: Tenant ID
        db: Database session
    
    Returns:
        Number of articles created
    """
    # Decrypt connection string
    connection_string = decrypt_connection_string(db_connection.connection_string)
    
    try:
        engine = create_engine(connection_string)
        
        # Build query
        columns_str = ", ".join(columns)
        query = f"SELECT {columns_str} FROM {table_name}"
        
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
        
        # Create or get knowledge base source
        source = db.query(KnowledgeBaseSource).filter(
            KnowledgeBaseSource.tenant_id == tenant_id,
            KnowledgeBaseSource.source_type == SourceType.DATABASE,
            KnowledgeBaseSource.source_config.contains({"connection_id": db_connection.id, "table": table_name})
        ).first()
        
        if not source:
            source = KnowledgeBaseSource(
                tenant_id=tenant_id,
                source_type=SourceType.DATABASE,
                source_config={
                    "connection_id": db_connection.id,
                    "table": table_name,
                    "columns": columns
                },
                status=SourceStatus.PROCESSING
            )
            db.add(source)
            db.commit()
            db.refresh(source)
        
        # Delete existing articles from this source
        db.query(KnowledgeBase).filter(
            KnowledgeBase.tenant_id == tenant_id,
            KnowledgeBase.source_id == source.id
        ).delete()
        
        # Convert rows to knowledge base articles
        articles_created = 0
        for row in rows:
            # Build title from first column or row number
            title = f"{table_name} - {row[0]}" if row else f"{table_name} - Row {articles_created + 1}"
            
            # Build content from all columns
            content_parts = []
            for i, col in enumerate(columns):
                value = row[i] if i < len(row) else None
                if value is not None:
                    content_parts.append(f"{col}: {value}")
            
            content = "\n".join(content_parts)
            
            if content:
                # Create knowledge base article
                kb_article = KnowledgeBase(
                    tenant_id=tenant_id,
                    title=title,
                    content=content,
                    category=f"Database - {table_name}",
                    tags=f"database,{table_name}",
                    source_id=source.id
                )
                db.add(kb_article)
                db.flush()  # Flush to get ID
                
                # Get tenant's embedding model
                tenant_config = db.query(TenantConfiguration).filter(
                    TenantConfiguration.tenant_id == tenant_id
                ).first()
                embedding_model_name = tenant_config.embedding_model if tenant_config else None
                
                # Generate and store embedding
                add_article_to_vector_db(kb_article.id, kb_article.title, kb_article.content, db, tenant_id=tenant_id, embedding_model_name=embedding_model_name)
                
                articles_created += 1
        
        # Update source status
        source.status = SourceStatus.ACTIVE
        from datetime import datetime
        source.last_synced_at = datetime.utcnow()
        db.commit()
        
        return articles_created
    
    except Exception as e:
        # Update source status to error
        if source:
            source.status = SourceStatus.ERROR
            db.commit()
        raise Exception(f"Error syncing database table: {e}")


def test_database_connection(connection_string: str) -> bool:
    """
    Test database connection.
    
    Args:
        connection_string: Database connection string
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False

