# Daily Briefing & Inbox Intelligence — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build an AI-powered Daily Briefing system that reads Gmail, triages emails with AI classification, drafts replies, auto-handles trivial messages, and presents everything in a dashboard widget with approval workflows.

**Architecture:** Background triage worker (Cloud Scheduler) pre-fetches and classifies emails into an `email_triage` table. A dashboard widget and chat agent both consume this pre-computed data. Users approve/edit/dismiss drafted replies. Auto-act handles low-stakes emails in shadow mode first.

**Tech Stack:** Python 3.10+ (FastAPI), Google Gmail API v1, Google ADK tools, Gemini AI (classification + drafts), Supabase (PostgreSQL + Realtime), Next.js/React (frontend widget), Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-03-19-daily-briefing-inbox-intelligence-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|----------------|
| `app/integrations/google/gmail_reader.py` | Gmail read/modify API wrapper — separate from GmailService (send) to keep single-responsibility. Shares credential pattern but not class hierarchy. |
| `app/agents/tools/gmail_inbox.py` | ADK tool definitions for inbox reading (read_inbox, read_email, etc.) |
| `app/services/email_triage_service.py` | AI classification engine + draft generation |
| `app/services/email_triage_worker.py` | Scheduled endpoint for background triage |
| `app/agents/tools/briefing_tools.py` | ADK tool definitions for briefing actions |
| `app/services/briefing_digest_service.py` | Email digest delivery |
| `supabase/migrations/20260319200000_email_triage.sql` | email_triage table, RLS, triggers, realtime |
| `supabase/migrations/20260319200001_user_briefing_preferences.sql` | preferences table, RLS, triggers |
| `tests/unit/test_gmail_reader.py` | Unit tests for Gmail reader |
| `tests/unit/test_email_triage_service.py` | Unit tests for triage classification + safety |
| `tests/unit/test_email_triage_worker.py` | Unit tests for worker orchestration |
| `tests/unit/test_briefing_tools.py` | Unit tests for briefing tool wrappers |
| `frontend/src/components/widgets/DailyBriefingWidget.tsx` | Main briefing widget |
| `frontend/src/components/NotificationCenter.tsx` | Bell icon + dropdown notification panel |
| `frontend/src/services/briefing.ts` | API client for briefing endpoints |
| `frontend/src/app/settings/briefing/page.tsx` | Briefing preferences settings page |

### Modified Files

| File | Change |
|------|--------|
| `app/integrations/google/client.py` | Add `get_user_gmail_credentials()` with refresh token + client_id/secret |
| `app/routers/briefing.py` | Add triage endpoints to existing router |
| `app/services/scheduled_endpoints.py` | Add `triage-tick` endpoint |
| `app/agent.py` | Import and add GMAIL_INBOX_TOOLS + BRIEFING_TOOLS |
| `app/agents/tools/registry.py` | Register new tools for workflow engine |
| `frontend/src/services/auth.ts` | Add Gmail scopes + offline access to OAuth |
| `frontend/src/components/widgets/WidgetRegistry.tsx` | Register DailyBriefingWidget |

---

## Task 1: Database Migrations

**Files:**
- Create: `supabase/migrations/20260319200000_email_triage.sql`
- Create: `supabase/migrations/20260319200001_user_briefing_preferences.sql`

- [x] **Step 1: Create email_triage migration**

```sql
-- supabase/migrations/20260319200000_email_triage.sql

-- Email triage table for AI-classified inbox items
CREATE TABLE IF NOT EXISTS email_triage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    gmail_message_id TEXT NOT NULL,
    thread_id TEXT,

    -- Email metadata
    sender TEXT NOT NULL,
    sender_name TEXT,
    subject TEXT,
    snippet TEXT,
    received_at TIMESTAMPTZ,

    -- AI classification
    priority TEXT NOT NULL CHECK (priority IN ('urgent', 'important', 'normal', 'low')),
    action_type TEXT NOT NULL CHECK (action_type IN ('needs_reply', 'needs_review', 'fyi', 'auto_handle', 'spam')),
    category TEXT CHECK (category IN ('meeting', 'deal', 'task', 'report', 'personal', 'newsletter', 'notification')),
    confidence FLOAT NOT NULL,
    classification_reasoning TEXT,

    -- Draft response
    draft_reply TEXT,
    draft_confidence FLOAT,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'sent', 'dismissed', 'auto_handled')),
    auto_action_taken TEXT,
    user_action TEXT,
    acted_at TIMESTAMPTZ,

    -- Briefing association
    briefing_date DATE NOT NULL DEFAULT CURRENT_DATE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, gmail_message_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_triage_user_date ON email_triage(user_id, briefing_date);
CREATE INDEX IF NOT EXISTS idx_email_triage_status ON email_triage(user_id, status);
CREATE INDEX IF NOT EXISTS idx_email_triage_gmail_id ON email_triage(gmail_message_id);

-- RLS
ALTER TABLE email_triage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own triage items"
    ON email_triage FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own triage items"
    ON email_triage FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to email_triage"
    ON email_triage FOR ALL
    USING (auth.role() = 'service_role');

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_email_triage_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER email_triage_updated_at
    BEFORE UPDATE ON email_triage
    FOR EACH ROW
    EXECUTE FUNCTION update_email_triage_updated_at();

-- Enable realtime for frontend
ALTER PUBLICATION supabase_realtime ADD TABLE email_triage;

-- RPC to get provider refresh token from auth.sessions (service role only)
CREATE OR REPLACE FUNCTION get_user_provider_refresh_token(p_user_id UUID)
RETURNS TABLE(provider_refresh_token TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT s.provider_refresh_token
    FROM auth.sessions s
    WHERE s.user_id = p_user_id
      AND s.provider_refresh_token IS NOT NULL
    ORDER BY s.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

- [x] **Step 2: Create user_briefing_preferences migration**

```sql
-- supabase/migrations/20260319200001_user_briefing_preferences.sql

CREATE TABLE IF NOT EXISTS user_briefing_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    briefing_time TIME NOT NULL DEFAULT '07:00',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    email_digest_enabled BOOLEAN NOT NULL DEFAULT true,
    email_digest_frequency TEXT NOT NULL DEFAULT 'daily' CHECK (email_digest_frequency IN ('daily', 'weekdays', 'off')),
    auto_act_enabled BOOLEAN NOT NULL DEFAULT false,
    auto_act_daily_cap INTEGER NOT NULL DEFAULT 10,
    auto_act_categories TEXT[] DEFAULT '{}',
    vip_senders TEXT[] DEFAULT '{}',
    ignored_senders TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS
ALTER TABLE user_briefing_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own preferences"
    ON user_briefing_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own preferences"
    ON user_briefing_preferences FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
    ON user_briefing_preferences FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to briefing preferences"
    ON user_briefing_preferences FOR ALL
    USING (auth.role() = 'service_role');

-- Reuse trigger function from email_triage migration
CREATE TRIGGER briefing_preferences_updated_at
    BEFORE UPDATE ON user_briefing_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_email_triage_updated_at();
```

- [x] **Step 3: Apply migrations locally**

Run: `supabase db push --local`
Expected: Both migrations apply successfully.

- [x] **Step 4: Verify tables exist**

Run: `supabase db reset --local` (clean rebuild to test from scratch)
Expected: No errors. Both tables visible in Supabase Studio.

- [x] **Step 5: Commit**

```bash
git add supabase/migrations/20260319200000_email_triage.sql supabase/migrations/20260319200001_user_briefing_preferences.sql
git commit -m "feat: add email_triage and user_briefing_preferences tables"
```

---

## Task 2: Gmail Reader Service

**Files:**
- Create: `app/integrations/google/gmail_reader.py`
- Modify: `app/integrations/google/client.py`
- Create: `tests/unit/test_gmail_reader.py`

- [x] **Step 1: Write failing tests for GmailReader**

```python
# tests/unit/test_gmail_reader.py
"""Tests for Gmail inbox reading service."""

import pytest
from unittest.mock import MagicMock, patch
from app.integrations.google.gmail_reader import GmailReader


@pytest.fixture
def mock_credentials():
    """Mock Google credentials."""
    creds = MagicMock()
    creds.token = "test_token"
    creds.valid = True
    return creds


@pytest.fixture
def reader(mock_credentials):
    """Gmail reader with mocked credentials."""
    with patch("app.integrations.google.gmail_reader.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        r = GmailReader(mock_credentials)
        r._service = mock_service
        return r


class TestListMessages:
    def test_list_unread_messages(self, reader):
        """Should return list of message IDs for unread emails."""
        reader._service.users().messages().list().execute.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "t1"},
                {"id": "msg2", "threadId": "t2"},
            ],
            "resultSizeEstimate": 2,
        }

        result = reader.list_messages(query="is:unread", max_results=10)

        assert result["status"] == "success"
        assert len(result["messages"]) == 2
        assert result["messages"][0]["id"] == "msg1"

    def test_list_messages_empty_inbox(self, reader):
        """Should handle empty inbox gracefully."""
        reader._service.users().messages().list().execute.return_value = {
            "resultSizeEstimate": 0,
        }

        result = reader.list_messages()

        assert result["status"] == "success"
        assert result["messages"] == []


