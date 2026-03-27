# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Email triage service for AI classification and draft generation.

Classifies emails by priority/action/category using Gemini,
generates draft replies, and enforces auto-act safety guardrails.
"""

import json
import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

VALID_PRIORITIES = {"urgent", "important", "normal", "low"}
VALID_ACTIONS = {"needs_reply", "needs_review", "fyi", "auto_handle", "spam"}
VALID_CATEGORIES = {
    "meeting",
    "deal",
    "task",
    "report",
    "personal",
    "newsletter",
    "notification",
}


class EmailTriageService:
    """Service for AI-powered email triage: classification, drafts, and auto-act safety."""

    def __init__(self, supabase_client: Client) -> None:
        """Initialize the email triage service.

        Args:
            supabase_client: Authenticated Supabase client instance.
        """
        self._db = supabase_client

    async def classify_email(self, email: dict, prefs: dict) -> dict:
        """Classify an email by priority, action type, and category.

        Calls the AI classifier, then validates and sanitizes the result.
        Falls back to safe defaults for any invalid or missing values.

        Args:
            email: Email data including sender, subject, and body.
            prefs: User preferences including vip_senders and ignored_senders.

        Returns:
            Dict with priority, action_type, category, confidence, and reasoning.
        """
        raw = await self._call_classifier(email, prefs)

        priority = raw.get("priority")
        if priority not in VALID_PRIORITIES:
            logger.warning(
                "Invalid priority %r from classifier, defaulting to normal", priority
            )
            priority = "normal"

        action_type = raw.get("action_type")
        if action_type not in VALID_ACTIONS:
            logger.warning(
                "Invalid action_type %r from classifier, defaulting to needs_review",
                action_type,
            )
            action_type = "needs_review"

        category = raw.get("category")
        if category not in VALID_CATEGORIES:
            logger.warning(
                "Invalid category %r from classifier, defaulting to None", category
            )
            category = None

        confidence = raw.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        return {
            "priority": priority,
            "action_type": action_type,
            "category": category,
            "confidence": confidence,
            "reasoning": raw.get("reasoning"),
        }

    async def _call_classifier(self, email: dict, prefs: dict) -> dict:
        """Call Gemini to classify a single email.

        Args:
            email: Email data dict.
            prefs: User preferences dict.

        Returns:
            Raw dict parsed from the model response (may contain invalid values).
        """
        import google.generativeai as genai

        model = genai.GenerativeModel("gemini-2.5-flash")

        body_snippet = (email.get("body") or "")[:2000]
        vip_senders = prefs.get("vip_senders", [])
        ignored_senders = prefs.get("ignored_senders", [])

        prompt = f"""You are an executive email triage assistant. Classify the following email.

Email details:
- Sender: {email.get("sender", "")}
- Sender name: {email.get("sender_name", "")}
- Subject: {email.get("subject", "")}
- Body: {body_snippet}

User context:
- VIP senders: {vip_senders}
- Ignored senders: {ignored_senders}

Respond with ONLY valid JSON in this exact format:
{{
  "priority": "<urgent|important|normal|low>",
  "action_type": "<needs_reply|needs_review|fyi|auto_handle|spam>",
  "category": "<meeting|deal|task|report|personal|newsletter|notification>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<brief explanation>"
}}"""

        try:
            response = await model.generate_content_async(prompt)
            text = response.text.strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                lines = text.splitlines()
                lines = [ln for ln in lines if not ln.startswith("```")]
                text = "\n".join(lines).strip()

            return json.loads(text)
        except (json.JSONDecodeError, ValueError, AttributeError) as exc:
            logger.warning("Classifier JSON parse failure: %s", exc)
            return {
                "priority": "normal",
                "action_type": "needs_review",
                "category": None,
                "confidence": 0.3,
                "reasoning": "Parse failure — safe defaults applied",
            }
        except Exception as exc:
            logger.error("Classifier call failed: %s", exc)
            return {
                "priority": "normal",
                "action_type": "needs_review",
                "category": None,
                "confidence": 0.3,
                "reasoning": "API error — safe defaults applied",
            }

    async def generate_draft(self, email: dict) -> dict:
        """Generate a draft reply for an email.

        Args:
            email: Email data including sender, subject, and body.

        Returns:
            Dict with 'draft' (str or None) and 'confidence' (float).
        """
        result = await self._call_draft_generator(email)
        return {
            "draft": result.get("draft"),
            "confidence": result.get("confidence", 0.0),
        }

    async def _call_draft_generator(self, email: dict) -> dict:
        """Call Gemini to generate a draft reply for an email.

        Args:
            email: Email data dict.

        Returns:
            Dict with 'draft' and 'confidence' keys.
        """
        import google.generativeai as genai

        model = genai.GenerativeModel("gemini-2.5-flash")

        body_snippet = (email.get("body") or "")[:2000]

        prompt = f"""You are drafting a brief, professional reply on behalf of a busy executive.

