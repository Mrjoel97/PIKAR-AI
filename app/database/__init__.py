"""Database service for Pikar AI.

Provides a centralized database session factory and utility functions
for all database operations.
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import Base

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_database_url() -> str:
    """Get database URL from environment or Supabase configuration."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        return f"{supabase_url}?apikey={os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')}"

    raise ValueError("DATABASE_URL or SUPABASE_URL must be set")


def get_engine() -> Engine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup.

    Usage:
        with get_db_session() as session:
            session.query(User).all()
    """
    session = get_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize database tables (for development only)."""
    Base.metadata.create_all(bind=get_engine())


def drop_db() -> None:
    """Drop all database tables (for development only)."""
    Base.metadata.drop_all(bind=get_engine())
