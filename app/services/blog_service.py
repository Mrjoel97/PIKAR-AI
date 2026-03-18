"""BlogService - CRUD operations for blog posts.

This service provides Create, Read, Update, Delete operations for blog posts
stored in the blog_posts table in Supabase with proper RLS authentication.
Used by MarketingAutomationAgent and ContentAgent.
"""

import re
from typing import Optional
from app.services.base_service import BaseService, AdminService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def _estimate_reading_time(content: str) -> int:
    """Estimate reading time in minutes (avg 200 wpm)."""
    words = len(content.split())
    return max(1, round(words / 200))


class BlogService(BaseService):
    """Service for managing blog posts.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize the blog service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "blog_posts"

    async def create_blog_post(
        self,
        title: str,
        content: str = "",
        excerpt: str = None,
        category: str = None,
        tags: list[str] = None,
        seo_metadata: dict = None,
        featured_image_url: str = None,
        campaign_id: str = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Create a new blog post.

        Args:
            title: Blog post title.
            content: Blog post body (markdown or HTML).
            excerpt: Short summary for previews.
            category: Blog category.
            tags: List of tags.
            seo_metadata: SEO metadata dict (meta_title, meta_description, keywords, focus_keyword).
            featured_image_url: URL to featured image.
            campaign_id: Optional campaign this post belongs to.
            user_id: Optional user ID override.

        Returns:
            The created blog post record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for blog post creation")

        word_count = len(content.split()) if content else 0
        slug = _slugify(title)

        data = {
            "user_id": effective_user_id,
            "title": title,
            "slug": slug,
            "content": content,
            "excerpt": excerpt,
            "category": category,
            "tags": tags or [],
            "seo_metadata": seo_metadata or {},
            "featured_image_url": featured_image_url,
            "campaign_id": campaign_id,
            "word_count": word_count,
            "reading_time_minutes": _estimate_reading_time(content) if content else 0,
            "status": "draft",
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._table_name).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_blog_post(self, post_id: str, user_id: Optional[str] = None) -> dict:
        """Retrieve a blog post by ID.

        Args:
            post_id: The unique blog post ID.
            user_id: Optional user ID override.

        Returns:
            The blog post record.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*").eq("id", post_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_blog_post(
        self,
        post_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        excerpt: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        seo_metadata: Optional[dict] = None,
        featured_image_url: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Update a blog post.

        Args:
            post_id: The unique blog post ID.
            title: New title.
            content: New content body.
            excerpt: New excerpt.
            category: New category.
            tags: New tags list.
            seo_metadata: New SEO metadata.
            featured_image_url: New featured image URL.
            status: New status (draft, review, scheduled, published, archived).
            user_id: Optional user ID override.

        Returns:
            The updated blog post record.
        """
        update_data = {}
        if title is not None:
            update_data["title"] = title
            update_data["slug"] = _slugify(title)
        if content is not None:
            update_data["content"] = content
            update_data["word_count"] = len(content.split())
            update_data["reading_time_minutes"] = _estimate_reading_time(content)
        if excerpt is not None:
            update_data["excerpt"] = excerpt
        if category is not None:
            update_data["category"] = category
        if tags is not None:
            update_data["tags"] = tags
        if seo_metadata is not None:
            update_data["seo_metadata"] = seo_metadata
        if featured_image_url is not None:
            update_data["featured_image_url"] = featured_image_url
        if status is not None:
            update_data["status"] = status

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).update(update_data).eq("id", post_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def publish_blog_post(self, post_id: str, user_id: Optional[str] = None) -> dict:
        """Publish a blog post (sets status and published_at).

        Args:
            post_id: The unique blog post ID.
            user_id: Optional user ID override.

        Returns:
            The published blog post record.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._table_name)
            .update({"status": "published", "published_at": "now()"})
            .eq("id", post_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from publish")

    async def list_blog_posts(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        campaign_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> list:
        """List blog posts with optional filters.

        Args:
            status: Filter by status.
            category: Filter by category.
            campaign_id: Filter by campaign.
            user_id: Filter by user.
            limit: Maximum results (default 50).

        Returns:
            List of blog post records.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*")

        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)
        if campaign_id:
            query = query.eq("campaign_id", campaign_id)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("created_at", desc=True).limit(limit))
        return response.data

    async def delete_blog_post(self, post_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a blog post.

        Args:
            post_id: The unique blog post ID.
            user_id: Optional user ID override.

        Returns:
            True if deletion was successful.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).delete().eq("id", post_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        return len(response.data) > 0
