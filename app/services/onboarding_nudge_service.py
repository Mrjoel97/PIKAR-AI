# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Onboarding Nudge Service -- contextual encouragement for new users.

Detects stalled users within their first 7 days and generates contextual
nudges tied to the specific incomplete onboarding step or checklist item.
Nudges are only generated when the user has been inactive for >24 hours.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client
from app.services.user_onboarding_service import (
    OnboardingStatus,
    get_user_onboarding_service,
)

logger = logging.getLogger(__name__)

# Module-level singleton
_service_instance: OnboardingNudgeService | None = None

# Contextual nudge messages keyed by the step that is stalled
_STEP_NUDGES: dict[str, dict[str, str]] = {
    "preferences": {
        "step_name": "preferences",
        "message": (
            "You've set up your business context -- nice! Setting your "
            "preferences takes about 30 seconds and helps me match your "
            "communication style."
        ),
        "suggested_action": "Set up your preferences now",
    },
    "agent_setup": {
        "step_name": "agent_setup",
        "message": (
            "Almost there! Giving your agent a name makes the experience "
            "feel more personal. It only takes a moment."
        ),
        "suggested_action": "Name your agent",
    },
    "complete_onboarding": {
        "step_name": "complete_onboarding",
        "message": (
            "You're just one step away from unlocking everything. "
            "Finish onboarding to get your personalized checklist."
        ),
        "suggested_action": "Complete onboarding",
    },
}

# Contextual nudge templates for checklist items
_CHECKLIST_NUDGES: dict[str, str] = {
    "brain_dump": (
        "Many solopreneurs find the Brain Dump incredibly useful for "
        "getting clarity. Want to try recording your thoughts?"
    ),
    "revenue_strategy": (
        "Mapping your revenue strategy takes just a few minutes and "
        "can surface opportunities you hadn't considered."
    ),
    "weekly_plan": (
        "A focused weekly plan keeps you moving forward. "
        "Want me to help you plan your next 7 days?"
    ),
    "first_workflow": (
        "Automating a repetitive task saves real time. "
        "Want to try running your first workflow?"
    ),
    "content_piece": (
        "Creating your first content piece is a great way to build "
        "momentum. I can help you draft something right now."
    ),
    "growth_experiment": (
        "A quick growth experiment can teach you a lot about your "
        "market. Want to design one together?"
    ),
    "pitch_review": (
        "Sharpening your pitch is one of the highest-leverage things "
        "you can do. Want me to review it?"
    ),
    "burn_rate": (
        "Understanding your runway is critical for planning. "
        "Want to check your burn rate?"
    ),
    "team_update": (
        "A concise team update keeps everyone aligned. "
        "Want help writing one?"
    ),
    "dept_health": (
        "A department health check gives you a quick read on each team. "
        "Want to run one now?"
    ),
    "process_audit": (
        "Auditing your processes can reveal hidden bottlenecks. "
        "Want to get started?"
    ),
    "compliance_review": (
        "A quick compliance review ensures nothing is falling through "
        "cracks. Want me to start one?"
    ),
    "kpi_dashboard": (
        "Tracking the right metrics makes all the difference. "
        "Want to set up KPI tracking?"
    ),
    "stakeholder_briefing": (
        "A well-structured stakeholder briefing builds confidence. "
        "Want help preparing one?"
    ),
    "risk_assessment": (
        "Identifying risks early gives you more options to mitigate them. "
        "Want to run a risk assessment?"
    ),
    "portfolio_review": (
        "Reviewing your initiative portfolio ensures you're focused on "
        "the right bets. Want to take a look?"
    ),
    "approval_workflow": (
        "Setting up governance controls brings order to decision-making. "
        "Want to configure an approval workflow?"
    ),
}


