"""
Database RAG endpoints.
Handles database connections and table syncing to knowledge base.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict

from app.database import get_db
from app.models import DatabaseConnection, KnowledgeBaseSource, SourceType, SourceStatus
from app.services.database_rag_service import (
    build_connection_string,
    encrypt_connection_string,
    decrypt_connection_string,
    get_database_tables,
    sync_database_table_to_kb,
    test_database_connection
)
from app.middleware.tenant_middleware import get_tenant_id_from_request
from app.middleware.auth import require_api_key

router = APIRouter()


class DatabaseConnectionCreate(BaseModel):
    connection_name: str
    db_type: str  # postgresql, mysql, sqlite
    host: str
    port: int
    database: str
    username: str
    password: str


class DatabaseConnectionResponse(BaseModel):
    id: int
    connection_name: str
    db_type: str
    is_active: int
    created_at: str
    
    class Config:
        from_attributes = True


class TableInfo(BaseModel):
    name: str
    columns: List[str]


class SyncTableRequest(BaseModel):
    connection_id: int
    table_name: str
    columns: List[str]


@router.post("/connect", response_model=DatabaseConnectionResponse)
async def create_database_connection(
    request: Request,
    connection: DatabaseConnectionCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Create a new database connection."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    # Build and test connection string
    connection_string = build_connection_string(
        connection.db_type,
        connection.host,
        connection.port,
        connection.database,
        connection.username,
        connection.password
    )
    
    # Test connection
    if not test_database_connection(connection_string):
        raise HTTPException(status_code=400, detail="Failed to connect to database")
    
    # Encrypt connection string
    encrypted_string = encrypt_connection_string(connection_string)
    
    # Create database connection
    db_connection = DatabaseConnection(
        tenant_id=tenant_id,
        connection_name=connection.connection_name,
        db_type=connection.db_type,
        connection_string=encrypted_string,
        is_active=1
    )
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)
    
    return DatabaseConnectionResponse(
        id=db_connection.id,
        connection_name=db_connection.connection_name,
        db_type=db_connection.db_type,
        is_active=db_connection.is_active,
        created_at=db_connection.created_at.isoformat()
    )


@router.get("/connections", response_model=List[DatabaseConnectionResponse])
async def list_database_connections(
    request: Request,
    db: Session = Depends(get_db)
):
    """List all database connections for tenant."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    connections = db.query(DatabaseConnection).filter(
        DatabaseConnection.tenant_id == tenant_id
    ).all()
    
    return [
        DatabaseConnectionResponse(
            id=conn.id,
            connection_name=conn.connection_name,
            db_type=conn.db_type,
            is_active=conn.is_active,
            created_at=conn.created_at.isoformat()
        )
        for conn in connections
    ]


@router.get("/connections/{connection_id}/tables", response_model=List[TableInfo])
async def get_database_tables_endpoint(
    request: Request,
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Get list of tables from a database connection."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    # Get connection
    db_connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.tenant_id == tenant_id
    ).first()
    
    if not db_connection:
        raise HTTPException(status_code=404, detail="Database connection not found")
    
    # Decrypt connection string
    connection_string = decrypt_connection_string(db_connection.connection_string)
    
    try:
        # Get tables
        tables = get_database_tables(connection_string, db_connection.db_type)
        return [TableInfo(name=t["name"], columns=t["columns"]) for t in tables]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tables: {str(e)}")


@router.post("/sync")
async def sync_database_table(
    request: Request,
    sync_request: SyncTableRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Sync a database table to knowledge base."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    # Get connection
    db_connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == sync_request.connection_id,
        DatabaseConnection.tenant_id == tenant_id
    ).first()
    
    if not db_connection:
        raise HTTPException(status_code=404, detail="Database connection not found")
    
    try:
        # Sync table
        articles_created = sync_database_table_to_kb(
            db_connection,
            sync_request.table_name,
            sync_request.columns,
            tenant_id,
            db
        )
        
        return {
            "message": f"Table synced successfully",
            "articles_created": articles_created
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing table: {str(e)}")


@router.delete("/connections/{connection_id}")
async def delete_database_connection(
    request: Request,
    connection_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Delete a database connection."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    # Get connection
    db_connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.tenant_id == tenant_id
    ).first()
    
    if not db_connection:
        raise HTTPException(status_code=404, detail="Database connection not found")
    
    db.delete(db_connection)
    db.commit()
    
    return {"message": "Database connection deleted successfully"}

