# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for GmailReader service."""

import base64
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from google.oauth2.credentials import Credentials

from app.integrations.google.gmail_reader import GmailReader, get_gmail_reader


@pytest.fixture
def mock_credentials():
    """Provide mock Google OAuth credentials."""
    creds = MagicMock(spec=Credentials)
    return creds


@pytest.fixture
def reader(mock_credentials):
    """Provide a GmailReader with a mocked Gmail service."""
    instance = GmailReader(mock_credentials)
    mock_service = MagicMock()
    instance._service = mock_service
    return instance


# ---------------------------------------------------------------------------
# TestListMessages
# ---------------------------------------------------------------------------


class TestListMessages:
    """Tests for GmailReader.list_messages."""

    def test_list_unread_messages(self, reader):
        """list_messages returns success with messages and count."""
        mock_response = {
            "messages": [{"id": "msg1", "threadId": "t1"}, {"id": "msg2", "threadId": "t2"}],
            "resultSizeEstimate": 2,
        }
        (
            reader._service.users.return_value
            .messages.return_value
            .list.return_value
            .execute.return_value
        ) = mock_response

        result = reader.list_messages(query="is:unread", max_results=50)

        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["messages"]) == 2
        assert result["messages"][0]["id"] == "msg1"

    def test_empty_inbox(self, reader):
        """list_messages returns success with empty list for empty inbox."""
        mock_response = {"resultSizeEstimate": 0}
        (
            reader._service.users.return_value
            .messages.return_value
            .list.return_value
            .execute.return_value
        ) = mock_response

        result = reader.list_messages(query="is:unread", max_results=50)

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["messages"] == []


# ---------------------------------------------------------------------------
# TestGetMessage
# ---------------------------------------------------------------------------


def _make_base64_body(text: str) -> str:
    """Encode plain text as urlsafe base64 for use in mock payloads."""
    return base64.urlsafe_b64encode(text.encode()).decode()


class TestGetMessage:
    """Tests for GmailReader.get_message."""

    def test_parse_sender_subject_body(self, reader):
        """get_message correctly parses headers, body, and metadata."""
        raw_body = _make_base64_body("Hello, this is the email body.")
        mock_msg = {
            "id": "msg1",
            "threadId": "t1",
            "snippet": "Hello, this is the email body.",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Jane Doe <jane@example.com>"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Thu, 19 Mar 2026 10:00:00 +0000"},
                ],
                "mimeType": "text/plain",
                "body": {"data": raw_body},
            },
        }
        (
            reader._service.users.return_value
            .messages.return_value
            .get.return_value
            .execute.return_value
        ) = mock_msg

        result = reader.get_message("msg1")

        assert result["status"] == "success"
        msg = result["message"]
        assert msg["id"] == "msg1"
        assert msg["sender"] == "jane@example.com"
        assert msg["sender_name"] == "Jane Doe"
        assert msg["subject"] == "Test Subject"
        assert "Hello, this is the email body." in msg["body"]
        assert msg["snippet"] == "Hello, this is the email body."
        assert "UNREAD" in msg["labels"]

    def test_not_found_error(self, reader):
        """get_message returns error dict when API raises HttpError."""
        from googleapiclient.errors import HttpError
        import httplib2

        resp = httplib2.Response({"status": "404"})
        resp.reason = "Not Found"
        (
            reader._service.users.return_value
            .messages.return_value
            .get.return_value
            .execute.side_effect
        ) = HttpError(resp=resp, content=b"Not Found")

        result = reader.get_message("nonexistent")

        assert result["status"] == "error"
        assert "message_id" in result


# ---------------------------------------------------------------------------
# TestModifyMessage
# ---------------------------------------------------------------------------


class TestModifyMessage:
    """Tests for GmailReader.modify_message."""

    def test_archive_removes_inbox(self, reader):
        """modify_message correctly calls API to remove INBOX label."""
        mock_response = {"id": "msg1", "labelIds": ["UNREAD"]}
        (
            reader._service.users.return_value
            .messages.return_value
            .modify.return_value
            .execute.return_value
        ) = mock_response

        result = reader.modify_message("msg1", remove_labels=["INBOX"])

        assert result["status"] == "success"
        assert result["message_id"] == "msg1"
        # Verify the API was called with the correct body
        reader._service.users.return_value.messages.return_value.modify.assert_called_once_with(
            userId="me",
            id="msg1",
            body={"addLabelIds": [], "removeLabelIds": ["INBOX"]},
        )

    def test_mark_read_removes_unread(self, reader):
        """modify_message correctly calls API to remove UNREAD label."""
        mock_response = {"id": "msg1", "labelIds": ["INBOX"]}
        (
            reader._service.users.return_value
            .messages.return_value
            .modify.return_value
            .execute.return_value
        ) = mock_response

        result = reader.modify_message("msg1", remove_labels=["UNREAD"])

        assert result["status"] == "success"
        reader._service.users.return_value.messages.return_value.modify.assert_called_once_with(
            userId="me",
            id="msg1",
            body={"addLabelIds": [], "removeLabelIds": ["UNREAD"]},
        )


# ---------------------------------------------------------------------------
# TestParseHelper
# ---------------------------------------------------------------------------


class TestParseHelper:
    """Tests for GmailReader._parse_sender helper."""

    def test_parse_name_and_email(self, reader):
        """_parse_sender splits 'Name <email>' correctly."""
        name, email = reader._parse_sender("Jane Doe <jane@example.com>")
        assert name == "Jane Doe"
        assert email == "jane@example.com"

    def test_parse_bare_email(self, reader):
        """_parse_sender returns empty name for bare email address."""
        name, email = reader._parse_sender("jane@example.com")
        assert name == ""
        assert email == "jane@example.com"


# ---------------------------------------------------------------------------
# TestFactory
# ---------------------------------------------------------------------------


def test_get_gmail_reader_returns_instance(mock_credentials):
    """get_gmail_reader factory returns a GmailReader instance."""
    instance = get_gmail_reader(mock_credentials)
    assert isinstance(instance, GmailReader)
    assert instance.credentials is mock_credentials
