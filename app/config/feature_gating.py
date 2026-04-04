# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Centralized feature gating configuration.

Single source of truth for backend tier-to-feature access.
Must stay in sync with frontend/src/config/featureGating.ts.
"""

from __future__ import annotations

# Ordered from lowest to highest tier
TIER_ORDER: list[str] = ["solopreneur", "startup", "sme", "enterprise"]

# Maps feature key to { label, description, min_tier }
# Keep in sync with frontend/src/config/featureGating.ts access matrix
FEATURE_ACCESS: dict[str, dict[str, str]] = {
    "workflows": {
        "label": "Workflow Engine",
        "description": "Automate multi-step business processes",
        "min_tier": "solopreneur",
    },
    "sales": {
        "label": "Sales Pipeline & CRM",
        "description": "Track deals, manage pipeline, forecast revenue",
        "min_tier": "solopreneur",
    },
    "reports": {
        "label": "Reports",
        "description": "Generate and view business reports",
        "min_tier": "solopreneur",
    },
    "approvals": {
        "label": "Approvals",
        "description": "Multi-step approval workflows",
        "min_tier": "solopreneur",
    },
    "compliance": {
        "label": "Compliance Suite",
        "description": "Audit trails, risk management, regulatory compliance",
        "min_tier": "solopreneur",
    },
    "finance-forecasting": {
        "label": "Financial Forecasting",
        "description": "Revenue projections and financial modeling",
        "min_tier": "solopreneur",
    },
    "custom-workflows": {
        "label": "Custom Workflows",
        "description": "Build custom workflow templates",
        "min_tier": "solopreneur",
    },
    "governance": {
        "label": "SSO & Governance",
        "description": "Single sign-on and enterprise governance controls",
        "min_tier": "enterprise",
    },
    "teams": {
        "label": "Team Workspace",
        "description": "Share your workspace with team members and assign roles",
        "min_tier": "startup",
    },
}


def is_feature_allowed(feature_key: str, user_tier: str) -> bool:
    """Check if a user's tier meets the minimum requirement for a feature.

    Args:
        feature_key: The feature identifier (e.g. "workflows", "compliance").
        user_tier: The user's current persona tier (e.g. "solopreneur", "startup").

    Returns:
        True if the user's tier is at or above the feature's minimum tier,
        or if the feature key is not in the access matrix (ungated).
        False if the user_tier is unknown or below the required tier.
    """
    feature = FEATURE_ACCESS.get(feature_key)
    if not feature:
        return True  # Unknown features are ungated
    min_tier = feature["min_tier"]
    try:
        return TIER_ORDER.index(user_tier) >= TIER_ORDER.index(min_tier)
    except ValueError:
        return False  # Unknown tier = no access


def get_required_tier(feature_key: str) -> str | None:
    """Get the minimum tier required for a feature.

    Args:
        feature_key: The feature identifier (e.g. "workflows", "compliance").

    Returns:
        The minimum tier string, or None if the feature is not in the access matrix.
    """
    feature = FEATURE_ACCESS.get(feature_key)
    return feature["min_tier"] if feature else None
