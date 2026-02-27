# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Docs tools for agents.

Provides tools for creating and managing documents.
"""

import os
import logging
from typing import Any, Optional

# Tool context type
ToolContextType = Any

logger = logging.getLogger(__name__)


def _get_docs_service(tool_context: ToolContextType):
    """Get Docs service from tool context credentials."""
    from app.integrations.google.docs import GoogleDocsService
    from app.integrations.google.client import get_google_credentials
    
    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")
    
    if not provider_token:
        raise ValueError("Google authentication required for document features.")
    
    credentials = get_google_credentials(provider_token, refresh_token)
    return GoogleDocsService(credentials)


def _track_created_doc(
    user_id: Optional[str],
    agent_id: Optional[str],
    doc_id: str,
    title: str,
    doc_url: str,
    doc_type: str = "document",
    metadata: Optional[dict] = None,
) -> None:
    """Track a created Google Doc in the database.
    
    Saves the document reference to agent_google_docs table for display
    in the Knowledge Vault.
    """
    try:
        from app.services.supabase import get_service_client
        
        if not user_id:
            logger.warning("Cannot track doc: missing user_id")
            return
        
        client = get_service_client()
        client.table("agent_google_docs").insert({
            "user_id": user_id,
            "agent_id": agent_id,
            "doc_id": doc_id,
            "title": title,
            "doc_url": doc_url,
            "doc_type": doc_type,
            "metadata": metadata or {},
        }).execute()
        
        logger.info(f"Tracked Google Doc: {title} ({doc_id}) for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to track created doc: {e}")


def create_document(
    tool_context: ToolContextType,
    title: str,
    content: str | None = None,
) -> dict[str, Any]:
    """Create a new Google Doc.
    
    Args:
        tool_context: Agent tool context.
        title: Document title.
        content: Optional initial content.
        
    Returns:
        Dict with document ID and URL.
    """
    try:
        service = _get_docs_service(tool_context)
        doc = service.create_document(title, content)
        
        # Track the created document for the Knowledge Vault
        user_id = tool_context.state.get("user_id")
        agent_id = tool_context.state.get("agent_id")
        _track_created_doc(
            user_id=user_id,
            agent_id=agent_id,
            doc_id=doc.id,
            title=doc.title,
            doc_url=doc.url,
            doc_type="document",
        )
        
        return {
            "status": "success",
            "message": f"Document '{title}' created",
            "document": {
                "id": doc.id,
                "title": doc.title,
                "url": doc.url,
            },
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to create document: {e}"}


def create_report_doc(
    tool_context: ToolContextType,
    title: str,
    sections: list[dict[str, str]],
) -> dict[str, Any]:
    """Create a formatted report as a Google Doc.
    
    Use this for written reports, proposals, and formal documents.
    
    Args:
        tool_context: Agent tool context.
        title: Document title.
        sections: List of sections, each with 'heading' and 'content'.
            Example: [{"heading": "Summary", "content": "..."}]
        
    Returns:
        Dict with document details.
    """
    try:
        service = _get_docs_service(tool_context)
        doc = service.create_report_document(title, sections)
        
        # Track the created document for the Knowledge Vault
        user_id = tool_context.state.get("user_id")
        agent_id = tool_context.state.get("agent_id")
        _track_created_doc(
            user_id=user_id,
            agent_id=agent_id,
            doc_id=doc.id,
            title=doc.title,
            doc_url=doc.url,
            doc_type="report",
            metadata={"sections": len(sections)},
        )
        
        return {
            "status": "success",
            "message": f"Report document created with {len(sections)} sections",
            "document": {
                "id": doc.id,
                "title": doc.title,
                "url": doc.url,
            },
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to create report: {e}"}


def append_to_document(
    tool_context: ToolContextType,
    document_id: str,
    text: str,
) -> dict[str, Any]:
    """Append text to an existing Google Doc.
    
    Args:
        tool_context: Agent tool context.
        document_id: The document ID.
        text: Text to append.
        
    Returns:
        Dict with status.
    """
    try:
        service = _get_docs_service(tool_context)
        service.append_text(document_id, text)
        
        return {
            "status": "success",
            "message": "Text appended to document",
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to append text: {e}"}


# Export Docs tools
DOCS_TOOLS = [
    create_document,
    create_report_doc,
    append_to_document,
]
