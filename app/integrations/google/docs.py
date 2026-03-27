# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Google Docs service for document creation.

Enables agents to create and edit Google Docs documents.
"""

from dataclasses import dataclass
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build


@dataclass
class DocumentInfo:
    """Information about a Google Doc."""

    id: str
    title: str
    url: str


class GoogleDocsService:
    """Service for Google Docs operations.

    Provides methods for:
    - Creating documents
    - Adding content
    - Basic formatting
    """

    def __init__(self, credentials: Credentials):
        """Initialize with Google OAuth credentials."""
        self.credentials = credentials
        self._docs_service: Resource | None = None
        self._drive_service: Resource | None = None

    @property
    def docs(self) -> Resource:
        """Lazy-load Docs API service."""
        if self._docs_service is None:
            self._docs_service = build("docs", "v1", credentials=self.credentials)
        return self._docs_service

    @property
    def drive(self) -> Resource:
        """Lazy-load Drive API for file operations."""
        if self._drive_service is None:
            self._drive_service = build("drive", "v3", credentials=self.credentials)
        return self._drive_service

    def create_document(
        self,
        title: str,
        content: str | None = None,
    ) -> DocumentInfo:
        """Create a new Google Doc.

        Args:
            title: Document title.
            content: Optional initial content.

        Returns:
            DocumentInfo with ID and URL.
        """
        # Create the document
        doc = self.docs.documents().create(body={"title": title}).execute()
        doc_id = doc.get("documentId")

        # Add content if provided
        if content:
            self.append_text(doc_id, content)

        return DocumentInfo(
            id=doc_id,
            title=title,
            url=f"https://docs.google.com/document/d/{doc_id}/edit",
        )

    def get_document(self, document_id: str) -> dict[str, Any]:
        """Get document metadata and content.

        Args:
            document_id: The document ID.

        Returns:
            Document details.
        """
        doc = self.docs.documents().get(documentId=document_id).execute()
        return doc

    def append_text(
        self,
        document_id: str,
        text: str,
    ) -> None:
        """Append text to the end of a document.

        Args:
            document_id: The document ID.
            text: Text to append.
        """
        # Get current document to find end index
        doc = self.get_document(document_id)
        end_index = doc.get("body", {}).get("content", [{}])[-1].get("endIndex", 1) - 1

        requests = [
            {
                "insertText": {
                    "location": {"index": max(1, end_index)},
                    "text": text,
                }
            }
        ]

        self.docs.documents().batchUpdate(
            documentId=document_id,
            body={"requests": requests},
        ).execute()

    def create_report_document(
        self,
        title: str,
        sections: list[dict[str, str]],
    ) -> DocumentInfo:
        """Create a formatted report document.

        Args:
            title: Document title.
            sections: List of dicts with 'heading' and 'content'.

        Returns:
            Created document info.
        """
        # Build content
        content_parts = []
        for section in sections:
            heading = section.get("heading", "")
            text = section.get("content", "")
            content_parts.append(f"\n\n{heading}\n\n{text}")

        full_content = "".join(content_parts)

        return self.create_document(title, full_content)


def get_docs_service(credentials: Credentials) -> GoogleDocsService:
    """Get Docs service instance."""
    return GoogleDocsService(credentials)
