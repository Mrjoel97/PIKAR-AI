# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Gmail reader service for inbox access.

Enables agents to read and manage emails for:
- Daily briefing generation
- Email triage and classification
- Inbox monitoring
"""

import base64
import re
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError


class GmailReader:
    """Service for reading and managing Gmail inbox.

    Provides methods for:
    - Listing messages with query filters
    - Fetching and parsing full message content
    - Batch retrieving messages
    - Modifying message labels (archive, mark read, etc.)
    """

    def __init__(self, credentials: Credentials) -> None:
        """Initialize with Google OAuth credentials.

        Args:
            credentials: Google OAuth credentials with Gmail read scope.
        """
        self.credentials = credentials
        self._service: Resource | None = None

    @property
    def service(self) -> Resource:
        """Lazy-load Gmail API service."""
        if self._service is None:
            self._service = build("gmail", "v1", credentials=self.credentials)
        return self._service

    def list_messages(
        self,
        query: str = "is:unread",
        max_results: int = 50,
        label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """List messages matching the given query.

        Args:
            query: Gmail search query string (e.g. "is:unread", "from:boss@corp.com").
            max_results: Maximum number of messages to return (1–500).
            label_ids: Optional list of label IDs to filter by.

        Returns:
            Dict with status, messages list (id + threadId), and count.
        """
        try:
            kwargs: dict[str, Any] = {
                "userId": "me",
                "q": query,
                "maxResults": max_results,
            }
            if label_ids:
                kwargs["labelIds"] = label_ids

            response = self.service.users().messages().list(**kwargs).execute()
            messages = response.get("messages", [])
            return {
                "status": "success",
                "messages": messages,
                "count": len(messages),
            }
        except HttpError as exc:
            return {
                "status": "error",
                "error": str(exc),
                "messages": [],
                "count": 0,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
                "messages": [],
                "count": 0,
            }

    def get_message(
        self,
        message_id: str,
        msg_format: str = "full",
    ) -> dict[str, Any]:
        """Fetch and parse a single Gmail message.

        Extracts sender name/address, subject, body (text/plain preferred),
        snippet, labels, and received timestamp from the message payload.

        Args:
            message_id: The Gmail message ID to retrieve.
            msg_format: API format — "full", "metadata", "minimal", or "raw".

        Returns:
            Dict with status and parsed message fields, or error details.
        """
        try:
            raw = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format=msg_format)
                .execute()
            )

            payload = raw.get("payload", {})
            headers = {
                h["name"].lower(): h["value"] for h in payload.get("headers", [])
            }

            from_header = headers.get("from", "")
            sender_name, sender = self._parse_sender(from_header)
            subject = headers.get("subject", "")
            received_at = headers.get("date", "")

            body = self._extract_body(payload)

            return {
                "status": "success",
                "message": {
                    "id": raw.get("id"),
                    "thread_id": raw.get("threadId"),
                    "sender": sender,
                    "sender_name": sender_name,
                    "subject": subject,
                    "body": body,
                    "snippet": raw.get("snippet", ""),
                    "labels": raw.get("labelIds", []),
                    "received_at": received_at,
                },
            }
        except HttpError as exc:
            return {
                "status": "error",
                "message_id": message_id,
                "error": str(exc),
            }
        except Exception as exc:
            return {
                "status": "error",
                "message_id": message_id,
                "error": str(exc),
            }

    def batch_get_messages(
        self,
        message_ids: list[str],
        msg_format: str = "metadata",
    ) -> dict[str, Any]:
        """Fetch multiple messages by ID.

        Calls get_message for each ID and collects successes and failures
        separately.

        Args:
            message_ids: List of Gmail message IDs to retrieve.
            msg_format: API format passed to each get_message call.

        Returns:
            Dict with status ("success" or "partial"), messages list, and
            errors list.
        """
        messages: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for mid in message_ids:
            result = self.get_message(mid, msg_format=msg_format)
            if result["status"] == "success":
                messages.append(result["message"])
            else:
                errors.append(result)

        overall_status = "success" if not errors else "partial"
        return {
            "status": overall_status,
            "messages": messages,
            "errors": errors,
        }

    def modify_message(
        self,
        message_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Modify labels on a message (e.g. archive, mark as read).

        Args:
            message_id: The Gmail message ID to modify.
            add_labels: Label IDs to add (e.g. ["STARRED"]).
            remove_labels: Label IDs to remove (e.g. ["UNREAD", "INBOX"]).

        Returns:
            Dict with status, message_id, and updated label IDs.
        """
        try:
            body: dict[str, list[str]] = {
                "addLabelIds": add_labels or [],
                "removeLabelIds": remove_labels or [],
            }
            result = (
                self.service.users()
                .messages()
                .modify(userId="me", id=message_id, body=body)
                .execute()
            )
            return {
                "status": "success",
                "message_id": result.get("id", message_id),
                "labels": result.get("labelIds", []),
            }
        except HttpError as exc:
            return {
                "status": "error",
                "message_id": message_id,
                "error": str(exc),
            }
        except Exception as exc:
            return {
                "status": "error",
                "message_id": message_id,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_sender(self, from_header: str) -> tuple[str, str]:
        """Parse a From header into (display_name, email_address).

        Handles both "Name <email>" and bare "email" formats.

        Args:
            from_header: Raw value of the "From" email header.

        Returns:
            Tuple of (display_name, email_address). display_name is empty
            string when not present.
        """
        match = re.match(r"^(.*?)\s*<([^>]+)>\s*$", from_header.strip())
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
            return name, email
        # Bare email address — no display name
        return "", from_header.strip()

    def _extract_body(self, payload: dict[str, Any]) -> str:
        """Recursively extract plain-text body from a message payload.

        Walks multipart MIME trees, preferring text/plain parts.

        Args:
            payload: The "payload" dict from the Gmail API message object.

        Returns:
            Decoded plain-text body string, or empty string if not found.
        """
        mime_type: str = payload.get("mimeType", "")

        # Plain text part — decode and return
        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode(
                    "utf-8", errors="replace"
                )
            return ""

        # Multipart — recurse into sub-parts, prefer text/plain
        if mime_type.startswith("multipart/"):
            parts = payload.get("parts", [])
            plain_text = ""
            for part in parts:
                extracted = self._extract_body(part)
                if extracted:
                    part_mime = part.get("mimeType", "")
                    if part_mime == "text/plain":
                        return extracted  # Prefer text/plain immediately
                    if not plain_text:
                        plain_text = extracted
            return plain_text

        return ""


def get_gmail_reader(credentials: Credentials) -> GmailReader:
    """Get GmailReader instance.

    Args:
        credentials: Google OAuth credentials with Gmail read scope.

    Returns:
        Configured GmailReader instance.
    """
    return GmailReader(credentials)
