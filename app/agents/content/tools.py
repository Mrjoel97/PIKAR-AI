# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for the Content Creation Agent."""


def search_knowledge(query: str) -> dict:
    """Search business knowledge base for relevant information.

    Args:
        query: The search query to find relevant business knowledge.

    Returns:
        Dictionary containing search results.
    """
    try:
        from app.rag.knowledge_vault import search_knowledge as kb_search

        return kb_search(query, top_k=3)
    except Exception:
        return {"results": []}


async def save_content(title: str, content: str) -> dict:
    """Save generated content to the Knowledge Vault via ContentService.

    Args:
        title: Title of the content.
        content: The text content to save.

    Returns:
        Dictionary confirming save status.
    """
    from app.services.content_service import ContentService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentService()
        result = await service.save_content(
            title, content, agent_id="content-agent", user_id=get_current_user_id()
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_content(content_id: str) -> dict:
    """Retrieve saved content by its ID.

    Args:
        content_id: The unique ID of the content.

    Returns:
        Dictionary containing the content record.
    """
    from app.services.content_service import ContentService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentService()
        result = await service.get_content(content_id, user_id=get_current_user_id())
        return {"success": True, "content": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_content(
    content_id: str, title: str = None, content: str = None
) -> dict:
    """Update existing content.

    Args:
        content_id: The unique ID of the content.
        title: New title (optional).
        content: New content text (optional).

    Returns:
        Dictionary with updated content.
    """
    from app.services.content_service import ContentService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentService()
        result = await service.update_content(
            content_id, title=title, content=content, user_id=get_current_user_id()
        )
        return {"success": True, "content": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_content(content_type: str = None) -> dict:
    """List saved content items.

    Args:
        content_type: Optional filter by type (e.g., 'blog', 'social').

    Returns:
        Dictionary with list of content items.
    """
    from app.services.content_service import ContentService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentService()
        items = await service.list_content(
            content_type=content_type, user_id=get_current_user_id()
        )
        return {"success": True, "items": items, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e), "items": []}
