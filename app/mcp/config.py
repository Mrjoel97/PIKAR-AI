"""MCP Configuration - API Keys and Settings.

This module manages API keys and configuration for MCP services.
All API keys are loaded from environment variables and never exposed
to agents or users.

Environment Variables Required:
- TAVILY_API_KEY: API key for Tavily search
- FIRECRAWL_API_KEY: API key for Firecrawl web scraping
- SUPABASE_URL: Supabase project URL
- SUPABASE_SERVICE_ROLE_KEY: Supabase service role key
- SENDGRID_API_KEY: SendGrid API key for email notifications (optional)
- HUBSPOT_API_KEY: HubSpot API key for CRM integration (optional)
- STITCH_API_KEY: Google Stitch API key for landing page generation (optional)
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class MCPConfig:
    """Configuration for MCP services.

    All fields are loaded from environment variables.
    This class is immutable to prevent accidental modification.
    """
    # Search API (Tavily)
    tavily_api_key: Optional[str] = None
    tavily_base_url: str = "https://api.tavily.com"

    # Web Scraping (Firecrawl)
    firecrawl_api_key: Optional[str] = None
    firecrawl_base_url: str = "https://api.firecrawl.dev"

    # Database (Supabase)
    supabase_url: Optional[str] = None
    supabase_service_key: Optional[str] = None

    # Email Service (SendGrid)
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: str = "noreply@pikar.ai"

    # CRM Integration (HubSpot)
    hubspot_api_key: Optional[str] = None
    hubspot_base_url: str = "https://api.hubapi.com"
    
    # Landing Page Builder (Google Stitch)
    stitch_api_key: Optional[str] = None
    stitch_api_url: str = "https://stitch.withgoogle.com/api"

    # Rate Limiting
    search_rate_limit_per_minute: int = 30
    scrape_rate_limit_per_minute: int = 10

    # Audit Logging
    audit_log_enabled: bool = True
    audit_log_table: str = "mcp_audit_logs"
    
    def is_tavily_configured(self) -> bool:
        """Check if Tavily API is configured."""
        return bool(self.tavily_api_key)
    
    def is_firecrawl_configured(self) -> bool:
        """Check if Firecrawl API is configured."""
        return bool(self.firecrawl_api_key)
    
    def is_supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_url and self.supabase_service_key)
    
    def is_email_configured(self) -> bool:
        """Check if email service (SendGrid) is configured."""
        return bool(self.sendgrid_api_key)
    
    def is_crm_configured(self) -> bool:
        """Check if CRM (HubSpot) is configured."""
        return bool(self.hubspot_api_key)
    
    def is_stitch_configured(self) -> bool:
        """Check if Stitch API is configured."""
        return bool(self.stitch_api_key)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of all configuration statuses."""
        return {
            "tavily": {"configured": self.is_tavily_configured(), "name": "Web Search (Tavily)"},
            "firecrawl": {"configured": self.is_firecrawl_configured(), "name": "Web Scraping (Firecrawl)"},
            "supabase": {"configured": self.is_supabase_configured(), "name": "Database (Supabase)"},
            "sendgrid": {"configured": self.is_email_configured(), "name": "Email (SendGrid)"},
            "hubspot": {"configured": self.is_crm_configured(), "name": "CRM (HubSpot)"},
            "stitch": {"configured": self.is_stitch_configured(), "name": "Landing Pages (Stitch)"},
        }


@lru_cache(maxsize=1)
def get_mcp_config() -> MCPConfig:
    """Get MCP configuration from environment variables.
    
    This function is cached to avoid repeated environment variable lookups.
    
    Returns:
        MCPConfig instance with all settings loaded.
    """
    return MCPConfig(
        # Search API
        tavily_api_key=os.environ.get("TAVILY_API_KEY"),
        
        # Web Scraping
        firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY"),
        
        # Database
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_service_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        
        # Email
        sendgrid_api_key=os.environ.get("SENDGRID_API_KEY"),
        sendgrid_from_email=os.environ.get("SENDGRID_FROM_EMAIL", "noreply@pikar.ai"),
        
        # CRM
        hubspot_api_key=os.environ.get("HUBSPOT_API_KEY"),
        
        # Landing Page Builder (Stitch)
        stitch_api_key=os.environ.get("STITCH_API_KEY"),
        stitch_api_url=os.environ.get("STITCH_API_URL", "https://stitch.withgoogle.com/api"),
        
        # Rate Limiting
        search_rate_limit_per_minute=int(os.environ.get("MCP_SEARCH_RATE_LIMIT", "30")),
        scrape_rate_limit_per_minute=int(os.environ.get("MCP_SCRAPE_RATE_LIMIT", "10")),
        
        # Audit Logging
        audit_log_enabled=os.environ.get("MCP_AUDIT_LOG_ENABLED", "true").lower() == "true",
        audit_log_table=os.environ.get("MCP_AUDIT_LOG_TABLE", "mcp_audit_logs"),
    )


def clear_config_cache() -> None:
    """Clear the configuration cache.
    
    Call this if environment variables have been updated and you need
    to reload the configuration.
    """
    get_mcp_config.cache_clear()

