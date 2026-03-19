# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Gmail inbox ADK tools."""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.tools.gmail_inbox import (
    archive_email,
    label_email,
    read_email,
    read_inbox,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_tool_context():
    """Provide a mock ADK tool context with Google tokens set."""
    ctx = MagicMock()
    ctx.state = {
        "google_provider_token": "test-access-token",
        "google_refresh_token": "test-refresh-token",
        "user_id": "user-123",
    }
    return ctx


@pytest.fixture()
def mock_tool_context_no_token():
    """Provide a mock ADK tool context with no Google tokens."""
    ctx = MagicMock()
    ctx.state = {}
    return ctx


@pytest.fixture()
def mock_reader():
    """Provide a mock GmailReader instance."""
    return MagicMock()


# ---------------------------------------------------------------------------
# TestReadInbox
# ---------------------------------------------------------------------------


class TestReadInbox:
    """Tests for the read_inbox tool."""

    def test_returns_emails_on_success(self, mock_tool_context, mock_reader):
        """read_inbox returns list of emails with metadata on success."""
        mock_reader.list_messages.return_value = {
            "status": "success",
            "messages": [
                {"id": "msg1", "threadId": "t1"},
                {"id": "msg2", "threadId": "t2"},
            ],
            "count": 2,
        }
        mock_reader.get_message.side_effect = [
            {
                "status": "success",
                "message": {
                    "id": "msg1",
                    "subject": "Hello",
                    "sender": "alice@example.com",
                    "snippet": "Hi there",
                    "received_at": "2026-03-19",
                },
            },
            {
                "status": "success",
                "message": {
                    "id": "msg2",
                    "subject": "World",
                    "sender": "bob@example.com",
                    "snippet": "Hey",
                    "received_at": "2026-03-19",
                },
            },
        ]

        with patch(
            "app.agents.tools.gmail_inbox._get_gmail_reader",
            return_value=mock_reader,
        ):
            result = read_inbox(mock_tool_context, max_results=20, query="is:unread")

        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["emails"]) == 2
        assert result["emails"][0]["id"] == "msg1"

    def test_auth_error_when_no_tokens(self, mock_tool_context_no_token):
        """read_inbox returns auth_required error when no Google token is present."""
        result = read_inbox(mock_tool_context_no_token)

        assert result["status"] == "error"
        assert result.get("auth_required") is True

    def test_returns_empty_list_for_empty_inbox(self, mock_tool_context, mock_reader):
        """read_inbox returns empty emails list when inbox has no matching messages."""
        mock_reader.list_messages.return_value = {
            "status": "success",
            "messages": [],
            "count": 0,
        }

        with patch(
            "app.agents.tools.gmail_inbox._get_gmail_reader",
            return_value=mock_reader,
        ):
            result = read_inbox(mock_tool_context, max_results=10)

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["emails"] == []

    def test_propagates_list_error(self, mock_tool_context, mock_reader):
        """read_inbox returns error dict when the reader raises an unexpected exception."""
        mock_reader.list_messages.side_effect = RuntimeError("API down")

        with patch(
            "app.agents.tools.gmail_inbox._get_gmail_reader",
            return_value=mock_reader,
        ):
            result = read_inbox(mock_tool_context)

        assert result["status"] == "error"
        assert "Failed to read inbox" in result["message"]


# ---------------------------------------------------------------------------
# TestReadEmail
# ---------------------------------------------------------------------------


