"""Alembic environment configuration for Pikar AI."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from environment or config.
    
    Tries multiple sources in order:
    1. DATABASE_URL environment variable (direct PostgreSQL URL)
    2. Supabase connection string (from SUPABASE_URL + SUPABASE_DB_HOST)
    3. Alembic config file
    
    Returns:
        The database URL string.
        
    Raises:
        ValueError: If no database URL can be determined.
    """
    # Option 1: Direct DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # Option 2: Build from Supabase configuration
    supabase_url = os.getenv("SUPABASE_URL")
    db_host = os.getenv("SUPABASE_DB_HOST", "")
    
    if supabase_url and db_host:
        # Use the direct PostgreSQL connection string from Supabase
        anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        if anon_key and db_host:
            db_password = os.getenv("SUPABASE_DB_PASSWORD", "")
            if db_password:
                return f"postgresql://postgres:{db_password}@{db_host}:5432/postgres"
            # Fallback: use the pooler URL format with anon key
            return f"postgresql://postgres.anonymous:{anon_key}@{db_host}:6543/postgres"
    
    # Option 3: Fall back to config file
    fallback = config.get_main_option("sqlalchemy.url")
    if fallback:
        return fallback
    
    raise ValueError("DATABASE_URL or Supabase configuration must be set")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    db_url = get_url()
    if not db_url:
        raise ValueError("Database URL could not be determined")
    configuration["sqlalchemy.url"] = db_url
    connectable = create_engine(
        db_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
