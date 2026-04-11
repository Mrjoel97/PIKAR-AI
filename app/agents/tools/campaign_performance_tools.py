# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Campaign performance tools -- plain-English paid-media reporting.

Exposes the CampaignPerformanceSummarizer service as an agent-callable
tool. The Marketing Agent uses this whenever a user asks "how are my
ads doing?" or "campaign performance" -- it returns both a ready-made
natural-language paragraph (summary_text) and the underlying structured
metrics the agent can use to answer follow-ups without calling another
tool.

Lazy imports mirror ad_platform_tools.py so importing the tool module
never triggers the full ad-service chain.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


async def summarize_campaign_performance(days: int = 7) -> dict[str, Any]:
    """Return a plain-English performance summary for all of the user's ad campaigns.

    Aggregates Google Ads and Meta Ads spend, conversions, and cost-per-
    acquisition across the reporting window, and produces a natural-
    language paragraph the agent can show the user directly -- for
    example:

        "Your Google Ads spent $340.00 this week and brought 12 customers
         at $28.33 each -- 20% better than last week."

    The tool also returns the full structured result so the agent can
    answer follow-up questions about per-campaign breakdowns without
    re-issuing the query.

    Args:
        days: Size of the reporting window in days (default 7 = this week).

    Returns:
        Dict with:
          - summary_text: ready-to-show natural-language paragraph
          - total_spend, total_conversions, overall_cpa
          - wow_spend_change_pct, wow_conversions_change_pct
          - per_campaign: list of campaign-level breakdowns
          - period, prior_period: date windows used for the comparison
        On auth failure: {"error": "Authentication required"}.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    if days <= 0:
        return {"error": "days must be a positive integer."}

    try:
        from app.services.campaign_performance_summarizer import (
            CampaignPerformanceSummarizer,
        )

        summarizer = CampaignPerformanceSummarizer()
        return await summarizer.summarize_all_platforms(user_id=user_id, days=days)
    except Exception as exc:
        logger.exception(
            "summarize_campaign_performance failed for user=%s days=%s",
            user_id,
            days,
        )
        return {"error": f"Failed to summarize campaign performance: {exc}"}


CAMPAIGN_PERFORMANCE_TOOLS = [summarize_campaign_performance]
