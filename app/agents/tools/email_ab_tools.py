# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Email A/B testing agent tools.

Thin wrappers around :class:`app.services.email_ab_testing_service.EmailABTestingService`
exposed as agent-callable functions.  These live on the EmailMarketingAgent
sub-agent (see ``app/agents/marketing/agent.py``) and enable the agent to
offer subject-line / body A/B tests during sequence creation.

Tools
-----
- ``create_ab_test``  -- fork a sequence step into two variants
- ``get_ab_test_results`` -- fetch per-variant metrics + winner suggestion

Each tool resolves the current ``user_id`` from request context so callers
don't have to pass it explicitly.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


# ---------------------------------------------------------------------------
# Tool: create_ab_test
# ---------------------------------------------------------------------------


async def create_ab_test(
    sequence_id: str,
    step_index: int,
    variant_b_subject: str,
    variant_b_body: str,
    split_pct: int = 50,
) -> dict[str, Any]:
    """Create an A/B test on a single email sequence step.

    The step at ``step_index`` becomes Variant A (original copy preserved)
    and a new Variant B row is added with the supplied subject/body. Both
    variants share a freshly-generated ``ab_test_id`` stored inside
    ``email_sequence_steps.metadata``.

    Args:
        sequence_id: Target sequence UUID.
        step_index: ``step_number`` of the step to fork.
        variant_b_subject: Subject line for Variant B.
        variant_b_body: Body template for Variant B.
        split_pct: Traffic share assigned to Variant B (0-100, default 50).

    Returns:
        Dict with ``ab_test_id``, ``variant_a``, ``variant_b``, ``split_pct``,
        or ``{"error": ...}`` on auth/validation failures.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.email_ab_testing_service import EmailABTestingService

    try:
        svc = EmailABTestingService()
        result = await svc.create_ab_test(
            user_id=user_id,
            sequence_id=sequence_id,
            step_index=step_index,
            variant_b_subject=variant_b_subject,
            variant_b_body=variant_b_body,
            split_pct=split_pct,
        )
        return result
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception(
            "create_ab_test failed for user=%s sequence=%s", user_id, sequence_id
        )
        return {"error": f"Failed to create A/B test: {exc}"}


# ---------------------------------------------------------------------------
# Tool: get_ab_test_results
# ---------------------------------------------------------------------------


async def get_ab_test_results(
    sequence_id: str,
    ab_test_id: str,
) -> dict[str, Any]:
    """Fetch per-variant metrics for an A/B test.

    Returns open_rate, click_rate, and sample sizes for both variants
    plus a winner recommendation.  When a winner is determined the
    response includes a ``suggestion`` field prompting the user to
    apply the winning variant as the permanent step copy.

    Args:
        sequence_id: Sequence UUID.
        ab_test_id: A/B test identifier returned by :func:`create_ab_test`.

    Returns:
        Dict with ``variant_a``, ``variant_b``, ``winner``,
        ``confidence_note``, and (when a winner exists) ``suggestion``.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.email_ab_testing_service import EmailABTestingService

    try:
        svc = EmailABTestingService()
        result = await svc.get_results(
            user_id=user_id,
            sequence_id=sequence_id,
            ab_test_id=ab_test_id,
        )
        winner = result.get("winner")
        if winner in ("A", "B"):
            result["suggestion"] = (
                f"Variant {winner} is winning. Want me to apply it as the "
                f"permanent version of this step?"
            )
        return result
    except Exception as exc:
        logger.exception(
            "get_ab_test_results failed for user=%s sequence=%s ab_test=%s",
            user_id,
            sequence_id,
            ab_test_id,
        )
        return {"error": f"Failed to fetch A/B test results: {exc}"}


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

EMAIL_AB_TOOLS = [create_ab_test, get_ab_test_results]