Original email:
- From: {email.get("sender_name", "")} <{email.get("sender", "")}>
- Subject: {email.get("subject", "")}
- Body: {body_snippet}

Instructions:
- Write a concise, executive-style reply (2-4 sentences maximum)
- Be professional and courteous
- Never make commitments or promises on behalf of the executive
- Do not include a subject line — body only

Respond with ONLY valid JSON in this exact format:
{{
  "draft": "<the draft reply text>",
  "confidence": <float 0.0-1.0 indicating how appropriate this draft is>
}}"""

        try:
            response = await model.generate_content_async(prompt)
            text = response.text.strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                lines = text.splitlines()
                lines = [ln for ln in lines if not ln.startswith("```")]
                text = "\n".join(lines).strip()

            return json.loads(text)
        except (json.JSONDecodeError, ValueError, AttributeError) as exc:
            logger.warning("Draft generator JSON parse failure: %s", exc)
            return {"draft": None, "confidence": 0.0}
        except Exception as exc:
            logger.error("Draft generator call failed: %s", exc)
            return {"draft": None, "confidence": 0.0}

    def should_auto_act(
        self,
        action_type: str,
        confidence: float,
        prefs: dict,
        auto_acted_today: int,
    ) -> bool:
        """Determine whether an email qualifies for automatic action.

        All safety guardrails must pass:
        - auto_act_enabled pref must be True
        - action_type must be 'auto_handle'
        - confidence must be >= 0.85
        - auto_acted_today must be below the daily cap

        Args:
            action_type: The classified action type for this email.
            confidence: Classifier confidence score (0.0–1.0).
            prefs: User preferences dict.
            auto_acted_today: Number of emails auto-acted on today.

        Returns:
            True only if ALL safety guardrails pass, False otherwise.
        """
        if not prefs.get("auto_act_enabled", False):
            return False
        if action_type != "auto_handle":
            return False
        if confidence < 0.85:
            return False
        daily_cap = prefs.get("auto_act_daily_cap", 10)
        if auto_acted_today >= daily_cap:
            return False
        return True

    async def store_triage_result(
        self,
        user_id: str,
        email: dict,
        classification: dict,
        draft: Any = None,
        status: str = "pending",
        auto_action: Any = None,
    ) -> dict | None:
        """Persist a triage result to the email_triage table.

        Upserts on (user_id, gmail_message_id) to avoid duplicates.

        Args:
            user_id: The authenticated user's ID.
            email: Email data dict.
            classification: Classification result from classify_email.
            draft: Optional draft text string.
            status: Triage status (default 'pending').
            auto_action: Optional auto-action metadata.

        Returns:
            The inserted/updated row dict, or None on error.
        """
        row = {
            "user_id": user_id,
            "gmail_message_id": email.get("gmail_message_id"),
            "sender": email.get("sender"),
            "sender_name": email.get("sender_name"),
            "subject": email.get("subject"),
            "received_at": email.get("received_at"),
            "priority": classification.get("priority"),
            "action_type": classification.get("action_type"),
            "category": classification.get("category"),
            "confidence": classification.get("confidence"),
            "reasoning": classification.get("reasoning"),
            "draft_reply": draft,
            "status": status,
            "auto_action": auto_action,
        }

        try:
            response = (
                self._db.table("email_triage")
                .upsert(row, on_conflict="user_id,gmail_message_id")
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as exc:
            logger.error("Failed to store triage result: %s", exc)
            return None