class TestGetMessage:
    def test_get_full_message(self, reader):
        """Should parse email metadata from Gmail API response."""
        reader._service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "threadId": "t1",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Jane Doe <jane@example.com>"},
                    {"name": "Subject", "value": "Q1 Report"},
                    {"name": "Date", "value": "Wed, 19 Mar 2026 10:00:00 +0000"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": "SGVsbG8gV29ybGQ="},  # "Hello World" base64
                    }
                ],
            },
            "snippet": "Hello World",
            "internalDate": "1742385600000",
        }

        result = reader.get_message("msg1")

        assert result["status"] == "success"
        assert result["sender"] == "jane@example.com"
        assert result["sender_name"] == "Jane Doe"
        assert result["subject"] == "Q1 Report"
        assert "Hello World" in result["body"]

    def test_get_message_not_found(self, reader):
        """Should return error for missing message."""
        from googleapiclient.errors import HttpError
        import httplib2

        reader._service.users().messages().get().execute.side_effect = HttpError(
            httplib2.Response({"status": "404"}), b"Not Found"
        )

        result = reader.get_message("nonexistent")

        assert result["status"] == "error"


class TestModifyMessage:
    def test_archive_message(self, reader):
        """Should remove INBOX label to archive."""
        reader._service.users().messages().modify().execute.return_value = {
            "id": "msg1",
            "labelIds": ["IMPORTANT"],
        }

        result = reader.modify_message("msg1", remove_labels=["INBOX"])

        assert result["status"] == "success"

    def test_mark_as_read(self, reader):
        """Should remove UNREAD label."""
        reader._service.users().messages().modify().execute.return_value = {
            "id": "msg1",
            "labelIds": ["INBOX"],
        }

        result = reader.modify_message("msg1", remove_labels=["UNREAD"])

        assert result["status"] == "success"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_gmail_reader.py -v`
Expected: ImportError — `gmail_reader` module does not exist.

- [x] **Step 3: Implement GmailReader service**

```python
# app/integrations/google/gmail_reader.py
"""Gmail inbox reading service.

Provides methods for reading, searching, and modifying Gmail messages.
Used by the email triage system for inbox intelligence.
"""

import base64
import re
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError


class GmailReader:
    """Service for reading Gmail inbox.

    Provides methods for:
    - Listing messages (with search filters)
    - Getting full message content
    - Batch message retrieval
    - Modifying messages (labels, archive, mark read)
    """

    def __init__(self, credentials: Credentials):
        """Initialize with Google OAuth credentials."""
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
        """List messages matching a query.

        Args:
            query: Gmail search query (e.g., "is:unread", "from:boss@co.com").
            max_results: Maximum messages to return (capped at 50 for triage).
            label_ids: Optional label filter.

        Returns:
            Dict with status and list of message stubs (id, threadId).
        """
        try:
            params: dict[str, Any] = {
                "userId": "me",
                "q": query,
                "maxResults": min(max_results, 50),
            }
            if label_ids:
                params["labelIds"] = label_ids

            response = self.service.users().messages().list(**params).execute()
            messages = response.get("messages", [])

            return {
                "status": "success",
                "messages": messages,
                "count": len(messages),
                "result_size_estimate": response.get("resultSizeEstimate", 0),
            }
        except HttpError as e:
            return {"status": "error", "message": f"Gmail API error: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to list messages: {e}"}

    def get_message(
        self,
        message_id: str,
        msg_format: str = "full",
    ) -> dict[str, Any]:
        """Get a full message by ID.

        Args:
            message_id: Gmail message ID.
            format: Response format ("full", "metadata", "minimal").

        Returns:
            Dict with parsed email fields: sender, sender_name, subject, body,
            snippet, labels, received_at, thread_id.
        """
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format=msg_format)
                .execute()
            )

            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            sender_raw = headers.get("from", "")
            sender_name, sender_email = self._parse_sender(sender_raw)
            body = self._extract_body(msg.get("payload", {}))

            return {
                "status": "success",
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "sender": sender_email,
                "sender_name": sender_name,
                "subject": headers.get("subject", "(no subject)"),
                "body": body,
                "snippet": msg.get("snippet", ""),
                "labels": msg.get("labelIds", []),
                "received_at": headers.get("date", ""),
                "internal_date": msg.get("internalDate"),
            }
        except HttpError as e:
            return {"status": "error", "message": f"Gmail API error: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get message: {e}"}

    def batch_get_messages(
        self,
        message_ids: list[str],
        msg_format: str = "metadata",
    ) -> dict[str, Any]:
        """Get multiple messages efficiently.

        Args:
            message_ids: List of Gmail message IDs.
            format: Response format for each message.

        Returns:
            Dict with status and list of parsed messages.
        """
        results = []
        errors = []

        for msg_id in message_ids:
            result = self.get_message(msg_id, format=format)
            if result["status"] == "success":
                results.append(result)
            else:
                errors.append({"id": msg_id, "error": result.get("message")})

        return {
            "status": "success" if not errors else "partial",
            "messages": results,
            "errors": errors,
            "count": len(results),
        }

    def modify_message(
        self,
        message_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Modify message labels (archive, mark read, etc.).

        Args:
            message_id: Gmail message ID.
            add_labels: Labels to add.
            remove_labels: Labels to remove (e.g., ["INBOX"] to archive,
                          ["UNREAD"] to mark read).

        Returns:
            Dict with modified message state.
        """
        try:
            body: dict[str, Any] = {}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels

            result = (
                self.service.users()
                .messages()
                .modify(userId="me", id=message_id, body=body)
                .execute()
            )

            return {
                "status": "success",
                "id": result["id"],
                "labels": result.get("labelIds", []),
            }
        except HttpError as e:
            return {"status": "error", "message": f"Gmail API error: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to modify message: {e}"}

    @staticmethod
    def _parse_sender(from_header: str) -> tuple[str, str]:
        """Parse 'Name <email>' into (name, email)."""
        match = re.match(r"(.+?)\s*<(.+?)>", from_header)
        if match:
            return match.group(1).strip().strip('"'), match.group(2).strip()
        return "", from_header.strip()

    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Extract plain text body from Gmail message payload."""
        # Direct body
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        # Multipart — find text/plain part
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="replace"
                    )
            # Nested multipart
            if part.get("parts"):
                result = GmailReader._extract_body(part)
                if result:
                    return result

        return ""


def get_gmail_reader(credentials: Credentials) -> GmailReader:
    """Get GmailReader service instance."""
    return GmailReader(credentials)
```

- [x] **Step 4: Add background credential helper to client.py**

Add this function to `app/integrations/google/client.py`:

```python
def get_user_gmail_credentials(
    provider_refresh_token: str,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> Credentials:
    """Create Google credentials for background Gmail access.

    Unlike get_google_credentials(), this uses a refresh token to obtain
    new access tokens without an active user session. Required for the
    email triage background worker.

    Args:
        provider_refresh_token: Google OAuth refresh token from Supabase session.
        client_id: Google OAuth client ID. Falls back to GOOGLE_CLIENT_ID env var.
        client_secret: Google OAuth client secret. Falls back to GOOGLE_CLIENT_SECRET env var.

    Returns:
        Google Credentials object that can auto-refresh.

    Raises:
        ValueError: If refresh token or client credentials are missing.
    """
    import os

    resolved_client_id = client_id or os.environ.get("GOOGLE_CLIENT_ID", "")
    resolved_client_secret = client_secret or os.environ.get("GOOGLE_CLIENT_SECRET", "")

    if not provider_refresh_token:
        raise ValueError("Refresh token required for background Gmail access.")
    if not resolved_client_id or not resolved_client_secret:
        raise ValueError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET required for background Gmail access."
        )

    return Credentials(
        token=None,
        refresh_token=provider_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=resolved_client_id,
        client_secret=resolved_client_secret,
    )
```

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_gmail_reader.py -v`
Expected: All tests pass.

- [x] **Step 6: Commit**

```bash
git add app/integrations/google/gmail_reader.py app/integrations/google/client.py tests/unit/test_gmail_reader.py
git commit -m "feat: add Gmail inbox reading service with background credential support"
```

---

## Task 3: Gmail Inbox ADK Tools

**Files:**
- Create: `app/agents/tools/gmail_inbox.py`
- Create: `tests/unit/test_gmail_inbox_tools.py`

- [x] **Step 1: Write failing tests**

