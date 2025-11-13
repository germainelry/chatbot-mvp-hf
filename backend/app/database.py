"""
Database configuration and session management.
Uses Supabase PostgreSQL exclusively for all environments.
"""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Validate DATABASE_URL is set
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required. Set it to your Supabase PostgreSQL connection string.")
    sys.exit(1)

# Validate DATABASE_URL is PostgreSQL
if not (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")):
    print("ERROR: DATABASE_URL must be a PostgreSQL connection string (starting with postgresql:// or postgres://)")
    print("SQLite is no longer supported. Please use Supabase PostgreSQL for all environments.")
    sys.exit(1)

# PostgreSQL configuration with connection pooling and SSL
# Supabase requires SSL connections
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

