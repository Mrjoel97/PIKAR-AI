# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Feature gate middleware for persona tier enforcement.

Provides a FastAPI dependency factory ``require_feature`` that checks the
caller's persona tier before allowing an endpoint to execute.

Usage in routers::

    from app.middleware.feature_gate import require_feature

    router = APIRouter(
        prefix="/compliance",
        tags=["Compliance"],
        dependencies=[Depends(require_feature("compliance"))],
    )

    # Or per-endpoint:
    @router.get("/audits")
    async def list_audits(
        request: Request,
        user_id: str = Depends(get_current_user_id),
        _gate: None = Depends(require_feature("compliance")),
    ):
        ...

The dependency resolves persona from the request cookie/header first (fast
path), then falls back to a DB profile lookup via ``resolve_effective_persona``.
A missing or unknown persona is treated as "solopreneur" (lowest tier).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request

from app.config.feature_gating import (
    FEATURE_ACCESS,
    get_required_tier,
    is_feature_allowed,
)
from app.personas.runtime import resolve_effective_persona
from app.routers.onboarding import get_current_user_id

logger = logging.getLogger(__name__)


def require_feature(feature_key: str) -> Callable[..., Any]:
    """Create a FastAPI dependency that gates an endpoint by feature key.

    Returns HTTP 403 with a structured upgrade message if the user's persona
    tier is below the feature's minimum tier requirement.  The restricted
    endpoint handler is never executed.

    Args:
        feature_key: The feature identifier defined in ``FEATURE_ACCESS``
            (e.g. ``"workflows"``, ``"compliance"``).

    Returns:
        An async FastAPI dependency callable suitable for use in
        ``Depends(require_feature(...))`` or router-level ``dependencies=[...]``.
    """

    async def _check_feature_gate(
        request: Request,
        user_id: str = Depends(get_current_user_id),
    ) -> None:
        """Inner dependency: resolve tier and enforce feature gate.

        Args:
            request: The incoming HTTP request (injected by FastAPI).
            user_id: The authenticated user ID from the JWT (injected by FastAPI).

        Raises:
            HTTPException: HTTP 403 with structured upgrade payload when the
                user's tier does not meet the feature's minimum tier requirement.
        """
        persona = await resolve_effective_persona(
            user_id=user_id,
            request=request,
        )

        if not persona:
            # No persona resolved — treat as lowest tier (solopreneur)
            persona = "solopreneur"

        if not is_feature_allowed(feature_key, persona):
            required = get_required_tier(feature_key)
            feature_meta = FEATURE_ACCESS.get(feature_key, {})
            label = feature_meta.get("label", feature_key)
            logger.info(
                "Feature gate blocked: user=%s tier=%s feature=%s required=%s",
                user_id,
                persona,
                feature_key,
                required,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "feature_gated",
                    "message": (
                        f"{label} requires {required} tier or higher. "
                        f"Your current tier is {persona}."
                    ),
                    "feature": feature_key,
                    "current_tier": persona,
                    "required_tier": required,
                    "upgrade_url": "/dashboard/billing",
                },
            )

    return _check_feature_gate