```python
# tests/unit/test_gmail_inbox_tools.py
"""Tests for Gmail inbox ADK tools."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_tool_context():
    """Mock ADK tool context with Google tokens."""
    ctx = MagicMock()
    ctx.state = {
        "google_provider_token": "test_access_token",
        "google_refresh_token": "test_refresh_token",
    }
    return ctx


class TestReadInbox:
    def test_returns_unread_emails(self, mock_tool_context):
        from app.agents.tools.gmail_inbox import read_inbox

        with patch("app.agents.tools.gmail_inbox._get_gmail_reader") as mock_get:
            mock_reader = MagicMock()
            mock_reader.list_messages.return_value = {
                "status": "success",
                "messages": [{"id": "m1"}, {"id": "m2"}],
                "count": 2,
            }
            mock_reader.get_message.side_effect = [
                {
                    "status": "success",
                    "sender": "boss@co.com",
                    "sender_name": "Boss",
                    "subject": "Urgent: Review needed",
                    "snippet": "Please review ASAP",
                    "received_at": "2026-03-19",
                },
                {
                    "status": "success",
                    "sender": "newsletter@co.com",
                    "sender_name": "Newsletter",
                    "subject": "Weekly digest",
                    "snippet": "This week in tech",
                    "received_at": "2026-03-19",
                },
            ]
            mock_get.return_value = mock_reader

            result = read_inbox(mock_tool_context, max_results=10)

        assert result["status"] == "success"
        assert len(result["emails"]) == 2

    def test_auth_required_error(self, mock_tool_context):
        from app.agents.tools.gmail_inbox import read_inbox

        mock_tool_context.state = {}
        result = read_inbox(mock_tool_context)
        assert result["status"] == "error"
        assert result["auth_required"] is True
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_gmail_inbox_tools.py -v`
Expected: ImportError — `gmail_inbox` module does not exist.

- [x] **Step 3: Implement gmail_inbox tools**

```python
# app/agents/tools/gmail_inbox.py
"""Gmail inbox tools for agents.

Provides tools for reading and managing inbox emails.
"""

from typing import Any

ToolContextType = Any


def _get_gmail_reader(tool_context: ToolContextType):
    """Get GmailReader from tool context credentials."""
    from app.integrations.google.gmail_reader import GmailReader
    from app.integrations.google.client import get_google_credentials

    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")

    if not provider_token:
        raise ValueError("Google authentication required for inbox features.")

    credentials = get_google_credentials(provider_token, refresh_token)
    return GmailReader(credentials)


def read_inbox(
    tool_context: ToolContextType,
    max_results: int = 20,
    query: str = "is:unread",
) -> dict[str, Any]:
    """Read recent emails from the user's inbox.

    Use this to check what emails the user has received.
    Returns sender, subject, snippet, and date for each email.

    Args:
        tool_context: Agent tool context.
        max_results: Maximum number of emails to return (default 20, max 50).
        query: Gmail search query (default "is:unread").

    Returns:
        Dict with list of email summaries.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        listing = reader.list_messages(query=query, max_results=max_results)

        if listing["status"] != "success":
            return listing

        emails = []
        for msg_stub in listing.get("messages", []):
            msg = reader.get_message(msg_stub["id"], format="metadata")
            if msg["status"] == "success":
                emails.append({
                    "id": msg["id"],
                    "thread_id": msg.get("thread_id"),
                    "sender": msg.get("sender"),
                    "sender_name": msg.get("sender_name"),
                    "subject": msg.get("subject"),
                    "snippet": msg.get("snippet"),
                    "received_at": msg.get("received_at"),
                    "labels": msg.get("labels", []),
                })

        return {
            "status": "success",
            "emails": emails,
            "count": len(emails),
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to read inbox: {e}"}


def read_email(
    tool_context: ToolContextType,
    message_id: str,
) -> dict[str, Any]:
    """Read a specific email's full content.

    Use this to get the complete body of an email for detailed review.

    Args:
        tool_context: Agent tool context.
        message_id: Gmail message ID from read_inbox results.

    Returns:
        Dict with full email content including body.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        return reader.get_message(message_id, format="full")
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to read email: {e}"}


def archive_email(
    tool_context: ToolContextType,
    message_id: str,
) -> dict[str, Any]:
    """Archive an email (remove from inbox, mark as read).

    Args:
        tool_context: Agent tool context.
        message_id: Gmail message ID.

    Returns:
        Dict with archive status.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        return reader.modify_message(
            message_id, remove_labels=["INBOX", "UNREAD"]
        )
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to archive email: {e}"}


def classify_email(
    tool_context: ToolContextType,
    message_id: str,
) -> dict[str, Any]:
    """Classify an email using AI triage.

    Thin wrapper around EmailTriageService.classify(). Results are
    persisted to the email_triage table for the daily briefing.

    Args:
        tool_context: Agent tool context.
        message_id: Gmail message ID to classify.

    Returns:
        Dict with priority, action_type, category, confidence, reasoning.
    """
    try:
        import asyncio
        from app.services.email_triage_service import EmailTriageService
        from app.services.supabase import get_service_client

        reader = _get_gmail_reader(tool_context)
        msg = reader.get_message(message_id, msg_format="full")
        if msg["status"] != "success":
            return msg

        client = get_service_client()
        triage = EmailTriageService(client)

        # Get user preferences for VIP/ignored senders
        user_id = tool_context.state.get("user_id", "")
        prefs_result = client.table("user_briefing_preferences").select("*").eq("user_id", user_id).execute()
        prefs = prefs_result.data[0] if prefs_result.data else {}

        # Run classification (async → sync bridge for ADK tool)
        loop = asyncio.get_event_loop()
        classification = loop.run_until_complete(triage.classify_email(msg, prefs))

        # Persist to email_triage table
        loop.run_until_complete(triage.store_triage_result(
            user_id=user_id, email=msg, classification=classification,
        ))

        return {"status": "success", **classification}
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to classify email: {e}"}


def label_email(
    tool_context: ToolContextType,
    message_id: str,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Add or remove labels on an email.

    Args:
        tool_context: Agent tool context.
        message_id: Gmail message ID.
        add_labels: Labels to add.
        remove_labels: Labels to remove.

    Returns:
        Dict with updated label state.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        return reader.modify_message(
            message_id, add_labels=add_labels, remove_labels=remove_labels
        )
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to label email: {e}"}


# Export
GMAIL_INBOX_TOOLS = [
    read_inbox,
    read_email,
    classify_email,
    archive_email,
    label_email,
]
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_gmail_inbox_tools.py -v`
Expected: All tests pass.

- [x] **Step 5: Commit**

```bash
git add app/agents/tools/gmail_inbox.py tests/unit/test_gmail_inbox_tools.py
git commit -m "feat: add Gmail inbox reading ADK tools"
```

---

## Task 4: Email Triage Service

**Files:**
- Create: `app/services/email_triage_service.py`
- Create: `tests/unit/test_email_triage_service.py`

- [x] **Step 1: Write failing tests for classification**

```python
# tests/unit/test_email_triage_service.py
"""Tests for email triage classification and draft generation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.email_triage_service import EmailTriageService


@pytest.fixture
def triage_service():
    """EmailTriageService with mocked dependencies."""
    mock_supabase = MagicMock()
    return EmailTriageService(supabase_client=mock_supabase)


class TestClassification:
    @pytest.mark.asyncio
    async def test_classify_urgent_email(self, triage_service):
        """Emails with urgent signals should be classified as urgent."""
        email = {
            "sender": "ceo@company.com",
            "subject": "URGENT: Board meeting moved to today",
            "snippet": "We need to discuss the acquisition ASAP",
            "body": "The board meeting has been moved. Please prepare.",
        }
        prefs = {"vip_senders": ["ceo@company.com"]}

        with patch.object(triage_service, "_call_classifier") as mock_ai:
            mock_ai.return_value = {
                "priority": "urgent",
                "action_type": "needs_reply",
                "category": "meeting",
                "confidence": 0.95,
                "reasoning": "VIP sender + urgent keyword + time-sensitive",
            }

            result = await triage_service.classify_email(email, prefs)

        assert result["priority"] == "urgent"
        assert result["action_type"] == "needs_reply"
        assert result["confidence"] >= 0.85

    @pytest.mark.asyncio
    async def test_classify_newsletter(self, triage_service):
        """Newsletters should be classified as fyi/low."""
        email = {
            "sender": "digest@techcrunch.com",
            "subject": "TechCrunch Daily - March 19",
            "snippet": "Today's top stories in tech...",
            "body": "Weekly newsletter content",
        }

        with patch.object(triage_service, "_call_classifier") as mock_ai:
            mock_ai.return_value = {
                "priority": "low",
                "action_type": "fyi",
                "category": "newsletter",
                "confidence": 0.98,
                "reasoning": "Automated newsletter from known source",
            }

            result = await triage_service.classify_email(email, {})

        assert result["priority"] == "low"
        assert result["action_type"] == "fyi"
        assert result["category"] == "newsletter"


class TestAutoActSafety:
    @pytest.mark.asyncio
    async def test_low_confidence_never_auto_acts(self, triage_service):
        """Emails with confidence < 0.85 must never be auto-handled."""
        result = triage_service.should_auto_act(
            action_type="auto_handle",
            confidence=0.80,
            prefs={"auto_act_enabled": True, "auto_act_daily_cap": 10},
            auto_acted_today=0,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_daily_cap_enforced(self, triage_service):
        """Should not auto-act when daily cap is reached."""
        result = triage_service.should_auto_act(
            action_type="auto_handle",
            confidence=0.95,
            prefs={"auto_act_enabled": True, "auto_act_daily_cap": 10},
            auto_acted_today=10,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_auto_act_disabled(self, triage_service):
        """Should not auto-act when user has disabled it."""
        result = triage_service.should_auto_act(
            action_type="auto_handle",
            confidence=0.95,
            prefs={"auto_act_enabled": False, "auto_act_daily_cap": 10},
            auto_acted_today=0,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_auto_act_allowed(self, triage_service):
        """Should auto-act when all conditions met."""
        result = triage_service.should_auto_act(
            action_type="auto_handle",
            confidence=0.95,
            prefs={"auto_act_enabled": True, "auto_act_daily_cap": 10},
            auto_acted_today=5,
        )
        assert result is True


class TestDraftGeneration:
    @pytest.mark.asyncio
    async def test_generate_draft_for_needs_reply(self, triage_service):
        """Should generate a draft reply for needs_reply emails."""
        email = {
            "sender": "client@acme.com",
            "subject": "Follow up on proposal",
            "body": "Hi, just checking in on the proposal we discussed last week.",
        }

        with patch.object(triage_service, "_call_draft_generator") as mock_ai:
            mock_ai.return_value = {
                "draft": "Hi, thanks for following up. I'll have the updated proposal to you by end of day tomorrow.",
                "confidence": 0.82,
            }

            result = await triage_service.generate_draft(email)

        assert result["draft"] is not None
        assert result["confidence"] > 0
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_email_triage_service.py -v`
Expected: ImportError — `email_triage_service` module does not exist.

