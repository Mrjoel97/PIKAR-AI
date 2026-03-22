"""Tests for admin research router."""

from __future__ import annotations


def test_research_router_imports():
    """Research router can be imported without errors."""
    from app.routers.admin.research import router
    assert router is not None


def test_research_router_has_endpoints():
    """Router has the expected number of routes."""
    from app.routers.admin.research import router
    routes = [r for r in router.routes if hasattr(r, "methods")]
    assert len(routes) >= 15


def test_research_router_registered():
    """Research router is included in admin router."""
    from app.routers.admin import admin_router
    # Check that at least one research-prefixed route exists
    paths = []
    for route in admin_router.routes:
        if hasattr(route, "path"):
            paths.append(route.path)
        elif hasattr(route, "routes"):
            # Sub-router
            for sub in route.routes:
                if hasattr(sub, "path"):
                    paths.append(sub.path)
    assert any("research" in p for p in paths)
