# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Email Sequence Service - Multi-step drip campaign engine.

Provides the complete email sequence lifecycle: CRUD, enrollment, template
rendering, delivery tick, daily send limits, bounce protection, and
open/click tracking.  Integrates with the Resend API for actual email
delivery and Redis for daily send limit counters.

Tables used (created by 20260404800000_crm_email_automation.sql):
- email_sequences
- email_sequence_steps
- email_sequence_enrollments
- email_tracking_events
- integration_sync_state (warm-up date tracking)
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

import jinja2

from app.services.base_service import AdminService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Sequence status transitions
VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["active"],
    "active": ["paused", "completed"],
    "paused": ["active", "completed"],
    "completed": [],
}

# Base URL for tracking pixel and click redirect URLs
_BASE_URL = os.environ.get("PIKAR_BASE_URL", "https://app.pikar.ai")

# Warm-up schedule: days since first send -> daily max sends
_WARMUP_SCHEDULE: list[tuple[int, int]] = [
    (7, 50),     # Week 1: 50/day
    (14, 100),   # Week 2: 100/day
    (21, 250),   # Week 3: 250/day
]
_WARMUP_DEFAULT = 500  # Week 4+: 500/day

# Bounce rate threshold
_BOUNCE_RATE_THRESHOLD = 0.05
_BOUNCE_MINIMUM_SENDS = 20

# 1x1 transparent PNG (43 bytes)
TRANSPARENT_PIXEL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Jinja2 environment for template rendering
_JINJA_ENV = jinja2.Environment(undefined=jinja2.Undefined)


