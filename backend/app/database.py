"""
Database configuration and session management.
Supports both SQLite (development) and PostgreSQL (production/Supabase).
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

# Determine if we're using PostgreSQL or SQLite
is_postgres = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")

# Configure engine based on database type
if is_postgres:
    # PostgreSQL configuration with connection pooling and SSL
    # Supabase requires SSL connections
    connect_args = {}
    if "sslmode" not in DATABASE_URL:
        # Add SSL mode if not already specified
        separator = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"
    
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before using
        echo=False
    )
else:
    # SQLite-specific configuration (for local development)
    engine = create_engine(
        DATABASE_URL,
            connect_args={"check_same_thread": False},  # Needed for SQLite
            poolclass=NullPool  # SQLite doesn't need connection pooling
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for FastAPI routes to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