class TestReadEmail:
    """Tests for the read_email tool."""

    def test_returns_full_message(self, mock_tool_context, mock_reader):
        """read_email returns full message content for a given message ID."""
        mock_reader.get_message.return_value = {
            "status": "success",
            "message": {
                "id": "msg42",
                "subject": "Important",
                "sender": "boss@corp.com",
                "body": "Please review this.",
                "snippet": "Please review",
                "labels": ["INBOX"],
                "received_at": "2026-03-19",
            },
        }

        with patch(
            "app.agents.tools.gmail_inbox._get_gmail_reader",
            return_value=mock_reader,
        ):
            result = read_email(mock_tool_context, message_id="msg42")

        assert result["status"] == "success"
        assert result["message"]["id"] == "msg42"
        assert result["message"]["sender"] == "boss@corp.com"
        mock_reader.get_message.assert_called_once_with("msg42", msg_format="full")

    def test_auth_error_when_no_tokens(self, mock_tool_context_no_token):
        """read_email returns auth_required error when no Google token is present."""
        result = read_email(mock_tool_context_no_token, message_id="msg1")

        assert result["status"] == "error"
        assert result.get("auth_required") is True

    def test_propagates_reader_error(self, mock_tool_context, mock_reader):
        """read_email returns error dict when the reader raises an unexpected exception."""
        mock_reader.get_message.side_effect = RuntimeError("network error")

        with patch(
            "app.agents.tools.gmail_inbox._get_gmail_reader",
            return_value=mock_reader,
        ):
            result = read_email(mock_tool_context, message_id="msg1")

        assert result["status"] == "error"
        assert "Failed to read email" in result["message"]


# ---------------------------------------------------------------------------
# TestArchiveEmail
# ---------------------------------------------------------------------------


class TestArchiveEmail:
    """Tests for the archive_email tool."""

    def test_removes_inbox_and_unread_labels(self, mock_tool_context, mock_reader):
        """archive_email calls modify_message removing INBOX and UNREAD."""
        mock_reader.modify_message.return_value = {
            "status": "success",
            "message_id": "msg99",
            "labels": [],
        }

        with patch(
            "app.agents.tools.gmail_inbox._get_gmail_reader",
            return_value=mock_reader,
        ):
            result = archive_email(mock_tool_context, message_id="msg99")

        assert result["status"] == "success"
        mock_reader.modify_message.assert_called_once_with(
            "msg99",
            remove_labels=["INBOX", "UNREAD"],
        )

    def test_auth_error_when_no_tokens(self, mock_tool_context_no_token):
        """archive_email returns auth_required error when no Google token is present."""
        result = archive_email(mock_tool_context_no_token, message_id="msg1")

        assert result["status"] == "error"
        assert result.get("auth_required") is True

    def test_propagates_modify_error(self, mock_tool_context, mock_reader):
        """archive_email returns error dict when the reader raises an unexpected exception."""
        mock_reader.modify_message.side_effect = RuntimeError("timeout")

        with patch(
            "app.agents.tools.gmail_inbox._get_gmail_reader",
            return_value=mock_reader,
        ):
            result = archive_email(mock_tool_context, message_id="msg1")

        assert result["status"] == "error"
        assert "Failed to archive email" in result["message"]


# ---------------------------------------------------------------------------
# TestLabelEmail
# ---------------------------------------------------------------------------


class TestLabelEmail:
    """Tests for the label_email tool."""

    def test_adds_and_removes_labels(self, mock_tool_context, mock_reader):
        """label_email passes add_labels and remove_labels to modify_message."""
        mock_reader.modify_message.return_value = {
            "status": "success",
            "message_id": "msg5",
            "labels": ["STARRED"],
        }

        with patch(
            "app.agents.tools.gmail_inbox._get_gmail_reader",
            return_value=mock_reader,
        ):
            result = label_email(
                mock_tool_context,
                message_id="msg5",
                add_labels=["STARRED"],
                remove_labels=["UNREAD"],
            )

        assert result["status"] == "success"
        mock_reader.modify_message.assert_called_once_with(
            "msg5",
            add_labels=["STARRED"],
            remove_labels=["UNREAD"],
        )

    def test_auth_error_when_no_tokens(self, mock_tool_context_no_token):
        """label_email returns auth_required error when no Google token is present."""
        result = label_email(mock_tool_context_no_token, message_id="msg1")

        assert result["status"] == "error"
        assert result.get("auth_required") is True