- [x] **Step 3: Implement EmailTriageService**

```python
# app/services/email_triage_service.py
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
    "meeting", "deal", "task", "report",
    "personal", "newsletter", "notification",
}

CLASSIFICATION_PROMPT = """Classify this email for an executive's daily briefing.

Email:
- From: {sender} ({sender_name})
- Subject: {subject}
- Body: {body}

VIP senders (always mark urgent): {vip_senders}
Ignored senders (always mark low): {ignored_senders}

Respond with JSON only:
{{
    "priority": "urgent|important|normal|low",
    "action_type": "needs_reply|needs_review|fyi|auto_handle|spam",
    "category": "meeting|deal|task|report|personal|newsletter|notification",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

DRAFT_PROMPT = """Draft a brief, professional reply to this email.
Match a concise executive style. Never commit to anything specific.

Email from {sender}:
Subject: {subject}
Body: {body}

Respond with JSON only:
{{
    "draft": "the reply text",
    "confidence": 0.0-1.0
}}"""


class EmailTriageService:
    """AI-powered email classification and draft generation."""

    def __init__(self, supabase_client: Client):
        """Initialize with Supabase client for data access."""
        self.supabase = supabase_client

    async def classify_email(
        self,
        email: dict[str, Any],
        prefs: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify an email using AI.

        Args:
            email: Dict with sender, subject, snippet, body.
            prefs: User preferences (vip_senders, ignored_senders).

        Returns:
            Dict with priority, action_type, category, confidence, reasoning.
        """
        result = await self._call_classifier(email, prefs)

        # Validate and sanitize
        result["priority"] = (
            result.get("priority", "normal")
            if result.get("priority") in VALID_PRIORITIES
            else "normal"
        )
        result["action_type"] = (
            result.get("action_type", "needs_review")
            if result.get("action_type") in VALID_ACTIONS
            else "needs_review"
        )
        result["category"] = (
            result.get("category")
            if result.get("category") in VALID_CATEGORIES
            else None
        )
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))

        return result

    async def _call_classifier(
        self,
        email: dict[str, Any],
        prefs: dict[str, Any],
    ) -> dict[str, Any]:
        """Call Gemini for email classification."""
        import google.generativeai as genai

        prompt = CLASSIFICATION_PROMPT.format(
            sender=email.get("sender", ""),
            sender_name=email.get("sender_name", ""),
            subject=email.get("subject", ""),
            body=email.get("body", email.get("snippet", ""))[:2000],
            vip_senders=", ".join(prefs.get("vip_senders", [])),
            ignored_senders=", ".join(prefs.get("ignored_senders", [])),
        )

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)

        try:
            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, AttributeError):
            logger.warning("Failed to parse classifier response: %s", response.text)
            return {
                "priority": "normal",
                "action_type": "needs_review",
                "category": None,
                "confidence": 0.3,
                "reasoning": "Classification failed — routing to manual review",
            }

    async def generate_draft(
        self,
        email: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a draft reply for an email.

        Args:
            email: Dict with sender, subject, body.

        Returns:
            Dict with draft text and confidence score.
        """
        return await self._call_draft_generator(email)

    async def _call_draft_generator(
        self,
        email: dict[str, Any],
    ) -> dict[str, Any]:
        """Call Gemini for draft reply generation."""
        import google.generativeai as genai

        prompt = DRAFT_PROMPT.format(
            sender=email.get("sender", ""),
            subject=email.get("subject", ""),
            body=email.get("body", email.get("snippet", ""))[:2000],
        )

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)

        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, AttributeError):
            logger.warning("Failed to parse draft response: %s", response.text)
            return {"draft": None, "confidence": 0.0}

    def should_auto_act(
        self,
        action_type: str,
        confidence: float,
        prefs: dict[str, Any],
        auto_acted_today: int,
    ) -> bool:
        """Check if auto-act is allowed for this email.

        Safety guardrails:
        - auto_act_enabled must be True
        - confidence must be >= 0.85
        - daily cap must not be exceeded
        - action_type must be "auto_handle"

        Args:
            action_type: The AI-assigned action type.
            confidence: Classification confidence score.
            prefs: User briefing preferences.
            auto_acted_today: Number of auto-actions taken today.

        Returns:
            True if auto-act is safe to proceed.
        """
        if not prefs.get("auto_act_enabled", False):
            return False
        if action_type != "auto_handle":
            return False
        if confidence < 0.85:
            return False
        if auto_acted_today >= prefs.get("auto_act_daily_cap", 10):
            return False
        return True

    async def store_triage_result(
        self,
        user_id: str,
        email: dict[str, Any],
        classification: dict[str, Any],
        draft: dict[str, Any] | None = None,
        status: str = "pending",
        auto_action: str | None = None,
    ) -> dict[str, Any] | None:
        """Store a triage result in the database.

        Args:
            user_id: User ID.
            email: Parsed email data.
            classification: AI classification result.
            draft: Optional draft reply data.
            status: Initial status (pending or auto_handled).
            auto_action: Description of auto-action taken, if any.

        Returns:
            Inserted row or None on error.
        """
        try:
            row = {
                "user_id": user_id,
                "gmail_message_id": email.get("id", ""),
                "thread_id": email.get("thread_id"),
                "sender": email.get("sender", ""),
                "sender_name": email.get("sender_name"),
                "subject": email.get("subject"),
                "snippet": email.get("snippet"),
                "received_at": email.get("received_at"),
                "priority": classification["priority"],
                "action_type": classification["action_type"],
                "category": classification.get("category"),
                "confidence": classification["confidence"],
                "classification_reasoning": classification.get("reasoning"),
                "draft_reply": draft.get("draft") if draft else None,
                "draft_confidence": draft.get("confidence") if draft else None,
                "status": status,
                "auto_action_taken": auto_action,
            }

            result = self.supabase.table("email_triage").upsert(
                row, on_conflict="user_id,gmail_message_id"
            ).execute()

            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Failed to store triage result: %s", e)
            return None
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_email_triage_service.py -v`
Expected: All tests pass.

- [x] **Step 5: Commit**

```bash
git add app/services/email_triage_service.py tests/unit/test_email_triage_service.py
git commit -m "feat: add email triage service with AI classification and safety guardrails"
```

---

## Task 5: Email Triage Worker (Scheduled Endpoint)

**Files:**
- Create: `app/services/email_triage_worker.py`
- Modify: `app/services/scheduled_endpoints.py`
- Create: `tests/unit/test_email_triage_worker.py`

- [x] **Step 1: Write failing tests for the worker**