class EmailSequenceService:
    """Complete email sequence engine.

    Uses AdminService (service role) for all database operations since
    the delivery tick runs without user context.
    """

    def __init__(self) -> None:
        self._admin = AdminService()

    # =====================================================================
    # CRUD
    # =====================================================================

    async def create_sequence(
        self,
        user_id: str,
        name: str,
        steps: list[dict],
        campaign_id: str | None = None,
    ) -> dict:
        """Create an email sequence with its steps in a single transaction.

        Args:
            user_id: Owner user ID.
            name: Sequence name.
            steps: List of step dicts with subject_template, body_template,
                   delay_hours, and optional delay_type.
            campaign_id: Optional linked campaign ID.

        Returns:
            Created sequence dict with nested steps.
        """
        client = self._admin.client

        # Create sequence record
        seq_data: dict = {
            "user_id": user_id,
            "name": name,
            "status": "draft",
        }
        if campaign_id:
            seq_data["campaign_id"] = campaign_id

        result = await execute_async(
            client.table("email_sequences").insert(seq_data),
            op_name="email_sequence.create",
        )
        sequence = result.data[0]
        sequence_id = sequence["id"]

        # Create steps
        step_records = []
        for idx, step in enumerate(steps):
            step_records.append({
                "sequence_id": sequence_id,
                "step_number": idx,
                "subject_template": step["subject_template"],
                "body_template": step["body_template"],
                "delay_hours": step.get("delay_hours", 0),
                "delay_type": step.get("delay_type", "after_previous"),
            })

        if step_records:
            steps_result = await execute_async(
                client.table("email_sequence_steps").insert(step_records),
                op_name="email_sequence.create_steps",
            )
            sequence["steps"] = steps_result.data
        else:
            sequence["steps"] = []

        logger.info(
            "Created email sequence %s with %d steps for user %s",
            sequence_id,
            len(step_records),
            user_id,
        )
        return sequence

    async def get_sequence(
        self, user_id: str, sequence_id: str
    ) -> dict | None:
        """Fetch a sequence with its steps and enrollment statistics.

        Args:
            user_id: Owner user ID (for scoping).
            sequence_id: Sequence UUID.

        Returns:
            Sequence dict with steps and enrollment stats, or None.
        """
        client = self._admin.client

        result = await execute_async(
            client.table("email_sequences")
            .select("*")
            .eq("id", sequence_id)
            .eq("user_id", user_id)
            .limit(1),
            op_name="email_sequence.get",
        )
        if not result.data:
            return None

        sequence = result.data[0]

        # Fetch steps
        steps_result = await execute_async(
            client.table("email_sequence_steps")
            .select("*")
            .eq("sequence_id", sequence_id)
            .order("step_number"),
            op_name="email_sequence.get_steps",
        )
        sequence["steps"] = steps_result.data or []

        # Fetch enrollment stats
        enrollments_result = await execute_async(
            client.table("email_sequence_enrollments")
            .select("status")
            .eq("sequence_id", sequence_id),
            op_name="email_sequence.get_enrollment_stats",
        )
        enrollments = enrollments_result.data or []
        sequence["enrollment_stats"] = {
            "active": sum(1 for e in enrollments if e["status"] == "active"),
            "completed": sum(
                1 for e in enrollments if e["status"] == "completed"
            ),
            "total": len(enrollments),
        }

        return sequence

    async def list_sequences(self, user_id: str) -> list[dict]:
        """List all sequences for a user with status and enrollment counts.

        Args:
            user_id: Owner user ID.

        Returns:
            List of sequence dicts with enrollment_count.
        """
        client = self._admin.client

        result = await execute_async(
            client.table("email_sequences")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True),
            op_name="email_sequence.list",
        )
        sequences = result.data or []

        # Attach enrollment counts
        for seq in sequences:
            enrollments_result = await execute_async(
                client.table("email_sequence_enrollments")
                .select("id", count="exact")
                .eq("sequence_id", seq["id"]),
                op_name="email_sequence.list_enrollment_count",
            )
            seq["enrollment_count"] = enrollments_result.count or 0

        return sequences

    async def update_sequence_status(
        self, user_id: str, sequence_id: str, status: str
    ) -> dict:
        """Update a sequence's status with transition validation.

        Valid transitions:
        - draft -> active
        - active -> paused, completed
        - paused -> active, completed

        Args:
            user_id: Owner user ID.
            sequence_id: Sequence UUID.
            status: Target status.

        Returns:
            Updated sequence dict.

        Raises:
            ValueError: If the transition is not allowed.
        """
        client = self._admin.client

        # Get current status
        result = await execute_async(
            client.table("email_sequences")
            .select("status")
            .eq("id", sequence_id)
            .eq("user_id", user_id)
            .limit(1),
            op_name="email_sequence.get_status",
        )
        if not result.data:
            msg = f"Sequence {sequence_id} not found"
            raise ValueError(msg)

        current_status = result.data[0]["status"]
        allowed = VALID_STATUS_TRANSITIONS.get(current_status, [])
        if status not in allowed:
            msg = (
                f"Cannot transition from '{current_status}' to '{status}'. "
                f"Allowed: {allowed}"
            )
            raise ValueError(msg)

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        update_result = await execute_async(
            client.table("email_sequences")
            .update({"status": status, "updated_at": now_iso})
            .eq("id", sequence_id)
            .eq("user_id", user_id),
            op_name="email_sequence.update_status",
        )

        logger.info(
            "Sequence %s transitioned: %s -> %s",
            sequence_id,
            current_status,
            status,
        )
        return update_result.data[0]

    async def delete_sequence(self, user_id: str, sequence_id: str) -> bool:
        """Delete a sequence and all related data (CASCADE).

        Args:
            user_id: Owner user ID.
            sequence_id: Sequence UUID.

        Returns:
            True if deleted.
        """
        client = self._admin.client

        result = await execute_async(
            client.table("email_sequences")
            .delete()
            .eq("id", sequence_id)
            .eq("user_id", user_id),
            op_name="email_sequence.delete",
        )

        deleted = bool(result.data)
        if deleted:
            logger.info("Deleted email sequence %s", sequence_id)
        return deleted

    # =====================================================================
    # Enrollment
    # =====================================================================

    async def enroll_contacts(
        self,
        user_id: str,
        sequence_id: str,
        contact_ids: list[str],
        timezone_str: str = "UTC",
    ) -> dict:
        """Enroll contacts in a sequence with timezone-aware scheduling.

        Skips contacts that are already enrolled (active status) or
        have unsubscribed.

        Args:
            user_id: Owner user ID.
            sequence_id: Sequence UUID.
            contact_ids: List of contact UUIDs to enroll.
            timezone_str: IANA timezone string (e.g. "America/New_York").

        Returns:
            Dict with enrolled and skipped counts.
        """
        client = self._admin.client

        # Verify sequence exists and is active
        seq_result = await execute_async(
            client.table("email_sequences")
            .select("id, status")
            .eq("id", sequence_id)
            .eq("user_id", user_id)
            .limit(1),
            op_name="email_sequence.enroll_verify",
        )
        if not seq_result.data:
            msg = f"Sequence {sequence_id} not found"
            raise ValueError(msg)
        if seq_result.data[0]["status"] != "active":
            msg = f"Sequence {sequence_id} is not active"
            raise ValueError(msg)

        # Get first step delay
        steps_result = await execute_async(
            client.table("email_sequence_steps")
            .select("delay_hours")
            .eq("sequence_id", sequence_id)
            .eq("step_number", 0)
            .limit(1),
            op_name="email_sequence.enroll_get_step0",
        )
        delay_hours = 0
        if steps_result.data:
            delay_hours = steps_result.data[0].get("delay_hours", 0)

        # Check existing enrollments
        existing_result = await execute_async(
            client.table("email_sequence_enrollments")
            .select("contact_id, status")
            .eq("sequence_id", sequence_id)
            .in_("contact_id", contact_ids),
            op_name="email_sequence.enroll_check_existing",
        )
        existing = {
            row["contact_id"]: row["status"]
            for row in (existing_result.data or [])
        }

        # Check unsubscribed contacts
        contacts_result = await execute_async(
            client.table("contacts")
            .select("id, metadata")
            .in_("id", contact_ids),
            op_name="email_sequence.enroll_check_contacts",
        )
        unsubscribed_ids = set()
        for contact in contacts_result.data or []:
            meta = contact.get("metadata") or {}
            if meta.get("unsubscribed"):
                unsubscribed_ids.add(contact["id"])

        # Compute next_send_at in UTC
        now = datetime.now(tz=timezone.utc)
        next_send_at = now + timedelta(hours=delay_hours)

        enrolled = 0
        skipped = 0
        records = []

        for cid in contact_ids:
            if cid in unsubscribed_ids:
                skipped += 1
                continue
            if cid in existing and existing[cid] in ("active", "completed"):
                skipped += 1
                continue

            records.append({
                "sequence_id": sequence_id,
                "contact_id": cid,
                "current_step": 0,
                "status": "active",
                "next_send_at": next_send_at.isoformat(),
                "timezone": timezone_str,
            })

        if records:
            await execute_async(
                client.table("email_sequence_enrollments").insert(records),
                op_name="email_sequence.enroll_insert",
            )
            enrolled = len(records)

        skipped += len(contact_ids) - enrolled - skipped

        logger.info(
            "Enrolled %d contacts in sequence %s (skipped %d)",
            enrolled,
            sequence_id,
            skipped,
        )
        return {"enrolled": enrolled, "skipped": skipped}

    async def unenroll_contact(
        self, user_id: str, enrollment_id: str
    ) -> dict:
        """Unenroll a contact by setting enrollment status to paused.

        Args:
            user_id: Owner user ID (for scoping via sequence).
            enrollment_id: Enrollment UUID.

        Returns:
            Updated enrollment dict.
        """
        client = self._admin.client

        result = await execute_async(
            client.table("email_sequence_enrollments")
            .update({"status": "paused"})
            .eq("id", enrollment_id),
            op_name="email_sequence.unenroll",
        )

        if result.data:
            logger.info("Unenrolled enrollment %s", enrollment_id)
            return result.data[0]

        msg = f"Enrollment {enrollment_id} not found"
        raise ValueError(msg)

    # =====================================================================
    # Template Rendering
    # =====================================================================

    @staticmethod
    def _render_template(template: str, context: dict) -> str:
        """Render a Jinja2 template string with contact context.

        Uses jinja2.Undefined so missing variables render as empty
        string rather than raising an error.

        Args:
            template: Jinja2 template string.
            context: Template context dict (first_name, company, etc.).

        Returns:
            Rendered string.
        """
        try:
            tpl = _JINJA_ENV.from_string(template)
            return tpl.render(context)
        except jinja2.TemplateSyntaxError:
            logger.warning("Template syntax error, returning raw template")
            return template

    # =====================================================================
    # Tracking Helpers
    # =====================================================================

    @staticmethod
    def _inject_tracking_pixel(
        html_content: str, tracking_id: str, base_url: str
    ) -> str:
        """Inject a 1x1 transparent tracking pixel before </body>.

        Args:
            html_content: Email HTML body.
            tracking_id: Format: {enrollment_id}_{step_number}.
            base_url: Base URL for the tracking endpoint.

        Returns:
            HTML with tracking pixel injected.
        """
        pixel_tag = (
            f'<img src="{base_url}/tracking/open/{tracking_id}" '
            f'width="1" height="1" alt="" style="display:none" />'
        )
        if "</body>" in html_content.lower():
            # Insert before closing body tag
            idx = html_content.lower().rfind("</body>")
            return html_content[:idx] + pixel_tag + html_content[idx:]
        return html_content + pixel_tag

    @staticmethod
    def _wrap_links(
        html_content: str, tracking_id: str, base_url: str
    ) -> str:
        """Replace href URLs with tracking redirect URLs.

        Skips unsubscribe links to ensure they always work directly.

        Args:
            html_content: Email HTML body.
            tracking_id: Format: {enrollment_id}_{step_number}.
            base_url: Base URL for the tracking endpoint.

        Returns:
            HTML with links wrapped for click tracking.
        """
        def _replace_href(match: re.Match) -> str:
            url = match.group(1)
            # Skip unsubscribe links and mailto links
            if "unsubscribe" in url.lower() or url.startswith("mailto:"):
                return match.group(0)
            tracking_url = (
                f"{base_url}/tracking/click/{tracking_id}"
                f"?url={url}"
            )
            return f'href="{tracking_url}"'

        return re.sub(r'href="(https?://[^"]+)"', _replace_href, html_content)

    @staticmethod
    def _add_unsubscribe_footer(
        html_content: str, enrollment_id: str, base_url: str
    ) -> str:
        """Add an unsubscribe link footer to the email HTML.

        Args:
            html_content: Email HTML body.
            enrollment_id: Enrollment UUID for the unsubscribe endpoint.
            base_url: Base URL for the unsubscribe endpoint.

        Returns:
            HTML with unsubscribe footer added.
        """
        unsub_url = f"{base_url}/unsubscribe/{enrollment_id}"
        footer = (
            '<div style="margin-top:32px;padding-top:16px;'
            "border-top:1px solid #e2e8f0;text-align:center;"
            'font-size:12px;color:#94a3b8;">'
            f'<a href="{unsub_url}" style="color:#94a3b8;">'
            "Unsubscribe from this email sequence</a></div>"
        )

        if "</body>" in html_content.lower():
            idx = html_content.lower().rfind("</body>")
            return html_content[:idx] + footer + html_content[idx:]
        return html_content + footer

    # =====================================================================
    # Bounce Protection
    # =====================================================================

    async def _check_bounce_rate(self, user_id: str) -> float:
        """Check the bounce rate over a rolling 24-hour window.

        If the rate exceeds 5% with at least 20 total sends, auto-pauses
        all active sequences for the user.

        Args:
            user_id: User ID to check.

        Returns:
            Bounce rate as a float (0.0 to 1.0).
        """
        client = self._admin.client
        cutoff = (
            datetime.now(tz=timezone.utc) - timedelta(hours=24)
        ).isoformat()

        # Count total sends and bounces in last 24h
        events_result = await execute_async(
            client.table("email_tracking_events")
            .select("event_type, enrollment_id")
            .in_("event_type", ["delivered", "bounced"])
            .gte("created_at", cutoff),
            op_name="email_sequence.check_bounce_rate",
        )
        events = events_result.data or []

        # Filter by user's enrollments
        # First get user's sequence IDs
        seq_result = await execute_async(
            client.table("email_sequences")
            .select("id")
            .eq("user_id", user_id),
            op_name="email_sequence.bounce_get_sequences",
        )
        user_seq_ids = {s["id"] for s in (seq_result.data or [])}

        if not user_seq_ids:
            return 0.0

        # Get enrollment IDs for user's sequences
        enroll_result = await execute_async(
            client.table("email_sequence_enrollments")
            .select("id, sequence_id")
            .in_("sequence_id", list(user_seq_ids)),
            op_name="email_sequence.bounce_get_enrollments",
        )
        user_enrollment_ids = {
            e["id"] for e in (enroll_result.data or [])
        }

        # Filter events to user's enrollments
        total_sends = 0
        bounces = 0
        for event in events:
            if event["enrollment_id"] in user_enrollment_ids:
                total_sends += 1
                if event["event_type"] == "bounced":
                    bounces += 1

        if total_sends < _BOUNCE_MINIMUM_SENDS:
            return 0.0

        rate = bounces / total_sends

        if rate > _BOUNCE_RATE_THRESHOLD:
            logger.warning(
                "Bounce rate %.1f%% exceeds threshold for user %s "
                "(%d bounces / %d sends). Auto-pausing all sequences.",
                rate * 100,
                user_id,
                bounces,
                total_sends,
            )
            # Auto-pause all active sequences
            pause_ts = datetime.now(tz=timezone.utc).isoformat()
            await execute_async(
                client.table("email_sequences")
                .update({"status": "paused", "updated_at": pause_ts})
                .eq("user_id", user_id)
                .eq("status", "active"),
                op_name="email_sequence.bounce_auto_pause",
            )

        return rate

    async def handle_bounce_event(
        self, enrollment_id: str, step_number: int
    ) -> None:
        """Record a bounce tracking event and update enrollment status.

        Args:
            enrollment_id: Enrollment UUID.
            step_number: Step that bounced.
        """
        client = self._admin.client

        # Record tracking event
        await execute_async(
            client.table("email_tracking_events").insert({
                "enrollment_id": enrollment_id,
                "step_number": step_number,
                "event_type": "bounced",
                "metadata": {},
            }),
            op_name="email_sequence.record_bounce",
        )

        # Update enrollment status
        await execute_async(
            client.table("email_sequence_enrollments")
            .update({"status": "bounced"})
            .eq("id", enrollment_id),
            op_name="email_sequence.bounce_enrollment",
        )

        logger.info(
            "Bounce recorded for enrollment %s step %d",
            enrollment_id,
            step_number,
        )

    async def handle_unsubscribe(self, enrollment_id: str) -> None:
        """Handle an unsubscribe request for an enrollment.

        Sets the enrollment status to 'unsubscribed' and marks the
        contact as unsubscribed in their metadata.

        Args:
            enrollment_id: Enrollment UUID.
        """
        client = self._admin.client

        # Get enrollment details
        enroll_result = await execute_async(
            client.table("email_sequence_enrollments")
            .select("contact_id, current_step")
            .eq("id", enrollment_id)
            .limit(1),
            op_name="email_sequence.unsub_get_enrollment",
        )
        if not enroll_result.data:
            logger.warning("Unsubscribe: enrollment %s not found", enrollment_id)
            return

        contact_id = enroll_result.data[0]["contact_id"]
        step_number = enroll_result.data[0]["current_step"]

        # Record tracking event
        await execute_async(
            client.table("email_tracking_events").insert({
                "enrollment_id": enrollment_id,
                "step_number": step_number,
                "event_type": "unsubscribed",
                "metadata": {},
            }),
            op_name="email_sequence.record_unsub",
        )

        # Update enrollment status
        await execute_async(
            client.table("email_sequence_enrollments")
            .update({"status": "unsubscribed"})
            .eq("id", enrollment_id),
            op_name="email_sequence.unsub_enrollment",
        )

        # Mark contact as unsubscribed in metadata
        contact_result = await execute_async(
            client.table("contacts")
            .select("metadata")
            .eq("id", contact_id)
            .limit(1),
            op_name="email_sequence.unsub_get_contact",
        )
        if contact_result.data:
            metadata = contact_result.data[0].get("metadata") or {}
            metadata["unsubscribed"] = True
            metadata["unsubscribed_at"] = datetime.now(tz=timezone.utc).isoformat()
            await execute_async(
                client.table("contacts")
                .update({"metadata": metadata})
                .eq("id", contact_id),
                op_name="email_sequence.unsub_contact_metadata",
            )

        logger.info(
            "Unsubscribe processed for enrollment %s (contact %s)",
            enrollment_id,
            contact_id,
        )

    # =====================================================================
    # Performance Stats
    # =====================================================================

    async def get_sequence_performance(
        self, user_id: str, sequence_id: str
    ) -> dict:
        """Aggregate tracking events into performance metrics.

        Args:
            user_id: Owner user ID.
            sequence_id: Sequence UUID.

        Returns:
            Dict with open_rate, click_rate, bounce_rate, completion_rate.
        """
        client = self._admin.client

        # Verify ownership
        seq_result = await execute_async(
            client.table("email_sequences")
            .select("id")
            .eq("id", sequence_id)
            .eq("user_id", user_id)
            .limit(1),
            op_name="email_sequence.perf_verify",
        )
        if not seq_result.data:
            msg = f"Sequence {sequence_id} not found"
            raise ValueError(msg)

        # Get all enrollments for this sequence
        enroll_result = await execute_async(
            client.table("email_sequence_enrollments")
            .select("id, status")
            .eq("sequence_id", sequence_id),
            op_name="email_sequence.perf_enrollments",
        )
        enrollments = enroll_result.data or []
        total_enrollments = len(enrollments)

        if total_enrollments == 0:
            return {
                "total_enrollments": 0,
                "open_rate": 0.0,
                "click_rate": 0.0,
                "bounce_rate": 0.0,
                "completion_rate": 0.0,
            }

        enrollment_ids = [e["id"] for e in enrollments]
        completed = sum(1 for e in enrollments if e["status"] == "completed")

        # Get tracking events
        events_result = await execute_async(
            client.table("email_tracking_events")
            .select("event_type, enrollment_id")
            .in_("enrollment_id", enrollment_ids),
            op_name="email_sequence.perf_events",
        )
        events = events_result.data or []

        # Count unique enrollments per event type
        opens = len({e["enrollment_id"] for e in events if e["event_type"] == "open"})
        clicks = len({e["enrollment_id"] for e in events if e["event_type"] == "click"})
        bounces = len(
            {e["enrollment_id"] for e in events if e["event_type"] == "bounced"}
        )
        delivered = len(
            {e["enrollment_id"] for e in events if e["event_type"] == "delivered"}
        )

        # Rates based on delivered (or total if no delivered events yet)
        base = delivered or total_enrollments

        return {
            "total_enrollments": total_enrollments,
            "total_delivered": delivered,
            "total_opens": opens,
            "total_clicks": clicks,
            "total_bounces": bounces,
            "open_rate": round(opens / base, 4) if base else 0.0,
            "click_rate": round(clicks / base, 4) if base else 0.0,
            "bounce_rate": round(bounces / base, 4) if base else 0.0,
            "completion_rate": round(completed / total_enrollments, 4),
        }


