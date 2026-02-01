# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Docs tools for agents.

Provides tools for creating and managing documents.
"""

from typing import Any

# Tool context type
ToolContextType = Any


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