class OnboardingNudgeService:
    """Service that checks onboarding progress and generates contextual nudges.

    Singleton -- use :func:`get_onboarding_nudge_service` to obtain the instance.
    """

    def __init__(self) -> None:
        self._client = get_service_client()

    async def check_nudges(self, user_id: str) -> list[dict[str, Any]]:
        """Check if the user has any onboarding nudges to show.

        Returns an empty list if:
        - The user account is older than 7 days.
        - The user was active within the last 24 hours.
        - Onboarding + checklist are fully complete.

        Otherwise returns contextual nudge(s) for the specific stalled step.

        Args:
            user_id: The user to check nudges for.

        Returns:
            List of nudge dicts, each with nudge_type, step_name, message,
            and suggested_action.
        """
        try:
            onb_svc = get_user_onboarding_service()
            status = await onb_svc.get_onboarding_status(user_id)

            # If onboarding is complete, check checklist items
            if status.is_completed:
                return await self._check_completed_user(user_id, status)

            # Onboarding not complete -- check 7-day window first
            return await self._check_incomplete_user(user_id, status)

        except Exception:
            logger.warning(
                "Failed to check nudges for user=%s",
                user_id,
                exc_info=True,
            )
            return []

    async def _check_completed_user(
        self, user_id: str, status: OnboardingStatus
    ) -> list[dict[str, Any]]:
        """Check for checklist nudges when onboarding is complete."""
        # Get checklist items
        checklist_resp = await execute_async(
            self._client.table("onboarding_checklist")
            .select("items")
            .eq("user_id", user_id)
            .limit(1),
            op_name="nudge.checklist",
        )

        checklist_data = checklist_resp.data
        if not checklist_data:
            return []

        items = checklist_data[0].get("items", [])
        incomplete = [i for i in items if not i.get("completed", False)]
        if not incomplete:
            return []

        # Check 7-day window
        if not await self._within_7_day_window(user_id):
            return []

        # Check activity recency
        if await self._active_within_24h(user_id):
            return []

        # Generate checklist nudge for the first incomplete item
        nudge = self._generate_checklist_nudge(incomplete, status.persona or "startup")
        return [nudge] if nudge else []

    async def _check_incomplete_user(
        self, user_id: str, status: OnboardingStatus
    ) -> list[dict[str, Any]]:
        """Check for onboarding step nudges when onboarding is incomplete."""
        # Check 7-day window first
        if not await self._within_7_day_window(user_id):
            return []

        # Check activity recency
        if await self._active_within_24h(user_id):
            return []

        # Generate step-specific nudge
        nudge = self._generate_step_nudge(status)
        return [nudge] if nudge else []

    async def _within_7_day_window(self, user_id: str) -> bool:
        """Check if the user account is within the 7-day onboarding window."""
        profile_resp = await execute_async(
            self._client.table("users_profile")
            .select("created_at")
            .eq("user_id", user_id)
            .limit(1),
            op_name="nudge.profile_age",
        )

        if not profile_resp.data:
            return False

        created_str = profile_resp.data[0].get("created_at")
        if not created_str:
            return False

        created_at = datetime.fromisoformat(created_str)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        return created_at > cutoff

    async def _active_within_24h(self, user_id: str) -> bool:
        """Check if the user had any interaction in the last 24 hours."""
        activity_resp = await execute_async(
            self._client.table("interaction_logs")
            .select("created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1),
            op_name="nudge.last_activity",
        )

        if not activity_resp.data:
            # No activity at all -- treat as stalled
            return False

        last_str = activity_resp.data[0].get("created_at")
        if not last_str:
            return False

        last_at = datetime.fromisoformat(last_str)
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=timezone.utc)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        return last_at > cutoff

    def _generate_step_nudge(self, status: OnboardingStatus) -> dict[str, Any] | None:
        """Generate a nudge for the specific stalled onboarding step.

        Args:
            status: Current onboarding status.

        Returns:
            A nudge dict or None if no nudge applies.
        """
        if not status.business_context_completed:
            return {
                "nudge_type": "onboarding_step",
                "step_name": "business_context",
                "message": (
                    "Getting started is easy -- tell me about your business "
                    "and I'll personalize everything for you. It takes less "
                    "than a minute."
                ),
                "suggested_action": "Set up your business context",
            }

        if not status.preferences_completed:
            return {
                "nudge_type": "onboarding_step",
                **_STEP_NUDGES["preferences"],
            }

        if not status.agent_setup_completed:
            return {
                "nudge_type": "onboarding_step",
                **_STEP_NUDGES["agent_setup"],
            }

        # All steps done but onboarding not marked complete
        return {
            "nudge_type": "onboarding_step",
            **_STEP_NUDGES["complete_onboarding"],
        }

    def _generate_checklist_nudge(
        self, incomplete_items: list[dict[str, Any]], persona: str
    ) -> dict[str, Any] | None:
        """Generate a nudge for the next incomplete checklist item.

        Args:
            incomplete_items: List of incomplete checklist item dicts.
            persona: User persona for context.

        Returns:
            A nudge dict or None.
        """
        if not incomplete_items:
            return None

        item = incomplete_items[0]
        item_id = item.get("id", "")
        item_title = item.get("title", item_id)

        message = _CHECKLIST_NUDGES.get(
            item_id,
            f"You haven't tried '{item_title}' yet -- it's a quick win that can help you move forward.",
        )

        return {
            "nudge_type": "checklist_item",
            "step_name": item_id,
            "message": message,
            "suggested_action": item_title,
        }


def get_onboarding_nudge_service() -> OnboardingNudgeService:
    """Return the singleton OnboardingNudgeService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = OnboardingNudgeService()
    return _service_instance