```python
# tests/unit/test_email_triage_worker.py
"""Tests for the email triage background worker."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.email_triage_worker import EmailTriageWorker


@pytest.fixture
def mock_supabase():
    mock = MagicMock()
    return mock


@pytest.fixture
def worker(mock_supabase):
    return EmailTriageWorker(supabase_client=mock_supabase)


class TestShadowMode:
    @pytest.mark.asyncio
    async def test_shadow_mode_records_without_acting(self, worker):
        """Shadow mode should record what would happen without executing."""
        with patch.object(worker, "_get_user_refresh_token", return_value="token"):
            with patch.object(worker, "_get_existing_message_ids", return_value=set()):
                with patch.object(worker, "_get_auto_act_count_today", return_value=0):
                    with patch("app.services.email_triage_worker.get_user_gmail_credentials"):
                        with patch("app.services.email_triage_worker.GmailReader") as MockReader:
                            mock_reader = MockReader.return_value
                            mock_reader.list_messages.return_value = {
                                "status": "success",
                                "messages": [{"id": "m1"}],
                            }
                            mock_reader.get_message.return_value = {
                                "status": "success",
                                "id": "m1",
                                "sender": "news@co.com",
                                "subject": "Newsletter",
                                "snippet": "Weekly update",
                            }

                            with patch.object(worker.triage_service, "classify_email", return_value={
                                "priority": "low",
                                "action_type": "auto_handle",
                                "category": "newsletter",
                                "confidence": 0.95,
                                "reasoning": "Newsletter",
                            }):
                                with patch.object(worker.triage_service, "store_triage_result") as mock_store:
                                    # auto_act_enabled = False = shadow mode
                                    result = await worker.process_user(
                                        "user1",
                                        {"auto_act_enabled": False},
                                    )

                                    # Verify shadow action was recorded
                                    store_call = mock_store.call_args
                                    assert "shadow:" in (store_call.kwargs.get("auto_action") or store_call[1].get("auto_action", ""))
                                    # Verify no actual Gmail modification was called
                                    mock_reader.modify_message.assert_not_called()


class TestUserProcessing:
    @pytest.mark.asyncio
    async def test_skips_user_without_refresh_token(self, worker, mock_supabase):
        """Should skip users who have no refresh token."""
        mock_supabase.auth.admin.get_user_by_id.return_value = MagicMock(
            user=MagicMock(
                user_metadata={},
                identities=[],
            )
        )

        result = await worker.process_user(
            user_id="user1",
            prefs={"auto_act_enabled": False},
        )

        assert result["status"] == "skipped"
        assert "refresh_token" in result["reason"].lower() or "token" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_isolates_user_failures(self, worker):
        """One user's failure should not affect others."""
        users = [
            {"user_id": "user1", "auto_act_enabled": False},
            {"user_id": "user2", "auto_act_enabled": False},
        ]

        with patch.object(worker, "process_user") as mock_process:
            mock_process.side_effect = [
                Exception("Gmail API error for user1"),
                {"status": "success", "processed": 3},
            ]

            results = await worker.process_all_users(users)

        assert len(results) == 2
        assert results[0]["status"] == "error"
        assert results[1]["status"] == "success"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_email_triage_worker.py -v`
Expected: ImportError — `email_triage_worker` module does not exist.

- [x] **Step 3: Implement EmailTriageWorker**

```python
# app/services/email_triage_worker.py
"""Email triage background worker.

Triggered by Cloud Scheduler via POST /scheduled/triage-tick.
Processes each user's inbox independently with per-user error isolation.
"""

import logging
from typing import Any

from supabase import Client

from app.integrations.google.client import get_user_gmail_credentials
from app.integrations.google.gmail_reader import GmailReader
from app.services.email_triage_service import EmailTriageService

logger = logging.getLogger(__name__)


class EmailTriageWorker:
    """Background worker for periodic email triage."""

    def __init__(self, supabase_client: Client):
        """Initialize with Supabase service-role client."""
        self.supabase = supabase_client
        self.triage_service = EmailTriageService(supabase_client)

    async def run(self) -> dict[str, Any]:
        """Run a full triage cycle for all enabled users.

        Returns:
            Summary of processing results.
        """
        # Get all users with briefing preferences
        try:
            result = self.supabase.table("user_briefing_preferences").select("*").execute()
            users = result.data or []
        except Exception as e:
            logger.error("Failed to fetch user preferences: %s", e)
            return {"status": "error", "message": str(e)}

        if not users:
            return {"status": "success", "message": "No users configured", "processed": 0}

        results = await self.process_all_users(users)

        succeeded = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "error")

        return {
            "status": "success",
            "users_processed": succeeded,
            "users_failed": failed,
            "total": len(results),
        }

    async def process_all_users(
        self,
        users: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Process each user independently with error isolation.

        Args:
            users: List of user preference rows.

        Returns:
            List of per-user processing results.
        """
        results = []
        for user_prefs in users:
            user_id = user_prefs.get("user_id", "unknown")
            try:
                result = await self.process_user(user_id, user_prefs)
                results.append(result)
            except Exception as e:
                logger.error("Triage failed for user %s: %s", user_id, e)
                results.append({
                    "status": "error",
                    "user_id": user_id,
                    "message": str(e),
                })
        return results

    async def process_user(
        self,
        user_id: str,
        prefs: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a single user's inbox.

        Args:
            user_id: Supabase user ID.
            prefs: User's briefing preferences.

        Returns:
            Processing result with count of emails handled.
        """
        # Get refresh token from Supabase auth
        refresh_token = await self._get_user_refresh_token(user_id)
        if not refresh_token:
            return {
                "status": "skipped",
                "user_id": user_id,
                "reason": "No refresh token available — user must re-authorize",
            }

        # Build Gmail reader with background credentials
        try:
            credentials = get_user_gmail_credentials(refresh_token)
            reader = GmailReader(credentials)
        except ValueError as e:
            return {"status": "skipped", "user_id": user_id, "reason": str(e)}

        # Fetch unread emails
        listing = reader.list_messages(query="is:unread", max_results=50)
        if listing["status"] != "success":
            return {"status": "error", "user_id": user_id, "message": listing.get("message")}

        message_stubs = listing.get("messages", [])
        if not message_stubs:
            return {"status": "success", "user_id": user_id, "processed": 0}

        # Filter out already-triaged messages
        existing_ids = await self._get_existing_message_ids(user_id)
        new_stubs = [m for m in message_stubs if m["id"] not in existing_ids]

        if not new_stubs:
            return {"status": "success", "user_id": user_id, "processed": 0, "skipped_dupes": len(message_stubs)}

        # Get auto-act count for today
        auto_acted_today = await self._get_auto_act_count_today(user_id)

        processed = 0
        for stub in new_stubs:
            msg = reader.get_message(stub["id"], format="full")
            if msg["status"] != "success":
                continue

            # Classify
            classification = await self.triage_service.classify_email(msg, prefs)

            # Generate draft if needs_reply
            draft = None
            if classification["action_type"] == "needs_reply":
                draft = await self.triage_service.generate_draft(msg)

            # Check auto-act (shadow mode vs. live mode)
            status = "pending"
            auto_action = None
            if classification["action_type"] == "auto_handle" and classification["confidence"] >= 0.85:
                if not prefs.get("auto_act_enabled", False):
                    # Shadow mode: record what WOULD happen without acting
                    auto_action = f"shadow: would auto-handle as {classification.get('category', 'unknown')}"
                elif self.triage_service.should_auto_act(
                    classification["action_type"],
                    classification["confidence"],
                    prefs,
                    auto_acted_today,
                ):
                    # Live mode: execute the auto-action
                    auto_action = await self._execute_auto_action(
                        reader, msg, classification
                    )
                    status = "auto_handled"
                    auto_acted_today += 1

            # Store result
            await self.triage_service.store_triage_result(
                user_id=user_id,
                email=msg,
                classification=classification,
                draft=draft,
                status=status,
                auto_action=auto_action,
            )

            # Send notification for urgent items
            if classification["priority"] == "urgent" and status == "pending":
                await self._send_urgent_notification(user_id, msg)

            processed += 1

        return {"status": "success", "user_id": user_id, "processed": processed}

    async def _get_user_refresh_token(self, user_id: str) -> str | None:
        """Get a user's Google refresh token from Supabase auth.sessions table.

        Supabase stores provider_refresh_token in auth.sessions, not in
        identity_data. We query it via service role using raw SQL.
        """
        try:
            # Query auth.sessions for the most recent Google session
            result = self.supabase.rpc(
                "get_user_provider_refresh_token",
                {"p_user_id": user_id},
            ).execute()

            if result.data:
                return result.data[0].get("provider_refresh_token") if isinstance(result.data, list) else result.data.get("provider_refresh_token")

            # Fallback: try admin API for identity data
            user_response = self.supabase.auth.admin.get_user_by_id(user_id)
            if user_response and user_response.user:
                for identity in (user_response.user.identities or []):
                    if identity.provider == "google":
                        return (identity.identity_data or {}).get("provider_refresh_token")

            return None
        except Exception as e:
            logger.warning("Failed to get refresh token for user %s: %s", user_id, e)
            return None

    async def _get_existing_message_ids(self, user_id: str) -> set[str]:
        """Get already-triaged message IDs for deduplication."""
        try:
            result = (
                self.supabase.table("email_triage")
                .select("gmail_message_id")
                .eq("user_id", user_id)
                .execute()
            )
            return {row["gmail_message_id"] for row in (result.data or [])}
        except Exception:
            return set()

    async def _get_auto_act_count_today(self, user_id: str) -> int:
        """Get number of auto-actions taken today."""
        try:
            from datetime import date

            result = (
                self.supabase.table("email_triage")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("status", "auto_handled")
                .eq("briefing_date", date.today().isoformat())
                .execute()
            )
            return result.count or 0
        except Exception:
            return 0

    async def _execute_auto_action(
        self,
        reader: GmailReader,
        email: dict[str, Any],
        classification: dict[str, Any],
    ) -> str:
        """Execute an auto-action on an email.

        Returns:
            Description of the action taken.
        """
        category = classification.get("category", "")
        msg_id = email.get("id", "")

        if category == "newsletter":
            reader.modify_message(msg_id, remove_labels=["INBOX", "UNREAD"])
            return "archived: newsletter"
        elif category == "notification":
            reader.modify_message(msg_id, remove_labels=["UNREAD"])
            return "marked read: notification"
        else:
            reader.modify_message(msg_id, remove_labels=["UNREAD"])
            return f"marked read: {category}"

    async def _send_urgent_notification(
        self,
        user_id: str,
        email: dict[str, Any],
    ) -> None:
        """Send in-app notification for urgent emails."""
        try:
            from app.notifications.notification_service import get_notification_service

            service = get_notification_service()
            from app.notifications.notification_service import NotificationType

            await service.create_notification(
                user_id=user_id,
                title=f"Urgent email from {email.get('sender_name', email.get('sender', 'Unknown'))}",
                message=email.get("subject", "(no subject)"),
                type=NotificationType.WARNING,
                link="/dashboard",
                metadata={"email_id": email.get("id"), "type": "urgent_email"},
            )
        except Exception as e:
            logger.warning("Failed to send urgent notification: %s", e)
```