# =========================================================================
# Daily Send Limit (Redis-based)
# =========================================================================


async def _get_redis_client():
    """Get the Redis client from the cache service.

    Returns:
        Redis client instance, or None if unavailable.
    """
    try:
        from app.services.cache import CacheService

        cache = CacheService()
        return await cache._ensure_connection()
    except Exception:
        logger.warning("Redis unavailable for daily send limit tracking")
        return None


async def _check_and_increment_daily_send(
    redis_client, user_id: str, max_sends: int
) -> bool:
    """Atomically check and increment the daily send counter.

    Uses Redis INCR on key ``pikar:email:daily:{user_id}:{date}``
    with a 90000s TTL (25 hours) on first use.

    Args:
        redis_client: Active Redis client.
        user_id: User ID for the counter.
        max_sends: Maximum sends allowed today.

    Returns:
        True if under limit (send allowed), False if limit reached.
    """
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    key = f"pikar:email:daily:{user_id}:{today}"

    count = await redis_client.incr(key)

    # Set TTL on first increment
    if count == 1:
        await redis_client.expire(key, 90000)

    if count > max_sends:
        # Over limit -- decrement back and return False
        await redis_client.decr(key)
        return False

    return True


async def _get_daily_send_limit(user_id: str) -> int:
    """Compute the warm-up daily send limit for a user.

    Based on days since first email send stored in
    integration_sync_state metadata for provider "email_sequences".

    Week 1: 50, Week 2: 100, Week 3: 250, Week 4+: 500.

    Args:
        user_id: User ID.

    Returns:
        Maximum daily sends allowed.
    """
    client = AdminService().client

    result = await execute_async(
        client.table("integration_sync_state")
        .select("metadata")
        .eq("user_id", user_id)
        .eq("provider", "email_sequences")
        .limit(1),
        op_name="email_sequence.get_warmup_date",
    )

    if not result.data:
        # First time -- create the record
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        await execute_async(
            client.table("integration_sync_state").upsert(
                {
                    "user_id": user_id,
                    "provider": "email_sequences",
                    "metadata": {"first_send_at": now_iso},
                    "status": "active",
                },
                on_conflict="user_id,provider",
            ),
            op_name="email_sequence.set_warmup_date",
        )
        return _WARMUP_SCHEDULE[0][1]  # Week 1 limit

    metadata = result.data[0].get("metadata") or {}
    first_send_str = metadata.get("first_send_at")
    if not first_send_str:
        return _WARMUP_SCHEDULE[0][1]

    try:
        first_send = datetime.fromisoformat(first_send_str)
    except (ValueError, TypeError):
        return _WARMUP_SCHEDULE[0][1]

    days_since = (datetime.now(tz=timezone.utc) - first_send).days

    for max_days, limit in _WARMUP_SCHEDULE:
        if days_since < max_days:
            return limit

    return _WARMUP_DEFAULT


