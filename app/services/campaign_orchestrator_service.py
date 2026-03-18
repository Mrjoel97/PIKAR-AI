"""CampaignOrchestratorService - 5-phase campaign lifecycle management.

Manages campaign phase transitions with approval gates:
  draft → review → approved → active → completed
             ↓                    ↓
           (pause)              (pause)

Integrates with the existing approval_requests system for review→approved gate.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.base_service import BaseService, AdminService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


VALID_PHASES = ("draft", "review", "approved", "active", "completed", "paused")

ALLOWED_TRANSITIONS = {
    "draft": ["review", "paused"],
    "review": ["approved", "draft", "paused"],
    "approved": ["active", "paused"],
    "active": ["completed", "paused"],
    "paused": ["draft", "review", "approved", "active"],
    "completed": [],
}


class CampaignOrchestratorService(BaseService):
    """Service for managing campaign phase lifecycle with approval gates.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        super().__init__(user_token)

    async def get_campaign_phase(
        self,
        campaign_id: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Get the current phase and full phase history for a campaign.

        Args:
            campaign_id: The campaign ID.
            user_id: Optional user ID override.

        Returns:
            Dict with current_phase and phase_history.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client

        # Get campaign current_phase
        campaign_query = (
            client.table("campaigns")
            .select("id, name, status, current_phase, utm_config, channels, budget, goals")
            .eq("id", campaign_id)
        )
        if not self.is_authenticated and effective_user_id:
            campaign_query = campaign_query.eq("user_id", effective_user_id)
        campaign_resp = await execute_async(campaign_query.single())

        # Get phase history
        history_query = (
            client.table("campaign_phases")
            .select("*")
            .eq("campaign_id", campaign_id)
            .order("entered_at", desc=False)
        )
        history_resp = await execute_async(history_query)

        return {
            "campaign": campaign_resp.data,
            "current_phase": campaign_resp.data.get("current_phase", "draft"),
            "phase_history": history_resp.data,
        }

    async def advance_phase(
        self,
        campaign_id: str,
        target_phase: str,
        notes: str = None,
        metadata: dict = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Advance a campaign to the next phase.

        Validates the transition is allowed. If transitioning from review→approved,
        creates an approval request and returns the approval link.

        Args:
            campaign_id: The campaign ID.
            target_phase: Phase to transition to.
            notes: Optional notes for the transition.
            metadata: Optional metadata for the phase record.
            user_id: Optional user ID override.

        Returns:
            Dict with phase transition result and optional approval_link.
        """
        if target_phase not in VALID_PHASES:
            raise Exception(f"Invalid phase: {target_phase}. Must be one of {VALID_PHASES}")

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client

        # Get current phase
        campaign_query = (
            client.table("campaigns")
            .select("id, name, current_phase, user_id")
            .eq("id", campaign_id)
        )
        if not self.is_authenticated and effective_user_id:
            campaign_query = campaign_query.eq("user_id", effective_user_id)
        campaign_resp = await execute_async(campaign_query.single())
        campaign = campaign_resp.data
        current_phase = campaign.get("current_phase", "draft")

        # Validate transition
        allowed = ALLOWED_TRANSITIONS.get(current_phase, [])
        if target_phase not in allowed:
            raise Exception(
                f"Cannot transition from '{current_phase}' to '{target_phase}'. "
                f"Allowed transitions: {allowed}"
            )

        result = {"campaign_id": campaign_id, "from_phase": current_phase, "to_phase": target_phase}

        # If moving to review→approved, create an approval request
        approval_link = None
        approval_request_id = None
        if current_phase == "review" and target_phase == "approved":
            approval_result = await self._create_approval_request(
                campaign_id=campaign_id,
                campaign_name=campaign.get("name", "Unnamed Campaign"),
                user_id=effective_user_id,
                client=client,
            )
            approval_link = approval_result.get("link")
            approval_request_id = approval_result.get("id")
            result["approval_link"] = approval_link
            result["approval_status"] = "pending"
            result["message"] = (
                f"Approval request created for campaign '{campaign.get('name')}'. "
                "Share the approval link with the reviewer. "
                "Campaign will advance to 'approved' once the request is approved."
            )
            # Don't actually advance yet — wait for approval
            # Record the review→pending transition
            await self._record_phase(
                campaign_id=campaign_id,
                phase="review",
                notes=notes or "Awaiting approval",
                approval_request_id=approval_request_id,
                metadata=metadata or {},
                user_id=effective_user_id,
                client=client,
            )
            return result

        # Close the current phase
        await self._close_current_phase(campaign_id, client)

        # Record the new phase
        await self._record_phase(
            campaign_id=campaign_id,
            phase=target_phase,
            notes=notes,
            approval_request_id=approval_request_id,
            metadata=metadata or {},
            user_id=effective_user_id,
            client=client,
        )

        # Update campaign current_phase and status
        status_map = {
            "draft": "draft",
            "review": "draft",
            "approved": "draft",
            "active": "active",
            "completed": "completed",
            "paused": "paused",
        }
        await execute_async(
            client.table("campaigns")
            .update({
                "current_phase": target_phase,
                "status": status_map.get(target_phase, "draft"),
            })
            .eq("id", campaign_id)
        )

        result["message"] = f"Campaign advanced from '{current_phase}' to '{target_phase}'"
        return result

    async def approve_campaign(
        self,
        campaign_id: str,
        notes: str = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Approve a campaign that's in review (shortcut that skips magic link).

        Used when the agent owner approves directly in chat.

        Args:
            campaign_id: The campaign ID.
            notes: Optional approval notes.
            user_id: Optional user ID override.

        Returns:
            Dict with the phase transition result.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client

        # Verify campaign is in review
        campaign_query = (
            client.table("campaigns")
            .select("id, current_phase")
            .eq("id", campaign_id)
        )
        if not self.is_authenticated and effective_user_id:
            campaign_query = campaign_query.eq("user_id", effective_user_id)
        campaign_resp = await execute_async(campaign_query.single())
        current_phase = campaign_resp.data.get("current_phase", "draft")

        if current_phase != "review":
            raise Exception(
                f"Campaign is in '{current_phase}' phase, not 'review'. "
                "Only campaigns in review can be approved."
            )

        # Close review phase, advance to approved
        await self._close_current_phase(campaign_id, client)
        await self._record_phase(
            campaign_id=campaign_id,
            phase="approved",
            notes=notes or "Approved by user",
            metadata={"approved_by": "direct"},
            user_id=effective_user_id,
            client=client,
        )
        await execute_async(
            client.table("campaigns")
            .update({"current_phase": "approved", "status": "draft"})
            .eq("id", campaign_id)
        )

        return {
            "campaign_id": campaign_id,
            "from_phase": "review",
            "to_phase": "approved",
            "message": "Campaign approved. Ready to launch — advance to 'active' when ready.",
        }

    async def _create_approval_request(
        self,
        campaign_id: str,
        campaign_name: str,
        user_id: str,
        client,
    ) -> dict:
        """Create an approval_requests record for campaign review."""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

        data = {
            "token": token_hash,
            "action_type": "campaign_launch",
            "payload": {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "requester_user_id": user_id,
                "requested_action": "Approve campaign for launch",
            },
            "status": "PENDING",
            "expires_at": expires_at,
        }

        response = await execute_async(
            client.table("approval_requests").insert(data)
        )
        if response.data:
            record = response.data[0]
            return {
                "id": record["id"],
                "link": f"/approval/{token}",
                "expires_at": expires_at,
            }
        raise Exception("Failed to create approval request")

    async def _close_current_phase(self, campaign_id: str, client) -> None:
        """Close the most recent open phase (set exited_at)."""
        await execute_async(
            client.table("campaign_phases")
            .update({"exited_at": datetime.now(timezone.utc).isoformat()})
            .eq("campaign_id", campaign_id)
            .is_("exited_at", "null")
        )

    async def _record_phase(
        self,
        campaign_id: str,
        phase: str,
        notes: str = None,
        approval_request_id: str = None,
        metadata: dict = None,
        user_id: str = None,
        client=None,
    ) -> dict:
        """Insert a new campaign_phases record."""
        data = {
            "campaign_id": campaign_id,
            "user_id": user_id,
            "phase": phase,
            "notes": notes,
            "approval_request_id": approval_request_id,
            "metadata": metadata or {},
        }
        data = {k: v for k, v in data.items() if v is not None}

        response = await execute_async(
            client.table("campaign_phases").insert(data)
        )
        if response.data:
            return response.data[0]
        raise Exception("Failed to record phase transition")
