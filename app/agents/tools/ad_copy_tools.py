# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Ad copy generation tools -- platform-aware format constraints and CRM context.

Provides two agent-callable functions:

1. ``get_ad_copy_context`` -- Returns platform-specific format constraints and
   CRM audience segment context so the agent LLM generates properly formatted
   ad copy. The agent calls this BEFORE writing copy to get character limits,
   headline counts, and audience data.

2. ``save_ad_copy_as_creative`` -- Creates an ad_creatives record via
   AdCreativeService once the agent has generated the copy. NON-GATED.

Platform constraints:
- Google Ads Search: 15 headlines (max 30 chars each), 4 descriptions (max 90)
- Meta Ads: primary_text (max 125), headline (max 40), description (max 30),
            CTA options list

CRM audience context (requires HubSpot connection):
- Lifecycle stage distribution (lead, qualified_lead, opportunity, customer, etc.)
- Top companies to personalize the copy hook
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform format constraints
# ---------------------------------------------------------------------------

PLATFORM_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "google_ads": {
        "format": "Search Ad",
        "headlines": {
            "count": 15,
            "shown_per_ad": 3,
            "max_chars": 30,
            "note": "Google shows 3 of your 15 headlines. Avoid punctuation at the end.",
        },
        "descriptions": {
            "count": 4,
            "shown_per_ad": 2,
            "max_chars": 90,
            "note": "Google shows 2 of your 4 descriptions.",
        },
        "display_url": {
            "max_chars": 15,
            "note": "Domain is auto-populated; you add 2 optional path fields.",
        },
        "tips": [
            "Include the primary keyword in at least one headline.",
            "Use a clear CTA in at least one headline (e.g. 'Get Started Free').",
            "Highlight unique value props across headlines (price, trust, urgency).",
            "Descriptions should expand on headlines with specific benefits.",
        ],
    },
    "meta_ads": {
        "format": "News Feed / Stories",
        "primary_text": {
            "max_chars": 125,
            "note": "Shown above the image/video. Lead with the hook in the first 3 lines.",
        },
        "headline": {
            "max_chars": 40,
            "note": "Shown below the image. Bold. State the value prop clearly.",
        },
        "description": {
            "max_chars": 30,
            "note": "Shown under the headline (not always displayed).",
        },
        "cta_options": [
            "Learn More",
            "Shop Now",
            "Sign Up",
            "Book Now",
            "Get Quote",
            "Contact Us",
            "Watch More",
            "Apply Now",
            "Download",
            "Get Offer",
        ],
        "tips": [
            "Primary text: hook in the first sentence (curiosity, pain point, bold claim).",
            "Use social proof in primary text where possible ('1,000+ businesses trust...').",
            "Headline: clear value prop or offer ('Free 14-Day Trial', 'Save 30% Today').",
            "Match the CTA to the funnel stage (awareness=Learn More, conversion=Shop Now).",
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


async def _get_crm_audience_context(user_id: str) -> dict[str, Any]:
    """Fetch CRM audience segment context from Supabase contacts.

    Queries the contacts table (synced from HubSpot) to build an audience
    summary: lifecycle stage distribution and top companies. Falls back
    gracefully if HubSpot is not connected or the table is empty.

    Args:
        user_id: The current user's UUID.

    Returns:
        Dict with lifecycle_distribution, top_companies, total_contacts,
        and crm_connected flag.
    """
    try:
        from app.services.base_service import AdminService
        from app.services.supabase_async import execute_async

        admin = AdminService()

        # Check if HubSpot is connected
        cred_result = await execute_async(
            admin.client.table("integration_credentials")
            .select("id")
            .eq("user_id", user_id)
            .eq("provider", "hubspot")
            .limit(1),
            op_name="ad_copy.hubspot_check",
        )
        if not cred_result.data:
            return {"crm_connected": False}

        # Fetch lifecycle stage distribution
        contacts_result = await execute_async(
            admin.client.table("contacts")
            .select("lifecycle_stage, company")
            .eq("user_id", user_id)
            .limit(500),
            op_name="ad_copy.contacts_summary",
        )
        rows = contacts_result.data or []

        if not rows:
            return {"crm_connected": True, "total_contacts": 0}

        # Tally lifecycle stages
        lifecycle_counts: dict[str, int] = {}
        companies: list[str] = []
        for row in rows:
            stage = row.get("lifecycle_stage") or "unknown"
            lifecycle_counts[stage] = lifecycle_counts.get(stage, 0) + 1
            if row.get("company"):
                companies.append(row["company"])

        # Top 5 companies by frequency
        company_freq: dict[str, int] = {}
        for c in companies:
            company_freq[c] = company_freq.get(c, 0) + 1
        top_companies = sorted(company_freq, key=lambda x: company_freq[x], reverse=True)[:5]

        return {
            "crm_connected": True,
            "total_contacts": len(rows),
            "lifecycle_distribution": lifecycle_counts,
            "top_companies": top_companies,
            "audience_note": (
                f"{len(rows)} contacts in CRM. "
                f"Primary stage: {max(lifecycle_counts, key=lifecycle_counts.get)!r}."
            ),
        }
    except Exception:
        logger.exception("_get_crm_audience_context failed for user=%s", user_id)
        return {"crm_connected": False, "error": "CRM context unavailable"}


# ---------------------------------------------------------------------------
# Tool 1: get_ad_copy_context
# ---------------------------------------------------------------------------


async def get_ad_copy_context(
    platform: str,
    campaign_name: str,
    objective: str,
    target_audience: str = "",
) -> dict[str, Any]:
    """Return platform format constraints and CRM audience context for ad copy.

    Call this BEFORE generating ad copy to understand character limits,
    headline counts, and audience segment data. The constraints returned
    should be followed precisely when writing copy — Google Ads will reject
    headlines over 30 chars.

    Args:
        platform: 'google_ads' or 'meta_ads'.
        campaign_name: Name of the campaign (used for context).
        objective: Campaign objective (e.g. 'lead_generation', 'sales', 'traffic').
        target_audience: Optional description of the intended audience.

    Returns:
        Dict with platform_constraints (format limits), crm_audience context,
        and campaign_context guidance for the LLM.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    constraints = PLATFORM_CONSTRAINTS.get(platform)
    if not constraints:
        return {
            "error": f"Unknown platform: {platform!r}. Use 'google_ads' or 'meta_ads'.",
        }

    # Fetch CRM audience context (non-blocking — graceful if unavailable)
    crm_audience = await _get_crm_audience_context(user_id)

    # Build campaign context guidance
    campaign_context = {
        "campaign_name": campaign_name,
        "objective": objective,
        "target_audience": target_audience,
        "funnel_guidance": _get_funnel_guidance(objective, platform),
    }

    return {
        "success": True,
        "platform": platform,
        "platform_constraints": constraints,
        "crm_audience": crm_audience,
        "campaign_context": campaign_context,
        "generation_instructions": (
            f"Generate {platform.replace('_', ' ').title()} ad copy for "
            f"'{campaign_name}'. Follow the character limits in "
            "platform_constraints exactly — Google Ads will reject any "
            "headline over 30 chars. Use the crm_audience data to "
            "personalize the hook and value proposition."
        ),
    }


def _get_funnel_guidance(objective: str, platform: str) -> str:
    """Return copy tone guidance based on campaign objective and platform.

    Args:
        objective: Campaign objective string.
        platform: Ad platform key.

    Returns:
        One-sentence copy tone guidance string.
    """
    objective_lower = objective.lower()
    if any(w in objective_lower for w in ["awareness", "brand", "reach"]):
        return "Top of funnel: lead with curiosity or a bold insight, not a hard sell."
    if any(w in objective_lower for w in ["traffic", "visit", "click"]):
        return "Mid funnel: lead with clear value prop and a specific reason to click."
    if any(w in objective_lower for w in ["lead", "sign", "register", "form"]):
        return "Lead gen: highlight a specific offer or free resource, low-friction CTA."
    if any(w in objective_lower for w in ["sale", "purchase", "conver", "revenue"]):
        return "Bottom funnel: price/urgency/social proof, strong action-oriented CTA."
    return "Balance value proposition with a clear action step."


# ---------------------------------------------------------------------------
# Tool 2: save_ad_copy_as_creative
# ---------------------------------------------------------------------------


async def save_ad_copy_as_creative(
    ad_campaign_id: str,
    platform: str,
    headline: str,
    description: str,
    primary_text: str = "",
    call_to_action: str = "Learn More",
    destination_url: str = "",
) -> dict[str, Any]:
    """Save generated ad copy as an ad creative record.

    Creates an ad_creatives row via AdCreativeService. NON-GATED — saving
    a draft creative does not start any spending.

    Args:
        ad_campaign_id: Local ad_campaigns UUID the creative belongs to.
        platform: 'google_ads' or 'meta_ads' (stored in creative specs).
        headline: Primary headline text.
        description: Ad description text.
        primary_text: Main body copy (Meta Ads only; optional for Google).
        call_to_action: CTA button text (default 'Learn More').
        destination_url: Landing page URL.

    Returns:
        Created creative record dict or error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.ad_management_service import AdCreativeService

        creative_svc = AdCreativeService()
        creative_name = f"{platform.replace('_', ' ').title()} Ad Copy"

        result = await creative_svc.create_creative(
            ad_campaign_id=ad_campaign_id,
            name=creative_name,
            creative_type="text_only",
            headline=headline,
            description=description,
            call_to_action=call_to_action,
            primary_text=primary_text or None,
            destination_url=destination_url or None,
            specs={"platform": platform},
            user_id=user_id,
        )
        return {
            "success": True,
            "platform": platform,
            "ad_campaign_id": ad_campaign_id,
            "creative_id": result.get("id"),
            "headline": headline,
            "description": description,
            "call_to_action": call_to_action,
            "status": "draft",
            "message": (
                "Ad copy saved as a draft creative. "
                "Review and update the destination_url before activating the campaign."
            ),
        }
    except Exception as exc:
        logger.exception("save_ad_copy_as_creative failed for user=%s", user_id)
        return {"error": f"Failed to save ad creative: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

AD_COPY_TOOLS = [
    get_ad_copy_context,
    save_ad_copy_as_creative,
]
