"""Centralized configuration management for Pikar AI.

Uses Pydantic Settings for type-safe, environment-based configuration.
All configuration is loaded at startup and validated.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    # Connection settings
    url: str = Field(default="", description="Supabase URL")
    anon_key: str = Field(default="", description="Supabase anon key for user operations")
    service_role_key: str = Field(default="", description="Supabase service role key for admin operations")
    
    # Pool configuration
    max_connections: int = Field(default=50, ge=1, le=1000)
    timeout: float = Field(default=60.0, ge=1.0, le=300.0)
    
    # Table names
    sessions_table: str = Field(default="sessions")
    events_table: str = Field(default="session_events")
    version_history_table: str = Field(default="session_version_history")
    
    @field_validator("url", "service_role_key")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Database URL and service role key are required")
        return v


class CacheSettings(BaseSettings):
    """Cache configuration."""
    
    model_config = SettingsConfigDict(env_prefix="CACHE_")
    
    # Redis connection
    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    password: Optional[str] = Field(default=None)
    db: int = Field(default=0, ge=0, le=15)
    
    # TTL settings (in seconds)
    ttl_user_config: int = Field(default=3600, ge=60)  # 1 hour
    ttl_session_meta: int = Field(default=1800, ge=60)  # 30 minutes
    ttl_persona: int = Field(default=7200, ge=60)  # 2 hours
    ttl_default: int = Field(default=3600, ge=60)  # 1 hour
    
    # Connection pool
    max_connections: int = Field(default=50, ge=1)


class GoogleAISettings(BaseSettings):
    """Google AI (Vertex AI / Gemini API) settings."""
    
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")
    
    # Authentication
    application_credentials: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    cloud_project: Optional[str] = Field(default=None)
    cloud_location: str = Field(default="us-central1")
    
    # Model configuration
    use_vertexai: bool = Field(default=False)
    model_primary: str = Field(default="gemini-2.5-pro")
    model_fallback: str = Field(default="gemini-2.5-flash")
    
    @field_validator("application_credentials")
    @classmethod
    def validate_credentials_path(cls, v: Optional[str]) -> Optional[str]:
        if v and not os.path.isabs(v):
            # Resolve relative paths against project root
            project_root = Path(__file__).resolve().parent.parent.parent
            resolved = (project_root / v.replace("\\", "/").lstrip("./")).resolve()
            if resolved.exists():
                return str(resolved)
        return v


class WidgetSettings(BaseSettings):
    """Widget rendering configuration."""
    
    model_config = SettingsConfigDict(env_prefix="WIDGET_")
    
    # Renderable widget types whitelist
    renderable_types: List[str] = Field(default=[
        "initiative_dashboard",
        "revenue_chart",
        "product_launch",
        "kanban_board",
        "workflow_builder",
        "morning_briefing",
        "calendar",
        "table",
        "form",
        "chart",
        "metric_card",
        "image",
        "video",
        "text",
        "list",
    ])
    
    # Widget defaults
    default_dismissible: bool = Field(default=True)
    max_title_length: int = Field(default=200)
    max_content_length: int = Field(default=10000)


class SecuritySettings(BaseSettings):
    """Security and authentication settings."""
    
    model_config = SettingsConfigDict(env_prefix="SECURITY_")
    
    # CORS
    allowed_origins: List[str] = Field(default=["*"])
    allowed_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: List[str] = Field(default=["*"])
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, ge=1)
    rate_limit_window: int = Field(default=60, ge=1)  # seconds
    
    # Session
    session_timeout: int = Field(default=3600, ge=60)  # seconds
    max_session_events: int = Field(default=40, ge=10)


class AppSettings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Allow extra env vars
    )
    
    # App info
    name: str = Field(default="pikar-ai")
    version: str = Field(default="1.0.0")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    debug: bool = Field(default=False)
    
    # URLs
    url: Optional[str] = Field(default=None)
    api_prefix: str = Field(default="/api/v1")
    
    # Feature flags
    enable_a2a: bool = Field(default=True)
    enable_caching: bool = Field(default=True)
    enable_telemetry: bool = Field(default=False)
    
    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    google_ai: GoogleAISettings = Field(default_factory=GoogleAISettings)
    widget: WidgetSettings = Field(default_factory=WidgetSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v


# Import Path here to avoid circular import issues
from pathlib import Path


@lru_cache()
def get_settings() -> AppSettings:
    """Get cached application settings.
    
    Returns:
        AppSettings: Validated application configuration
    """
    return AppSettings()


# Export all settings classes
__all__ = [
    "AppSettings",
    "DatabaseSettings",
    "CacheSettings",
    "GoogleAISettings",
    "WidgetSettings",
    "SecuritySettings",
    "get_settings",
]
