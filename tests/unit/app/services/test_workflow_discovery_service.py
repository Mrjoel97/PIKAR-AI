# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for workflow discovery service.

Tests NL intent-based workflow search and content template retrieval.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.workflow_discovery_service import (
    ContentTemplate,
    WorkflowMatch,
    get_content_templates,
    search_workflows_by_intent,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_TEMPLATES = [
    {
        "id": "t1",
        "name": "Product Launch Campaign",
        "description": "Launch a new product with coordinated marketing",
        "category": "marketing",
    },
    {
        "id": "t2",
        "name": "Blog Post Creation",
        "description": "Create and publish a blog post with SEO optimization",
        "category": "content",
    },
    {
        "id": "t3",
        "name": "Monthly Financial Report",
        "description": "Generate monthly financial summaries and charts",
        "category": "finance",
    },
    {
        "id": "t4",
        "name": "Sales Pipeline Review",
        "description": "Review and update the sales pipeline status",
        "category": "sales",
    },
    {
        "id": "t5",
        "name": "Social Media Content Calendar",
        "description": "Plan and schedule social media posts for the week",
        "category": "marketing",
    },
    {
        "id": "t6",
        "name": "Customer Newsletter",
        "description": "Draft and send a customer newsletter with updates",
        "category": "content",
    },
    {
        "id": "t7",
        "name": "Competitive Analysis Report",
        "description": "Analyze competitor positioning and market trends",
        "category": "strategy",
    },
]


def _mock_engine():
    """Create a mock workflow engine with list_templates returning MOCK_TEMPLATES."""
    engine = AsyncMock()
    engine.list_templates = AsyncMock(return_value=MOCK_TEMPLATES)
    return engine


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(
    "app.services.workflow_discovery_service.get_workflow_engine",
    return_value=_mock_engine(),
)
async def test_search_launch_product(mock_engine):
    """search_workflows_by_intent('launch a product') returns product launch match."""
    results = await search_workflows_by_intent("launch a product")
    assert len(results) > 0
    names = [r.name.lower() for r in results]
    assert any("product launch" in n or "launch" in n for n in names)


@pytest.mark.asyncio
@patch(
    "app.services.workflow_discovery_service.get_workflow_engine",
    return_value=_mock_engine(),
)
async def test_search_blog_post(mock_engine):
    """search_workflows_by_intent('write a blog post') returns content workflows."""
    results = await search_workflows_by_intent("write a blog post")
    assert len(results) > 0
    names = [r.name.lower() for r in results]
    assert any("blog" in n for n in names)


@pytest.mark.asyncio
@patch(
    "app.services.workflow_discovery_service.get_workflow_engine",
    return_value=_mock_engine(),
)
async def test_search_nonexistent(mock_engine):
    """search_workflows_by_intent('xyznonexistent') returns empty list."""
    results = await search_workflows_by_intent("xyznonexistent")
    assert results == []


@pytest.mark.asyncio
async def test_get_content_templates_all():
    """get_content_templates() returns all templates with required fields."""
    results = await get_content_templates()
    assert len(results) >= 12
    for t in results:
        assert isinstance(t, ContentTemplate)
        assert t.name
        assert t.description
        assert t.category
        assert t.icon


@pytest.mark.asyncio
async def test_get_content_templates_by_category():
    """get_content_templates(category='marketing') filters to marketing only."""
    results = await get_content_templates(category="marketing")
    assert len(results) > 0
    for t in results:
        assert t.category == "marketing"


@pytest.mark.asyncio
@patch(
    "app.services.workflow_discovery_service.get_workflow_engine",
    return_value=_mock_engine(),
)
async def test_search_max_results_and_fields(mock_engine):
    """search_workflows_by_intent returns max 5 results with required fields."""
    results = await search_workflows_by_intent("marketing content social blog")
    assert len(results) <= 5
    for r in results:
        assert isinstance(r, WorkflowMatch)
        assert r.name
        assert r.description
        assert r.category
        assert 0.0 <= r.match_score <= 1.0
