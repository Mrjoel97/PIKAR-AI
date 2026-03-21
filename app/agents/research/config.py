"""Domain-specific configuration for the Research Intelligence System.

Defines freshness thresholds, cache TTLs, and research depth parameters
per agent domain. These values drive the adaptive router and continuous
intelligence scheduler.
"""

from __future__ import annotations

DOMAIN_FRESHNESS: dict[str, dict[str, int | float]] = {
    "financial": {"default_hours": 4, "critical_hours": 1, "expiry_days": 7},
    "marketing": {"default_hours": 12, "critical_hours": 4, "expiry_days": 14},
    "compliance": {"default_hours": 24, "critical_hours": 2, "expiry_days": 30},
    "sales": {"default_hours": 8, "critical_hours": 2, "expiry_days": 7},
    "strategic": {"default_hours": 12, "critical_hours": 4, "expiry_days": 14},
    "operations": {"default_hours": 24, "critical_hours": 8, "expiry_days": 30},
    "hr": {"default_hours": 48, "critical_hours": 24, "expiry_days": 60},
    "customer_support": {"default_hours": 8, "critical_hours": 2, "expiry_days": 7},
    "data": {"default_hours": 12, "critical_hours": 4, "expiry_days": 14},
    "content": {"default_hours": 24, "critical_hours": 8, "expiry_days": 30},
}

DEFAULT_FRESHNESS_HOURS = 24


def get_cache_ttl_seconds(domain: str) -> int:
    """Return Redis cache TTL in seconds for a domain's graph_read results.

    Uses the domain's default_hours freshness threshold. Unknown domains
    get a 24-hour default.

    Args:
        domain: Agent domain name (e.g., 'financial', 'hr').

    Returns:
        Cache TTL in seconds.
    """
    config = DOMAIN_FRESHNESS.get(domain)
    if config is None:
        return DEFAULT_FRESHNESS_HOURS * 3600
    return int(config["default_hours"] * 3600)