# =========================================================================
# Delivery Tick (called by WorkflowWorker)
# =========================================================================


async def run_email_delivery_tick() -> list[dict]:
    """Process due email sequence enrollments.

    Called by WorkflowWorker every 60 seconds.  Queries active
    enrollments with next_send_at <= now(), processes up to 50 at a
    time, checks daily send limits and bounce rates, renders templates,
    sends via Resend with tracking injected, and advances enrollments.

    Returns:
        List of send result dicts.
    """
    service = EmailSequenceService()
    client = service._admin.client
    now = datetime.now(tz=timezone.utc)

    # Query due enrollments
    result = await execute_async(
        client.table("email_sequence_enrollments")
        .select("*, email_sequences!inner(user_id, status)")
        .eq("status", "active")
        .eq("email_sequences.status", "active")
        .lte("next_send_at", now.isoformat())
        .order("next_send_at")
        .limit(50),
        op_name="email_sequence.delivery_tick_query",
    )
    enrollments = result.data or []

    if not enrollments:
        return []

    logger.info("Email delivery tick: %d due enrollments", len(enrollments))

    # Get Redis client for daily send limits
    redis_client = await _get_redis_client()

    results = []
    # Track users whose bounce rate has been checked this tick
    checked_bounce_users: set[str] = set()

    for enrollment in enrollments:
        enrollment_id = enrollment["id"]
        sequence_id = enrollment["sequence_id"]
        contact_id = enrollment["contact_id"]
        current_step = enrollment["current_step"]
        user_id = enrollment["email_sequences"]["user_id"]

        try:
            # Check bounce rate (once per user per tick)
            if user_id not in checked_bounce_users:
                bounce_rate = await service._check_bounce_rate(user_id)
                checked_bounce_users.add(user_id)
                if bounce_rate > _BOUNCE_RATE_THRESHOLD:
                    logger.warning(
                        "User %s bounce rate %.1f%% exceeds threshold, skipping",
                        user_id,
                        bounce_rate * 100,
                    )
                    continue

            # Check daily send limit
            if redis_client:
                max_sends = await _get_daily_send_limit(user_id)
                allowed = await _check_and_increment_daily_send(
                    redis_client, user_id, max_sends
                )
                if not allowed:
                    logger.info(
                        "Daily send limit reached for user %s, skipping",
                        user_id,
                    )
                    continue

            # Load step template
            step_result = await execute_async(
                client.table("email_sequence_steps")
                .select("*")
                .eq("sequence_id", sequence_id)
                .eq("step_number", current_step)
                .limit(1),
                op_name="email_sequence.delivery_get_step",
            )
            if not step_result.data:
                logger.warning(
                    "Step %d not found for sequence %s",
                    current_step,
                    sequence_id,
                )
                continue

            step = step_result.data[0]

            # Load contact data for template rendering
            contact_result = await execute_async(
                client.table("contacts")
                .select("*")
                .eq("id", contact_id)
                .limit(1),
                op_name="email_sequence.delivery_get_contact",
            )
            if not contact_result.data:
                logger.warning("Contact %s not found, skipping", contact_id)
                continue

            contact = contact_result.data[0]
            metadata = contact.get("metadata") or {}

            # Build template context
            template_context = {
                "first_name": contact.get("first_name", ""),
                "last_name": contact.get("last_name", ""),
                "company": contact.get("company", ""),
                "email": contact.get("email", ""),
                "deal_name": metadata.get("deal_name", ""),
                **{k: v for k, v in metadata.items() if isinstance(v, str)},
            }

            # Render templates
            subject = service._render_template(
                step["subject_template"], template_context
            )
            body_html = service._render_template(
                step["body_template"], template_context
            )

            # Build tracking ID
            tracking_id = f"{enrollment_id}_{current_step}"

            # Add unsubscribe footer
            body_html = service._add_unsubscribe_footer(
                body_html, enrollment_id, _BASE_URL
            )

            # Inject tracking pixel
            body_html = service._inject_tracking_pixel(
                body_html, tracking_id, _BASE_URL
            )

            # Wrap links for click tracking
            body_html = service._wrap_links(
                body_html, tracking_id, _BASE_URL
            )

            # Build List-Unsubscribe headers (RFC 8058)
            unsub_url = f"{_BASE_URL}/unsubscribe/{enrollment_id}"
            custom_headers = {
                "List-Unsubscribe": f"<{unsub_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                "X-Pikar-Sequence-Id": sequence_id,
                "X-Pikar-Enrollment-Id": enrollment_id,
                "X-Pikar-Step": str(current_step),
            }

            # Send via Resend
            from app.mcp.integrations.email_service import EmailService

            email_service = EmailService()
            send_result = await email_service.send_email(
                to_emails=[contact["email"]],
                subject=subject,
                html_content=body_html,
            )

            # Record delivered event
            if send_result.get("success"):
                await execute_async(
                    client.table("email_tracking_events").insert({
                        "enrollment_id": enrollment_id,
                        "step_number": current_step,
                        "event_type": "delivered",
                        "metadata": {
                            "resend_id": send_result.get("id"),
                            "headers": custom_headers,
                        },
                    }),
                    op_name="email_sequence.delivery_record",
                )

                # Advance to next step
                next_step = current_step + 1

                # Check if there is a next step
                next_step_result = await execute_async(
                    client.table("email_sequence_steps")
                    .select("delay_hours")
                    .eq("sequence_id", sequence_id)
                    .eq("step_number", next_step)
                    .limit(1),
                    op_name="email_sequence.delivery_check_next",
                )

                if next_step_result.data:
                    # More steps -- advance
                    delay_hours = next_step_result.data[0].get("delay_hours", 24)
                    next_send_at = now + timedelta(hours=delay_hours)
                    await execute_async(
                        client.table("email_sequence_enrollments")
                        .update({
                            "current_step": next_step,
                            "next_send_at": next_send_at.isoformat(),
                        })
                        .eq("id", enrollment_id),
                        op_name="email_sequence.delivery_advance",
                    )
                else:
                    # No more steps -- complete
                    await execute_async(
                        client.table("email_sequence_enrollments")
                        .update({"status": "completed"})
                        .eq("id", enrollment_id),
                        op_name="email_sequence.delivery_complete",
                    )

                results.append({
                    "enrollment_id": enrollment_id,
                    "step": current_step,
                    "status": "sent",
                    "resend_id": send_result.get("id"),
                })
            else:
                logger.warning(
                    "Failed to send email for enrollment %s step %d: %s",
                    enrollment_id,
                    current_step,
                    send_result.get("error"),
                )
                results.append({
                    "enrollment_id": enrollment_id,
                    "step": current_step,
                    "status": "failed",
                    "error": send_result.get("error"),
                })

        except Exception:
            logger.exception(
                "Error processing enrollment %s", enrollment_id
            )
            results.append({
                "enrollment_id": enrollment_id,
                "step": current_step,
                "status": "error",
            })

    return results
