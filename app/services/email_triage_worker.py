# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Background email triage worker.

Runs on a Cloud Scheduler tick to fetch, classify, and optionally
auto-act on unread emails for all opted-in users.
"""

import logging
from datetime import date
from typing import Any

from app.integrations.google.client import get_user_gmail_credentials
from app.integrations.google.gmail_reader import GmailReader
from app.notifications.notification_service import NotificationService, NotificationType
from app.services.email_triage_service import EmailTriageService
from supabase import Client

logger = logging.getLogger(__name__)

_MAX_EMAILS_PER_RUN = 50


class EmailTriageWorker:
    """Background worker that triages unread emails for all enabled users.

    Fetches user preferences from ``user_briefing_preferences``, retrieves
    unread Gmail messages via the stored OAuth refresh token, classifies each
    email with :class:`EmailTriageService`, optionally generates draft replies,
    and persists results.  Auto-act is guarded by a shadow-mode check so that
    users who have not explicitly enabled ``auto_act_enabled`` only see what
    *would* have happened.
    """

    def __init__(self, supabase_client: Client) -> None:
        """Initialise the worker.

        Args:
            supabase_client: Authenticated Supabase service-role client.
        """
        self._db = supabase_client
        self.triage_service = EmailTriageService(supabase_client=supabase_client)

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def run(self) -> dict[str, Any]:
        """Fetch all triage-enabled users and process each one.

        Returns:
            Summary dict with total counts and per-user results.
        """
        try:
            response = (
                self._db.table("user_briefing_preferences")
                .select("user_id, preferences")
                .eq("email_triage_enabled", True)
                .execute()
            )
            users = response.data or []
        except Exception as exc:
            logger.error("Failed to fetch triage-enabled users: %s", exc)
            users = []

        results = await self.process_all_users(users)

        total_processed = sum(r.get("processed", 0) for r in results)
        total_auto_acted = sum(r.get("auto_acted", 0) for r in results)

        logger.info(
            "Email triage run complete: %d users, %d emails processed, %d auto-acted",
            len(results),
            total_processed,
            total_auto_acted,
        )

        return {
            "status": "complete",
            "users": len(results),
            "emails_processed": total_processed,
            "auto_acted": total_auto_acted,
            "results": results,
        }

    async def process_all_users(self, users: list[dict]) -> list[dict[str, Any]]:
        """Process each user independently, isolating per-user failures.

        Args:
            users: List of dicts with ``user_id`` and ``preferences`` keys.

        Returns:
            List of per-user result dicts.
        """
        results: list[dict[str, Any]] = []
        for row in users:
            user_id = row.get("user_id", "")
            prefs = row.get("preferences") or {}
            try:
                result = await self.process_user(user_id, prefs)
            except Exception as exc:
                logger.error("Triage failed for user %s: %s", user_id, exc)
                result = {"status": "error", "user_id": user_id, "error": str(exc)}
            results.append(result)
        return results

    async def process_user(self, user_id: str, prefs: dict) -> dict[str, Any]:
        """Run the full triage pipeline for a single user.

        Steps:
        1. Resolve OAuth refresh token.
        2. Build GmailReader with background credentials.
        3. Fetch up to 50 unread messages.
        4. De-duplicate against already-triaged message IDs.
        5. Classify each new email; generate draft if ``needs_reply``.
        6. Apply shadow-mode / live-mode auto-act logic.
        7. Persist triage result; send urgent notification when warranted.

        Args:
            user_id: Supabase user ID.
            prefs: User preference dict (from ``user_briefing_preferences``).

        Returns:
            Summary dict for this user.
        """
        if not await self._try_acquire_lock(user_id):
            return {
                "status": "skipped",
                "user_id": user_id,
                "reason": "lock_held_by_another_instance",
            }

        try:
            return await self._process_user_locked(user_id, prefs)
        finally:
            await self._release_lock(user_id)

    async def _process_user_locked(self, user_id: str, prefs: dict) -> dict:
        """Execute the triage pipeline after the distributed lock has been acquired.

        This is the inner implementation called by :meth:`process_user` once
        the per-user Redis lock is held.  The split keeps locking concerns
        separate from processing logic.

        Args:
            user_id: Supabase user ID.
            prefs: User preference dict (from ``user_briefing_preferences``).

        Returns:
            Summary dict for this user.
        """
        refresh_token = await self._get_user_refresh_token(user_id)
        if not refresh_token:
            logger.info("No refresh token for user %s — skipping", user_id)
            return {
                "status": "skipped",
                "user_id": user_id,
                "reason": "no_refresh_token",
            }

        try:
            credentials = get_user_gmail_credentials(refresh_token)
            reader = GmailReader(credentials)
        except ValueError as exc:
            logger.warning(
                "Cannot build Gmail credentials for user %s: %s", user_id, exc
            )
            return {"status": "skipped", "user_id": user_id, "reason": str(exc)}

        # Fetch unread emails
        list_result = reader.list_messages(
            query="is:unread", max_results=_MAX_EMAILS_PER_RUN
        )
        if list_result.get("status") != "success":
            logger.warning(
                "Gmail list failed for user %s: %s", user_id, list_result.get("error")
            )
            return {
                "status": "error",
                "user_id": user_id,
                "error": list_result.get("error"),
            }

        messages = list_result.get("messages", [])
        if not messages:
            return {"status": "ok", "user_id": user_id, "processed": 0, "auto_acted": 0}

        existing_ids = await self._get_existing_message_ids(user_id)
        auto_acted_today = await self._get_auto_act_count_today(user_id)

        processed = 0
        auto_acted = 0

        for msg_stub in messages:
            msg_id = msg_stub.get("id")
            if msg_id in existing_ids:
                continue

            msg_result = reader.get_message(msg_id)
            if msg_result.get("status") != "success":
                logger.debug("Failed to fetch message %s for user %s", msg_id, user_id)
                continue

            msg = msg_result["message"]
            # Normalise key used downstream
            msg.setdefault("gmail_message_id", msg.get("id", msg_id))

            try:
                classification = await self.triage_service.classify_email(msg, prefs)
            except Exception as exc:
                logger.warning("Classification failed for msg %s: %s", msg_id, exc)
                continue

            draft: str | None = None
            if classification.get("action_type") == "needs_reply":
                try:
                    draft_result = await self.triage_service.generate_draft(msg)
                    draft = draft_result.get("draft")
                except Exception as exc:
                    logger.warning(
                        "Draft generation failed for msg %s: %s", msg_id, exc
                    )

            auto_action: str | None = None
            status = "pending"

            if (
                classification.get("action_type") == "auto_handle"
                and classification.get("confidence", 0.0) >= 0.85
            ):
                if not prefs.get("auto_act_enabled", False):
                    # Shadow mode: record what *would* happen but do not act
                    category = classification.get("category", "unknown")
                    auto_action = f"shadow: would auto-handle as {category}"
                elif self.triage_service.should_auto_act(
                    action_type=classification["action_type"],
                    confidence=classification["confidence"],
                    prefs=prefs,
                    auto_acted_today=auto_acted_today,
                ):
                    # Live mode: execute the action
                    auto_action = await self._execute_auto_action(
                        reader, msg, classification
                    )
                    status = "auto_handled"
                    auto_acted_today += 1
                    auto_acted += 1

            await self.triage_service.store_triage_result(
                user_id=user_id,
                email=msg,
                classification=classification,
                draft=draft,
                status=status,
                auto_action=auto_action,
            )

            if classification.get("priority") == "urgent":
                await self._send_urgent_notification(user_id, msg)

            processed += 1
            existing_ids.add(msg_id)

        return {
            "status": "ok",
            "user_id": user_id,
            "processed": processed,
            "auto_acted": auto_acted,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _try_acquire_lock(self, user_id: str) -> bool:
        """Try to acquire a Redis lock for this user's email processing.

        Uses SET NX (only-if-not-exists) with a 5-minute TTL so the lock
        automatically expires if the worker crashes mid-run.  If Redis is
        unavailable the method returns ``True`` to allow processing (graceful
        degradation), accepting the small risk of duplicate work over the
        larger risk of silently skipping all email triage.

        Args:
            user_id: Supabase user ID used as the lock key discriminator.

        Returns:
            ``True`` if the lock was acquired (or Redis is down), ``False``
            if another instance already holds the lock for this user.
        """
        try:
            from app.services.cache import CacheService

            cache = CacheService()
            lock_key = f"email_triage:lock:{user_id}"
            result = await cache.set_nx(lock_key, "processing", ttl=300)
            if not result:
                logger.info(
                    "Email triage lock already held for user %s — skipping",
                    user_id,
                )
            return result
        except Exception:
            # If Redis is down, allow processing (graceful degradation)
            return True

    async def _release_lock(self, user_id: str) -> None:
        """Release the distributed processing lock for a user.

        The lock will expire via TTL regardless, so failures here are
        non-critical.

        Args:
            user_id: Supabase user ID whose lock should be released.
        """
        try:
            from app.services.cache import CacheService

            cache = CacheService()
            await cache.delete(f"email_triage:lock:{user_id}")
        except Exception:
            pass  # Lock will expire via TTL

    async def _get_user_refresh_token(self, user_id: str) -> str | None:
        """Resolve the Google OAuth refresh token for a user.

        Tries the ``get_user_provider_refresh_token`` RPC first; falls back to
        querying the Supabase admin ``auth.users`` table.

        Args:
            user_id: Supabase user ID.

        Returns:
            Refresh token string, or ``None`` if unavailable.
        """
        try:
            rpc_response = self._db.rpc(
                "get_user_provider_refresh_token",
                {"p_user_id": user_id},
            ).execute()
            token = rpc_response.data
            if isinstance(token, str) and token:
                return token
            if isinstance(token, list) and token:
                return token[0] if isinstance(token[0], str) else None
        except Exception as exc:
            logger.debug(
                "RPC get_user_provider_refresh_token failed for %s: %s", user_id, exc
            )

        # Fallback: query admin table directly
        try:
            response = (
                self._db.table("user_oauth_tokens")
                .select("refresh_token")
                .eq("user_id", user_id)
                .eq("provider", "google")
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0].get("refresh_token")
        except Exception as exc:
            logger.debug("Admin token fallback failed for %s: %s", user_id, exc)

        return None

    async def _get_existing_message_ids(self, user_id: str) -> set[str]:
        """Return the set of Gmail message IDs already in ``email_triage``.

        Args:
            user_id: Supabase user ID.

        Returns:
            Set of already-triaged ``gmail_message_id`` strings.
        """
        try:
            response = (
                self._db.table("email_triage")
                .select("gmail_message_id")
                .eq("user_id", user_id)
                .execute()
            )
            return {
                row["gmail_message_id"]
                for row in (response.data or [])
                if row.get("gmail_message_id")
            }
        except Exception as exc:
            logger.warning(
                "Failed to fetch existing message IDs for %s: %s", user_id, exc
            )
            return set()

    async def _get_auto_act_count_today(self, user_id: str) -> int:
        """Count emails auto-handled today for rate-limiting.

        Args:
            user_id: Supabase user ID.

        Returns:
            Number of emails auto-acted on since midnight UTC today.
        """
        today_str = date.today().isoformat()
        try:
            response = (
                self._db.table("email_triage")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("status", "auto_handled")
                .gte("created_at", f"{today_str}T00:00:00")
                .execute()
            )
            return response.count or 0
        except Exception as exc:
            logger.warning("Failed to fetch auto-act count for %s: %s", user_id, exc)
            return 0

    async def _execute_auto_action(
        self,
        reader: GmailReader,
        email: dict,
        classification: dict,
    ) -> str:
        """Execute the appropriate Gmail action based on email category.

        Currently:
        - ``newsletter`` → archive (remove INBOX) and mark as read.
        - ``notification`` → mark as read only.
        - Anything else → archive.

        Args:
            reader: Authenticated GmailReader for the user.
            email: Parsed email dict.
            classification: Classification result dict.

        Returns:
            Human-readable description of the action taken.
        """
        category = classification.get("category", "")
        msg_id = email.get("gmail_message_id") or email.get("id", "")

        if category == "newsletter":
            reader.modify_message(
                msg_id,
                add_labels=[],
                remove_labels=["INBOX", "UNREAD"],
            )
            return "archived_newsletter"

        if category == "notification":
            reader.modify_message(
                msg_id,
                add_labels=[],
                remove_labels=["UNREAD"],
            )
            return "marked_read_notification"

        # Default: archive
        reader.modify_message(
            msg_id,
            add_labels=[],
            remove_labels=["INBOX"],
        )
        return f"archived_{category or 'unknown'}"

    async def _send_urgent_notification(self, user_id: str, email: dict) -> None:
        """Send an in-app notification for an urgent email.

        Args:
            user_id: Supabase user ID to notify.
            email: Parsed email dict.
        """
        try:
            notification_service = NotificationService()
            subject = email.get("subject", "(no subject)")
            sender = email.get("sender_name") or email.get("sender", "Unknown")
            await notification_service.create_notification(
                user_id=user_id,
                title="Urgent email received",
                message=f"From {sender}: {subject}",
                type=NotificationType.WARNING,
                metadata={
                    "gmail_message_id": email.get("gmail_message_id"),
                    "sender": email.get("sender"),
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to send urgent notification for user %s: %s", user_id, exc
            )
