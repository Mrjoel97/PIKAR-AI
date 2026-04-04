# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for solopreneur feature gating unlock.

Verifies that solopreneur persona has access to all features EXCEPT
teams and governance, and that other tier access levels remain unchanged.
"""

from __future__ import annotations

import pytest

from app.config.feature_gating import FEATURE_ACCESS, TIER_ORDER, is_feature_allowed


# ── Solopreneur unlocked features ────────────────────────────────────────────


def test_solopreneur_workflows_access() -> None:
    """Solopreneur must have access to the Workflow Engine."""
    assert is_feature_allowed("workflows", "solopreneur") is True


def test_solopreneur_custom_workflows_access() -> None:
    """Solopreneur must have access to Custom Workflows."""
    assert is_feature_allowed("custom-workflows", "solopreneur") is True


def test_solopreneur_sales_reports_access() -> None:
    """Solopreneur must have access to Sales, Reports, and Approvals."""
    assert is_feature_allowed("sales", "solopreneur") is True
    assert is_feature_allowed("reports", "solopreneur") is True
    assert is_feature_allowed("approvals", "solopreneur") is True


def test_solopreneur_compliance_finance_access() -> None:
    """Solopreneur must have access to Compliance and Financial Forecasting."""
    assert is_feature_allowed("compliance", "solopreneur") is True
    assert is_feature_allowed("finance-forecasting", "solopreneur") is True


# ── Solopreneur restricted features ─────────────────────────────────────────


def test_solopreneur_restricted_features() -> None:
    """Solopreneur must NOT have access to Teams or Governance."""
    assert is_feature_allowed("teams", "solopreneur") is False
    assert is_feature_allowed("governance", "solopreneur") is False


# ── Other tiers unaffected ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "feature_key,tier,expected",
    [
        # Startup — gets all unlocked features (min_tier=solopreneur) + teams
        # Only governance (enterprise) is restricted
        ("workflows", "startup", True),
        ("sales", "startup", True),
        ("reports", "startup", True),
        ("approvals", "startup", True),
        ("teams", "startup", True),
        ("compliance", "startup", True),
        ("finance-forecasting", "startup", True),
        ("custom-workflows", "startup", True),
        ("governance", "startup", False),
        # SME — gets everything except governance
        ("workflows", "sme", True),
        ("compliance", "sme", True),
        ("finance-forecasting", "sme", True),
        ("teams", "sme", True),
        ("custom-workflows", "sme", True),
        ("governance", "sme", False),
        # Enterprise — gets everything
        ("workflows", "enterprise", True),
        ("compliance", "enterprise", True),
        ("custom-workflows", "enterprise", True),
        ("governance", "enterprise", True),
        ("teams", "enterprise", True),
    ],
    ids=lambda x: str(x),
)
def test_other_tiers_unaffected(feature_key: str, tier: str, expected: bool) -> None:
    """Access levels for startup, sme, and enterprise tiers remain unchanged."""
    assert is_feature_allowed(feature_key, tier) is expected


# ── Config consistency ───────────────────────────────────────────────────────


def test_feature_access_min_tier_values() -> None:
    """Verify the exact min_tier values in FEATURE_ACCESS after unlock."""
    expected_tiers = {
        "workflows": "solopreneur",
        "sales": "solopreneur",
        "reports": "solopreneur",
        "approvals": "solopreneur",
        "compliance": "solopreneur",
        "finance-forecasting": "solopreneur",
        "custom-workflows": "solopreneur",
        "governance": "enterprise",
        "teams": "startup",
    }
    for key, expected_min in expected_tiers.items():
        actual = FEATURE_ACCESS[key]["min_tier"]
        assert actual == expected_min, (
            f"Feature '{key}' min_tier is '{actual}', expected '{expected_min}'"
        )
