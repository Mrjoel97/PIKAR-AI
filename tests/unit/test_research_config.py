"""Tests for research domain configuration."""


def test_domain_freshness_has_all_domains():
    """All 10 agent domains must have freshness config."""
    from app.agents.research.config import DOMAIN_FRESHNESS

    expected_domains = {
        "financial",
        "marketing",
        "compliance",
        "sales",
        "strategic",
        "operations",
        "hr",
        "customer_support",
        "data",
        "content",
    }
    assert set(DOMAIN_FRESHNESS.keys()) == expected_domains


def test_domain_freshness_values_are_valid():
    """Each domain config must have default_hours, critical_hours, expiry_days."""
    from app.agents.research.config import DOMAIN_FRESHNESS

    for domain, config in DOMAIN_FRESHNESS.items():
        assert "default_hours" in config, f"{domain} missing default_hours"
        assert "critical_hours" in config, f"{domain} missing critical_hours"
        assert "expiry_days" in config, f"{domain} missing expiry_days"
        assert config["critical_hours"] < config["default_hours"], (
            f"{domain}: critical_hours must be < default_hours"
        )
        assert config["default_hours"] < config["expiry_days"] * 24, (
            f"{domain}: default_hours must be < expiry_days in hours"
        )


def test_cache_ttl_for_domain():
    """Cache TTL helper returns correct seconds."""
    from app.agents.research.config import get_cache_ttl_seconds

    ttl = get_cache_ttl_seconds("financial")
    assert ttl == 4 * 3600  # 4 hours in seconds

    ttl = get_cache_ttl_seconds("hr")
    assert ttl == 48 * 3600  # 48 hours in seconds


def test_cache_ttl_unknown_domain_returns_default():
    """Unknown domain returns 24-hour default TTL."""
    from app.agents.research.config import get_cache_ttl_seconds

    ttl = get_cache_ttl_seconds("nonexistent_domain")
    assert ttl == 24 * 3600
