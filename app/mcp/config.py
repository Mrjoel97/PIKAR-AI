"""MCP Configuration - API Keys and Settings.

This module manages API keys and configuration for MCP services.
All API keys are loaded from environment variables and never exposed
to agents or users.

Environment Variables Required:
- TAVILY_API_KEY: API key for Tavily search
- FIRECRAWL_API_KEY: API key for Firecrawl web scraping
- SUPABASE_URL: Supabase project URL
- SUPABASE_SERVICE_ROLE_KEY: Supabase service role key
- RESEND_API_KEY: Resend API key for email notifications (optional)
- HUBSPOT_API_KEY: HubSpot API key for CRM integration (optional)
- STITCH_API_KEY: Google Stitch API key for landing page generation (optional)
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class MCPConfig:
    """Configuration for MCP services.

    All fields are loaded from environment variables.
    This class is immutable to prevent accidental modification.
    """

    # Search API (Tavily)
    tavily_api_key: str | None = None
    tavily_base_url: str = "https://api.tavily.com"

    # Web Scraping (Firecrawl)
    firecrawl_api_key: str | None = None
    firecrawl_base_url: str = "https://api.firecrawl.dev"

    # Database (Supabase)
    supabase_url: str | None = None
    supabase_service_key: str | None = None

    # Email Service (Resend)
    resend_api_key: str | None = None
    resend_from_email: str = "noreply@pikar.ai"

    # CRM Integration (HubSpot)
    hubspot_api_key: str | None = None
    hubspot_base_url: str = "https://api.hubapi.com"

    # Landing Page Builder (Google Stitch)
    stitch_api_key: str | None = None
    stitch_api_url: str = "https://stitch.withgoogle.com/api"

    # Google SEO (Search Console + GA4)
    google_seo_service_account_json: str | None = None
    google_analytics_property_id: str | None = None

    # Rate Limiting
    search_rate_limit_per_minute: int = 30
    scrape_rate_limit_per_minute: int = 10
    crawl_rate_limit_per_minute: int = 5

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
        """Check if email service (Resend) is configured."""
        return bool(self.resend_api_key)

    def is_crm_configured(self) -> bool:
        """Check if CRM (HubSpot) is configured."""
        return bool(self.hubspot_api_key)

    def is_stitch_configured(self) -> bool:
        """Check if Stitch API is configured."""
        return bool(self.stitch_api_key)

    def is_google_seo_configured(self) -> bool:
        """Check if Google Search Console / GA4 is configured."""
        return bool(self.google_seo_service_account_json)

    def is_google_analytics_configured(self) -> bool:
        """Check if Google Analytics 4 property is configured."""
        return bool(self.google_analytics_property_id)

    def get_status_summary(self) -> dict[str, Any]:
        """Get a summary of all configuration statuses."""
        return {
            "tavily": {
                "configured": self.is_tavily_configured(),
                "name": "Web Search (Tavily)",
            },
            "firecrawl": {
                "configured": self.is_firecrawl_configured(),
                "name": "Web Scraping (Firecrawl)",
            },
            "supabase": {
                "configured": self.is_supabase_configured(),
                "name": "Database (Supabase)",
            },
            "resend": {
                "configured": self.is_email_configured(),
                "name": "Email (Resend)",
            },
            "hubspot": {
                "configured": self.is_crm_configured(),
                "name": "CRM (HubSpot)",
            },
            "stitch": {
                "configured": self.is_stitch_configured(),
                "name": "Landing Pages (Stitch)",
            },
            "google_seo": {
                "configured": self.is_google_seo_configured(),
                "name": "Google Search Console",
            },
            "google_analytics": {
                "configured": self.is_google_analytics_configured(),
                "name": "Google Analytics 4",
            },
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
        resend_api_key=os.environ.get("RESEND_API_KEY"),
        resend_from_email=os.environ.get("RESEND_FROM_EMAIL", "noreply@pikar.ai"),
        # CRM
        hubspot_api_key=os.environ.get("HUBSPOT_API_KEY"),
        # Landing Page Builder (Stitch)
        stitch_api_key=os.environ.get("STITCH_API_KEY"),
        stitch_api_url=os.environ.get(
            "STITCH_API_URL", "https://stitch.withgoogle.com/api"
        ),
        # Google SEO (Search Console + GA4)
        google_seo_service_account_json=os.environ.get(
            "GOOGLE_SEO_SERVICE_ACCOUNT_JSON"
        ),
        google_analytics_property_id=os.environ.get("GOOGLE_ANALYTICS_PROPERTY_ID"),
        # Rate Limiting
        search_rate_limit_per_minute=int(os.environ.get("MCP_SEARCH_RATE_LIMIT", "30")),
        scrape_rate_limit_per_minute=int(os.environ.get("MCP_SCRAPE_RATE_LIMIT", "10")),
        crawl_rate_limit_per_minute=int(os.environ.get("MCP_CRAWL_RATE_LIMIT", "5")),
        # Audit Logging
        audit_log_enabled=os.environ.get("MCP_AUDIT_LOG_ENABLED", "true").lower()
        == "true",
        audit_log_table=os.environ.get("MCP_AUDIT_LOG_TABLE", "mcp_audit_logs"),
    )


def clear_config_cache() -> None:
    """Clear the configuration cache.

    Call this if environment variables have been updated and you need
    to reload the configuration.
    """
    get_mcp_config.cache_clear()
