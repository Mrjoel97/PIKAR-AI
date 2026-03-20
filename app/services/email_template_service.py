"""EmailTemplateService - CRUD operations for email templates.

This service provides Create, Read, Update, Delete operations for email
templates stored in the email_templates table in Supabase.
Used by MarketingAutomationAgent for email campaign creation.
"""

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class EmailTemplateService(BaseService):
    """Service for managing email templates.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the email template service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "email_templates"

    async def create_template(
        self,
        name: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        category: str = "general",
        variables: list[str] = None,
        ab_variants: list[dict] = None,
        campaign_id: str = None,
        metadata: dict = None,
        user_id: str | None = None,
    ) -> dict:
        """Create a new email template.

        Args:
            name: Template name.
            subject: Email subject line.
            body_html: HTML email body.
            body_text: Plain text fallback.
            category: Template category (welcome, nurture, promotional, etc.).
            variables: List of placeholder variable names (e.g., ['first_name', 'company']).
            ab_variants: A/B test variants [{variant_name, subject, body_html, body_text}].
            campaign_id: Optional campaign this template belongs to.
            metadata: Additional metadata (tone, audience_segment, preview_text).
            user_id: Optional user ID override.

        Returns:
            The created email template record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for email template creation")

        data = {
            "user_id": effective_user_id,
            "name": name,
            "subject": subject,
            "body_html": body_html,
            "body_text": body_text or "",
            "category": category,
            "variables": variables or [],
            "ab_variants": ab_variants or [],
            "campaign_id": campaign_id,
            "metadata": metadata or {},
            "status": "draft",
        }
        data = {k: v for k, v in data.items() if v is not None}

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._table_name).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_template(self, template_id: str, user_id: str | None = None) -> dict:
        """Retrieve an email template by ID.

        Args:
            template_id: The unique template ID.
            user_id: Optional user ID override.

        Returns:
            The email template record.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*").eq("id", template_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_template(
        self,
        template_id: str,
        name: str | None = None,
        subject: str | None = None,
        body_html: str | None = None,
        body_text: str | None = None,
        category: str | None = None,
        variables: list[str] | None = None,
        ab_variants: list[dict] | None = None,
        status: str | None = None,
        metadata: dict | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update an email template.

        Args:
            template_id: The unique template ID.
            name: New name.
            subject: New subject line.
            body_html: New HTML body.
            body_text: New plain text body.
            category: New category.
            variables: New variables list.
            ab_variants: New A/B variants.
            status: New status (draft, active, archived).
            metadata: New metadata.
            user_id: Optional user ID override.

        Returns:
            The updated email template record.
        """
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if subject is not None:
            update_data["subject"] = subject
        if body_html is not None:
            update_data["body_html"] = body_html
        if body_text is not None:
            update_data["body_text"] = body_text
        if category is not None:
            update_data["category"] = category
        if variables is not None:
            update_data["variables"] = variables
        if ab_variants is not None:
            update_data["ab_variants"] = ab_variants
        if status is not None:
            update_data["status"] = status
        if metadata is not None:
            update_data["metadata"] = metadata

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).update(update_data).eq("id", template_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_template(
        self, template_id: str, user_id: str | None = None
    ) -> bool:
        """Delete an email template.

        Args:
            template_id: The unique template ID.
            user_id: Optional user ID override.

        Returns:
            True if deletion was successful.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).delete().eq("id", template_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        return len(response.data) > 0

    async def list_templates(
        self,
        category: str | None = None,
        status: str | None = None,
        campaign_id: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list:
        """List email templates with optional filters.

        Args:
            category: Filter by category.
            status: Filter by status.
            campaign_id: Filter by campaign.
            user_id: Optional user ID override.
            limit: Maximum results (default 50).

        Returns:
            List of email template records.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*")

        if category:
            query = query.eq("category", category)
        if status:
            query = query.eq("status", status)
        if campaign_id:
            query = query.eq("campaign_id", campaign_id)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(
            query.order("created_at", desc=True).limit(limit)
        )
        return response.data