- [x] **Step 4: Add triage-tick endpoint to scheduled_endpoints.py**

Add this endpoint to `app/services/scheduled_endpoints.py`, after the existing endpoints:

```python
@router.post("/triage-tick")
async def trigger_email_triage(x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")):
    """Trigger email triage for all enabled users."""
    _verify_scheduler(x_scheduler_secret)

    from app.services.email_triage_worker import EmailTriageWorker

    client = _get_supabase()
    worker = EmailTriageWorker(supabase_client=client)
    result = await worker.run()

    logger.info("Email triage completed: %s", result)
    return result
```

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_email_triage_worker.py -v`
Expected: All tests pass.

- [x] **Step 6: Commit**

```bash
git add app/services/email_triage_worker.py app/services/scheduled_endpoints.py tests/unit/test_email_triage_worker.py
git commit -m "feat: add email triage background worker with Cloud Scheduler endpoint"
```

---

## Task 6: Briefing API Endpoints

**Files:**
- Modify: `app/routers/briefing.py`
- Create: `app/agents/tools/briefing_tools.py`
- Create: `tests/unit/test_briefing_tools.py`

- [x] **Step 1: Write failing tests for briefing tools**

```python
# tests/unit/test_briefing_tools.py
"""Tests for briefing ADK tools."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_tool_context():
    ctx = MagicMock()
    ctx.state = {"user_id": "test-user-123"}
    return ctx


class TestGetDailyBriefing:
    def test_returns_grouped_triage_items(self, mock_tool_context):
        from app.agents.tools.briefing_tools import get_daily_briefing

        mock_supabase = MagicMock()
        mock_supabase.table().select().eq().eq().order().execute.return_value = MagicMock(
            data=[
                {"id": "1", "priority": "urgent", "action_type": "needs_reply", "status": "pending"},
                {"id": "2", "priority": "low", "action_type": "fyi", "status": "pending"},
                {"id": "3", "priority": "normal", "action_type": "auto_handle", "status": "auto_handled"},
            ]
        )

        with patch("app.agents.tools.briefing_tools._get_supabase", return_value=mock_supabase):
            result = get_daily_briefing(mock_tool_context)

        assert result["status"] == "success"
        assert "urgent" in result or "sections" in result
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_briefing_tools.py -v`
Expected: ImportError.

- [x] **Step 3: Implement briefing_tools.py**

```python
# app/agents/tools/briefing_tools.py
"""Briefing tools for the ExecutiveAgent.

