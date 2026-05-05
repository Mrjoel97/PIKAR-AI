# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for GoogleDocsService.read_doc_content + replace_section.

The Google Docs API client is fully mocked; no network calls.
"""

from unittest.mock import MagicMock

import pytest

from app.integrations.google.docs import GoogleDocsService


def _build_service_with_doc(doc_payload: dict) -> GoogleDocsService:
    """Return a GoogleDocsService with a mocked _docs_service.

    The mock chain mirrors `service.docs.documents().get(...).execute()`
    and `service.docs.documents().batchUpdate(...).execute()`.
    """
    service = GoogleDocsService(MagicMock())

    docs_service = MagicMock()
    documents = MagicMock()
    docs_service.documents.return_value = documents

    get_call = MagicMock()
    get_call.execute.return_value = doc_payload
    documents.get.return_value = get_call

    batch_update_call = MagicMock()
    batch_update_call.execute.return_value = {"replies": []}
    documents.batchUpdate.return_value = batch_update_call

    service._docs_service = docs_service
    return service


def test_read_doc_content_concatenates_text_runs() -> None:
    """read_doc_content joins every textRun.content in body order."""
    doc_payload = {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Hello "}},
                            {"textRun": {"content": "world."}},
                        ]
                    }
                }
            ]
        }
    }
    service = _build_service_with_doc(doc_payload)

    assert service.read_doc_content("doc-1") == "Hello world."


def test_replace_section_raises_when_anchor_missing() -> None:
    """replace_section raises ValueError if no heading matches anchor."""
    doc_payload = {
        "body": {
            "content": [
                {
                    "startIndex": 1,
                    "endIndex": 20,
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "elements": [
                            {"textRun": {"content": "Just a paragraph.\n"}},
                        ],
                    },
                }
            ]
        }
    }
    service = _build_service_with_doc(doc_payload)

    with pytest.raises(ValueError, match="Anchor heading"):
        service.replace_section("doc-1", "Missing Heading", "new body")