Provides tools for managing the daily briefing:
getting briefing data, approving drafts, dismissing items.
"""

import logging
from datetime import date, datetime, timezone
from typing import Any

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

ToolContextType = Any


def _get_supabase():
    """Get Supabase service client."""
    return get_service_client()


def get_daily_briefing(
    tool_context: ToolContextType,
) -> dict[str, Any]:
    """Get today's daily briefing with triaged emails.

    Returns emails grouped by section: urgent, needs_reply, auto_handled, fyi.

    Args:
        tool_context: Agent tool context (contains user_id in state).

    Returns:
        Dict with briefing sections and counts.
    """
    try:
        user_id = tool_context.state.get("user_id")
        if not user_id:
            return {"status": "error", "message": "User ID not available"}

        client = _get_supabase()
        result = (
            client.table("email_triage")
            .select("*")
            .eq("user_id", user_id)
            .eq("briefing_date", date.today().isoformat())
            .order("received_at", desc=True)
            .execute()
        )

        items = result.data or []

        sections = {
            "urgent": [i for i in items if i["priority"] == "urgent" and i["status"] == "pending"],
            "needs_reply": [i for i in items if i["action_type"] == "needs_reply" and i["status"] == "pending"],
            "auto_handled": [i for i in items if i["status"] == "auto_handled"],
            "fyi": [i for i in items if i["action_type"] == "fyi" and i["status"] == "pending"],
        }

        return {
            "status": "success",
            "sections": sections,
            "counts": {k: len(v) for k, v in sections.items()},
            "total": len(items),
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get briefing: {e}"}


def refresh_briefing(
    tool_context: ToolContextType,
) -> dict[str, Any]:
    """Trigger an on-demand triage refresh.

    Fetches new emails and re-classifies the inbox.

    Args:
        tool_context: Agent tool context.

    Returns:
        Dict with refresh results (count of new items processed).
    """
    try:
        import asyncio
        from app.services.email_triage_worker import EmailTriageWorker

        user_id = tool_context.state.get("user_id")
        if not user_id:
            return {"status": "error", "message": "User ID not available"}

        client = _get_supabase()

        prefs_result = client.table("user_briefing_preferences").select("*").eq("user_id", user_id).execute()
        prefs = prefs_result.data[0] if prefs_result.data else {}

        worker = EmailTriageWorker(supabase_client=client)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(worker.process_user(user_id, prefs))

        return result
    except Exception as e:
        return {"status": "error", "message": f"Failed to refresh: {e}"}


def approve_draft(
    tool_context: ToolContextType,
    triage_item_id: str,
) -> dict[str, Any]:
    """Approve and send a drafted email reply.

    Args:
        tool_context: Agent tool context.
        triage_item_id: ID of the email_triage row.

    Returns:
        Dict with send status.
    """
    try:
        user_id = tool_context.state.get("user_id")
        client = _get_supabase()

        # Fetch the triage item
        item = (
            client.table("email_triage")
            .select("*")
            .eq("id", triage_item_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not item.data:
            return {"status": "error", "message": "Triage item not found"}

        triage = item.data
        if not triage.get("draft_reply"):
            return {"status": "error", "message": "No draft reply available"}

        # Send via Gmail using public credential helpers
        from app.integrations.google.client import get_google_credentials
        from app.integrations.google.gmail import GmailService

        provider_token = tool_context.state.get("google_provider_token")
        refresh_token = tool_context.state.get("google_refresh_token")
        if not provider_token:
            return {"status": "error", "message": "Google auth required", "auth_required": True}

        credentials = get_google_credentials(provider_token, refresh_token)
        gmail = GmailService(credentials)
        send_result = gmail.send_email(
            to=[triage["sender"]],
            subject=f"Re: {triage.get('subject', '')}",
            body=triage["draft_reply"],
        )

        if send_result.get("status") == "success":
            # Update triage status
            client.table("email_triage").update({
                "status": "sent",
                "user_action": "approved_draft",
                "acted_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", triage_item_id).execute()

        return send_result
    except Exception as e:
        return {"status": "error", "message": f"Failed to approve draft: {e}"}


def dismiss_item(
    tool_context: ToolContextType,
    triage_item_id: str,
) -> dict[str, Any]:
    """Dismiss a triage item (no action needed).

    Args:
        tool_context: Agent tool context.
        triage_item_id: ID of the email_triage row.

    Returns:
        Dict with status.
    """
    try:
        user_id = tool_context.state.get("user_id")
        client = _get_supabase()

        client.table("email_triage").update({
            "status": "dismissed",
            "user_action": "dismissed",
            "acted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", triage_item_id).eq("user_id", user_id).execute()

        return {"status": "success", "message": "Item dismissed"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to dismiss: {e}"}


def undo_auto_action(
    tool_context: ToolContextType,
    triage_item_id: str,
) -> dict[str, Any]:
    """Undo an auto-action (revert to pending).

    Args:
        tool_context: Agent tool context.
        triage_item_id: ID of the email_triage row.

    Returns:
        Dict with status.
    """
    try:
        user_id = tool_context.state.get("user_id")
        client = _get_supabase()

        client.table("email_triage").update({
            "status": "pending",
            "auto_action_taken": None,
            "user_action": "undone",
            "acted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", triage_item_id).eq("user_id", user_id).execute()

        return {"status": "success", "message": "Auto-action undone"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to undo: {e}"}


# Export
BRIEFING_TOOLS = [
    get_daily_briefing,
    refresh_briefing,
    approve_draft,
    dismiss_item,
    undo_auto_action,
]
```

- [x] **Step 4: Add triage endpoints to existing briefing router**

Add the following to `app/routers/briefing.py` after existing endpoints. Import `date` from `datetime` at the top:

```python
# --- Email Triage Briefing Endpoints ---

from pydantic import BaseModel as TriageBaseModel


class TriageActionRequest(TriageBaseModel):
    """Request body for triage item actions."""
    draft_text: Optional[str] = None


@router.get('/briefing/today')
@limiter.limit(get_user_persona_limit)
async def get_briefing_today(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Get today's email triage briefing grouped by section."""
    try:
        from datetime import date
        from app.services.supabase import get_service_client

        client = get_service_client()
        result = (
            client.table("email_triage")
            .select("*")
            .eq("user_id", user_id)
            .eq("briefing_date", date.today().isoformat())
            .order("received_at", desc=True)
            .execute()
        )

        items = result.data or []

        sections = {
            "urgent": [i for i in items if i["priority"] == "urgent" and i["status"] == "pending"],
            "needs_reply": [i for i in items if i["action_type"] == "needs_reply" and i["status"] == "pending" and i["priority"] != "urgent"],
            "auto_handled": [i for i in items if i["status"] == "auto_handled"],
            "fyi": [i for i in items if i["action_type"] == "fyi" and i["status"] == "pending"],
        }

        return {
            "sections": sections,
            "counts": {k: len(v) for k, v in sections.items()},
            "total": len(items),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/briefing/refresh')
@limiter.limit(get_user_persona_limit)
async def refresh_briefing(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Trigger an on-demand triage refresh for the current user."""
    try:
        from app.services.email_triage_worker import EmailTriageWorker
        from app.services.supabase import get_service_client

        client = get_service_client()

        # Get user preferences (or use defaults)
        prefs_result = (
            client.table("user_briefing_preferences")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        prefs = prefs_result.data[0] if prefs_result.data else {}

        worker = EmailTriageWorker(supabase_client=client)
        result = await worker.process_user(user_id, prefs)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/briefing/items/{item_id}/approve')
@limiter.limit(get_user_persona_limit)
async def approve_triage_item(
    item_id: str,
    request: Request,
    body: TriageActionRequest = None,
    user_id: str = Depends(get_current_user_id),
):
    """Approve and send a drafted reply."""
    try:
        from app.services.supabase import get_service_client

        client = get_service_client()

        # Get the triage item
        item_result = (
            client.table("email_triage")
            .select("*")
            .eq("id", item_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not item_result.data:
            raise HTTPException(status_code=404, detail="Triage item not found")

        triage = item_result.data
        draft_text = (body.draft_text if body and body.draft_text else triage.get("draft_reply"))

        if not draft_text:
            raise HTTPException(status_code=400, detail="No draft text available")

        # Update status to approved (actual send is async/separate)
        client.table("email_triage").update({
            "status": "approved",
            "draft_reply": draft_text,
            "user_action": "approved",
        }).eq("id", item_id).execute()

        return {"status": "approved", "item_id": item_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/briefing/items/{item_id}/dismiss')
@limiter.limit(get_user_persona_limit)
async def dismiss_triage_item(
    item_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Dismiss a triage item."""
    try:
        from app.services.supabase import get_service_client

        client = get_service_client()
        client.table("email_triage").update({
            "status": "dismissed",
            "user_action": "dismissed",
        }).eq("id", item_id).eq("user_id", user_id).execute()

        return {"status": "dismissed", "item_id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/briefing/items/{item_id}/undo')
@limiter.limit(get_user_persona_limit)
async def undo_triage_action(
    item_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Undo an auto-action or dismissal."""
    try:
        from app.services.supabase import get_service_client

        client = get_service_client()
        client.table("email_triage").update({
            "status": "pending",
            "auto_action_taken": None,
            "user_action": "undone",
        }).eq("id", item_id).eq("user_id", user_id).execute()

        return {"status": "undone", "item_id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/briefing/preferences')
@limiter.limit(get_user_persona_limit)
async def get_briefing_preferences(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Get user's briefing preferences."""
    try:
        from app.services.supabase import get_service_client

        client = get_service_client()
        result = (
            client.table("user_briefing_preferences")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        if result.data:
            return result.data[0]

        # Return defaults if no preferences set
        return {
            "briefing_time": "07:00",
            "timezone": "UTC",
            "email_digest_enabled": True,
            "email_digest_frequency": "daily",
            "auto_act_enabled": False,
            "auto_act_daily_cap": 10,
            "auto_act_categories": [],
            "vip_senders": [],
            "ignored_senders": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/briefing/preferences')
@limiter.limit(get_user_persona_limit)
async def update_briefing_preferences(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Update user's briefing preferences."""
    try:
        from app.services.supabase import get_service_client

        body = await request.json()
        body["user_id"] = user_id

        client = get_service_client()
        result = (
            client.table("user_briefing_preferences")
            .upsert(body, on_conflict="user_id")
            .execute()
        )

        return result.data[0] if result.data else body
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_briefing_tools.py -v`
Expected: All tests pass.

- [x] **Step 6: Commit**

```bash
git add app/agents/tools/briefing_tools.py app/routers/briefing.py tests/unit/test_briefing_tools.py
git commit -m "feat: add briefing API endpoints and ADK tools"
```

---

## Task 7: Wire Tools into ExecutiveAgent

**Files:**
- Modify: `app/agent.py`
- Modify: `app/agents/tools/registry.py`

- [x] **Step 1: Add tool imports to agent.py**

Add these imports near the other tool imports in `app/agent.py`:

```python
from app.agents.tools.gmail_inbox import GMAIL_INBOX_TOOLS
from app.agents.tools.briefing_tools import BRIEFING_TOOLS
```

Then add `*GMAIL_INBOX_TOOLS, *BRIEFING_TOOLS` to the tools list in the ExecutiveAgent definition (the list passed to `_sanitize()`).

- [x] **Step 2: Register tools in registry.py**

Add to the `TOOL_REGISTRY` dict in `app/agents/tools/registry.py`:

```python
# Gmail inbox tools
"read_inbox": read_inbox,
"read_email": read_email,
"classify_email": classify_email,
"archive_email": archive_email,
"label_email": label_email,
# Briefing tools
"get_daily_briefing": get_daily_briefing,
"refresh_briefing": refresh_briefing,
"approve_draft": approve_draft,
"dismiss_item": dismiss_item,
"undo_auto_action": undo_auto_action,
```

Add the corresponding imports at the top of registry.py:

```python
from app.agents.tools.gmail_inbox import read_inbox, read_email, classify_email, archive_email, label_email
from app.agents.tools.briefing_tools import get_daily_briefing, refresh_briefing, approve_draft, dismiss_item, undo_auto_action
```

- [x] **Step 3: Verify no import errors**

Run: `uv run python -c "from app.agent import executive_agent; print('OK')"`
Expected: "OK" with no errors.

- [x] **Step 4: Commit**

```bash
git add app/agent.py app/agents/tools/registry.py
git commit -m "feat: wire Gmail inbox and briefing tools into ExecutiveAgent"
```

---

## Task 8: Frontend OAuth Scope Update

**Files:**
- Modify: `frontend/src/services/auth.ts`

- [x] **Step 1: Update signInWithGoogle to request Gmail scopes and offline access**

In `frontend/src/services/auth.ts`, update the `signInWithOAuth` call to include:

```typescript
const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        scopes: 'email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar',
        queryParams: {
            access_type: 'offline',
            prompt: 'consent',
        },
    },
});
```

- [x] **Step 2: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [x] **Step 3: Commit**

```bash
git add frontend/src/services/auth.ts
git commit -m "feat: add Gmail read/modify scopes and offline access to OAuth flow"
```

---

## Task 9: Frontend Briefing API Client

**Files:**
- Create: `frontend/src/services/briefing.ts`

- [x] **Step 1: Create the API client**

```typescript
// frontend/src/services/briefing.ts
import { createClient } from '@/lib/supabase/client';

export interface TriageItem {
  id: string;
  gmail_message_id: string;
  sender: string;
  sender_name: string | null;
  subject: string | null;
  snippet: string | null;
  received_at: string | null;
  priority: 'urgent' | 'important' | 'normal' | 'low';
  action_type: 'needs_reply' | 'needs_review' | 'fyi' | 'auto_handle' | 'spam';
  category: string | null;
  confidence: number;
  classification_reasoning: string | null;
  draft_reply: string | null;
  draft_confidence: number | null;
  status: 'pending' | 'approved' | 'sent' | 'dismissed' | 'auto_handled';
  auto_action_taken: string | null;
  briefing_date: string;
}

export interface BriefingSections {
  urgent: TriageItem[];
  needs_reply: TriageItem[];
  auto_handled: TriageItem[];
  fyi: TriageItem[];
}

export interface BriefingResponse {
  sections: BriefingSections;
  counts: Record<string, number>;
  total: number;
}

export interface BriefingPreferences {
  briefing_time: string;
  timezone: string;
  email_digest_enabled: boolean;
  email_digest_frequency: 'daily' | 'weekdays' | 'off';
  auto_act_enabled: boolean;
  auto_act_daily_cap: number;
  auto_act_categories: string[];
  vip_senders: string[];
  ignored_senders: string[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${session.access_token}` };
}

export async function getBriefingToday(): Promise<BriefingResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/today`, { headers });
  if (!res.ok) throw new Error(`Failed to fetch briefing: ${res.statusText}`);
  return res.json();
}

export async function refreshBriefing(): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/refresh`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to refresh: ${res.statusText}`);
}

export async function approveTriageItem(itemId: string, draftText?: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/items/${itemId}/approve`, {
    method: 'PATCH',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft_text: draftText }),
  });
  if (!res.ok) throw new Error(`Failed to approve: ${res.statusText}`);
}

export async function dismissTriageItem(itemId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/items/${itemId}/dismiss`, {
    method: 'PATCH',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to dismiss: ${res.statusText}`);
}

export async function undoTriageAction(itemId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/items/${itemId}/undo`, {
    method: 'PATCH',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to undo: ${res.statusText}`);
}

export async function getBriefingPreferences(): Promise<BriefingPreferences> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/preferences`, { headers });
  if (!res.ok) throw new Error(`Failed to fetch preferences: ${res.statusText}`);
  return res.json();
}

export async function updateBriefingPreferences(prefs: Partial<BriefingPreferences>): Promise<BriefingPreferences> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/preferences`, {
    method: 'PUT',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(prefs),
  });
  if (!res.ok) throw new Error(`Failed to update preferences: ${res.statusText}`);
  return res.json();
}
```

- [x] **Step 2: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [x] **Step 3: Commit**

```bash
git add frontend/src/services/briefing.ts
git commit -m "feat: add briefing API client for frontend"
```

---

## Task 10: DailyBriefingWidget Component

**Files:**
- Create: `frontend/src/components/widgets/DailyBriefingWidget.tsx`
- Modify: `frontend/src/components/widgets/WidgetRegistry.tsx`

- [x] **Step 1: Create the DailyBriefingWidget**

This is a large component. Create `frontend/src/components/widgets/DailyBriefingWidget.tsx` with:

1. **Header:** Greeting, date, freshness indicator, refresh button, quick stat badges
2. **Urgent/Needs Reply section:** Cards with sender, subject, snippet, priority badge. Expandable with draft reply textarea + Approve/Edit/Dismiss buttons.
3. **Auto-Handled section:** Collapsible log of auto-actions with undo buttons.
4. **FYI section:** Collapsible summary list with "mark all read."
5. **Real-time:** Supabase realtime subscription on `email_triage` table for live updates.
6. **Empty state:** "Inbox zero" message.

Use the existing widget pattern: accept `WidgetDefinition` prop, use Tailwind dark mode classes, import icons from `lucide-react`.

Use the `briefing.ts` API client for all data fetching and actions.

Key implementation notes:
- Use `useState` for sections data, `useEffect` for initial fetch
- Use `useCallback` for action handlers (approve, dismiss, undo)
- Optimistic updates: remove card from UI before API completes
- Keyboard shortcuts via `useEffect` with `keydown` listener: `j/k` navigate, `a` approve, `e` edit, `d` dismiss

- [x] **Step 2: Register in WidgetRegistry**

In `frontend/src/components/widgets/WidgetRegistry.tsx`, add:

```typescript
const DailyBriefingWidget = dynamic(() => import('./DailyBriefingWidget'), {
  loading: () => <WidgetSkeleton />,
  ssr: false,
});
```

Add to the registry mapping:

```typescript
'daily_briefing': DailyBriefingWidget,
```

- [x] **Step 3: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [x] **Step 4: Commit**

```bash
git add frontend/src/components/widgets/DailyBriefingWidget.tsx frontend/src/components/widgets/WidgetRegistry.tsx
git commit -m "feat: add DailyBriefingWidget with approval flow and realtime updates"
```

---

## Task 11: NotificationCenter Component

**Files:**
- Create: `frontend/src/components/NotificationCenter.tsx`

- [x] **Step 1: Create the NotificationCenter**

Build `frontend/src/components/NotificationCenter.tsx`:

1. **Bell icon** with unread count badge (red dot with number)
2. **Dropdown panel** on click: list of recent notifications
3. **Each notification:** icon (based on type), title, message, timestamp, optional action button
4. **Actions:** "Mark all read", individual dismiss
5. **Realtime:** Supabase subscription on `notifications` table for live updates
6. Use existing `notifications` table — no new API needed, query directly via Supabase client

Pattern: `useState` for notifications array + `isOpen` toggle. `useEffect` for initial fetch + realtime subscription. Click-outside handler to close dropdown.

- [x] **Step 2: Add to navigation layout**

Find the main nav/header component (likely in `frontend/src/app/(personas)/layout.tsx` or a shared header component) and add `<NotificationCenter />` to the right side of the nav bar.

- [x] **Step 3: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [x] **Step 4: Commit**

```bash
git add frontend/src/components/NotificationCenter.tsx
git commit -m "feat: add NotificationCenter with bell icon and realtime updates"
```

---

## Task 12: Briefing Preferences Settings Page

**Files:**
- Create: `frontend/src/app/settings/briefing/page.tsx`

- [x] **Step 1: Create the settings page**

Build a form page with controls for:
- **Briefing time:** Time picker (default 07:00)
- **Timezone:** Dropdown selector
- **Email digest:** Toggle + frequency selector (daily/weekdays/off)
- **Auto-act:** Toggle with warning text about shadow mode, daily cap slider (1-50)
- **Auto-act categories:** Multi-select checkboxes for category types
- **VIP senders:** Tag input for adding/removing VIP email addresses
- **Ignored senders:** Tag input for adding/removing ignored addresses

Use `getBriefingPreferences()` and `updateBriefingPreferences()` from the API client. Show success toast on save.

- [x] **Step 2: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [x] **Step 3: Commit**

```bash
git add frontend/src/app/settings/briefing/page.tsx
git commit -m "feat: add briefing preferences settings page"
```

---

## Task 13: Integration Testing & Polish

**Files:**
- Multiple files — end-to-end verification

- [x] **Step 1: Run full backend test suite**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All existing + new tests pass.

- [x] **Step 2: Run linting**

Run: `uv run ruff check app/ --fix && uv run ruff format app/`
Expected: No errors.

- [x] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Clean build.

- [x] **Step 4: Run type checking**

Run: `uv run ty check .`
Expected: No type errors in new files.

- [x] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: fix lint and type issues from daily briefing implementation"
```

---

## Dependency Graph

```
Task 1 (Migrations)
    ↓
Task 2 (Gmail Reader) → Task 3 (Inbox Tools)
    ↓                        ↓
Task 4 (Triage Service) → Task 5 (Worker)
    ↓                        ↓
Task 6 (Briefing API + Tools) → Task 7 (Wire into Agent)
    ↓
Task 8 (OAuth Scopes)
    ↓
Task 9 (API Client) → Task 10 (Briefing Widget)
                     → Task 11 (NotificationCenter)
                     → Task 12 (Settings Page)
    ↓
Task 13 (Integration Testing)
```

Tasks 10, 11, 12 can run in parallel once Task 9 is complete.

---

## Deferred to Next Iteration

These spec items are intentionally deferred to keep the initial implementation focused:

- **`GET /briefing/history`** — Past briefings endpoint. Low priority for MVP; users need today's briefing first.
- **`briefing_digest_service.py`** — Email digest delivery at user's configured time. Requires Cloud Scheduler cron per-user timing, which is a separate infrastructure concern. Ship after the core widget proves valuable.
- **Re-authorization banner** — UI banner for users with stale OAuth scopes. Ship after OAuth flow is tested with real users; the `prompt: 'consent'` flow handles most cases for new signups.
