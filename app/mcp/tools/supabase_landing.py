"""Supabase Landing Page MCP Tool.

Provides backend integration for landing pages including:
- Landing page deployment and hosting
- Form submission handling
- Lead capture and storage
- Dynamic content management
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)


class SupabaseLandingTool:
    """Supabase MCP Tool for landing page backend operations."""
    
    def __init__(self):
        self._supabase = None
    
    @property
    def supabase(self):
        """Get Supabase service client."""
        if self._supabase is None:
            self._supabase = get_service_client()
        return self._supabase
    
    async def create_landing_page(
        self,
        user_id: str,
        title: str,
        slug: str,
        html_content: str,
        metadata: Optional[Dict[str, Any]] = None,
        published: bool = False,
    ) -> Dict[str, Any]:
        """Create a new landing page in the database.
        
        Args:
            user_id: User ID who owns the page
            title: Page title
            slug: URL slug for the page
            html_content: HTML content of the page
            metadata: Additional metadata (SEO, analytics, etc.)
            published: Whether the page is live
            
        Returns:
            Created page details
        """
        try:
            page_id = str(uuid.uuid4())
            
            page_data = {
                "id": page_id,
                "user_id": user_id,
                "title": title,
                "slug": slug,
                "html_content": html_content,
                "metadata": metadata or {},
                "published": published,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            self.supabase.table("landing_pages").insert(page_data).execute()
            
            return {
                "success": True,
                "page_id": page_id,
                "slug": slug,
                "url": f"/landing/{slug}",
                "published": published,
                "message": f"Landing page '{title}' created successfully",
            }
            
        except Exception as e:
            logger.error(f"Failed to create landing page: {e}")
            return {"error": str(e)}
    
    async def update_landing_page(
        self,
        page_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing landing page.
        
        Args:
            page_id: Page ID to update
            user_id: User ID for authorization
            updates: Fields to update
            
        Returns:
            Update result
        """
        try:
            # Add updated timestamp
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            self.supabase.table("landing_pages")\
                .update(updates)\
                .eq("id", page_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return {
                "success": True,
                "page_id": page_id,
                "updated_fields": list(updates.keys()),
                "message": "Landing page updated",
            }
            
        except Exception as e:
            logger.error(f"Failed to update landing page: {e}")
            return {"error": str(e)}
    
    async def publish_landing_page(
        self,
        page_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Publish a landing page to make it live.
        
        Args:
            page_id: Page ID to publish
            user_id: User ID for authorization
            
        Returns:
            Publish result with live URL
        """
        try:
            # Get page details first
            page = self.supabase.table("landing_pages")\
                .select("slug, title")\
                .eq("id", page_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if not page.data:
                return {"error": "Page not found"}
            
            # Update to published
            self.supabase.table("landing_pages")\
                .update({
                    "published": True,
                    "published_at": datetime.now(timezone.utc).isoformat(),
                })\
                .eq("id", page_id)\
                .execute()
            
            return {
                "success": True,
                "page_id": page_id,
                "slug": page.data["slug"],
                "url": f"/landing/{page.data['slug']}",
                "message": f"'{page.data['title']}' is now live!",
            }
            
        except Exception as e:
            logger.error(f"Failed to publish page: {e}")
            return {"error": str(e)}
    
    async def create_form(
        self,
        user_id: str,
        page_id: str,
        form_name: str,
        fields: List[Dict[str, Any]],
        webhook_url: Optional[str] = None,
        email_notification: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a form for a landing page.
        
        Args:
            user_id: User ID
            page_id: Landing page ID
            form_name: Name of the form
            fields: List of form fields with name, type, required, label
            webhook_url: Optional webhook to call on submission
            email_notification: Email to notify on submission
            
        Returns:
            Form details including submission endpoint
        """
        try:
            form_id = str(uuid.uuid4())
            
            form_data = {
                "id": form_id,
                "user_id": user_id,
                "page_id": page_id,
                "form_name": form_name,
                "fields": fields,
                "webhook_url": webhook_url,
                "email_notification": email_notification,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            self.supabase.table("landing_forms").insert(form_data).execute()
            
            # Generate form HTML
            form_html = self._generate_form_html(form_id, form_name, fields)
            
            return {
                "success": True,
                "form_id": form_id,
                "submission_endpoint": f"/api/forms/{form_id}/submit",
                "form_html": form_html,
                "fields": fields,
                "message": f"Form '{form_name}' created",
            }
            
        except Exception as e:
            logger.error(f"Failed to create form: {e}")
            return {"error": str(e)}
    
    def _generate_form_html(
        self,
        form_id: str,
        form_name: str,
        fields: List[Dict[str, Any]],
    ) -> str:
        """Generate HTML for a form."""
        field_html = []
        
        for field in fields:
            field_name = field.get("name", "field")
            field_type = field.get("type", "text")
            field_label = field.get("label", field_name.title())
            required = "required" if field.get("required", False) else ""
            placeholder = field.get("placeholder", "")
            
            if field_type == "textarea":
                input_html = f'''
    <textarea 
      name="{field_name}" 
      placeholder="{placeholder}"
      {required}
      class="form-input"
    ></textarea>'''
            elif field_type == "select":
                options = "".join([
                    f'<option value="{opt}">{opt}</option>' 
                    for opt in field.get("options", [])
                ])
                input_html = f'''
    <select name="{field_name}" {required} class="form-input">
      <option value="">Select...</option>
      {options}
    </select>'''
            else:
                input_html = f'''
    <input 
      type="{field_type}" 
      name="{field_name}" 
      placeholder="{placeholder}"
      {required}
      class="form-input"
    />'''
            
            field_html.append(f'''
  <div class="form-field">
    <label for="{field_name}">{field_label}</label>
    {input_html}
  </div>''')
        
        return f'''<form 
  id="form-{form_id}" 
  action="/api/forms/{form_id}/submit" 
  method="POST"
  class="landing-form"
>
  {"".join(field_html)}
  <button type="submit" class="submit-btn">Submit</button>
</form>

<style>
.landing-form {{ max-width: 400px; margin: 0 auto; }}
.form-field {{ margin-bottom: 16px; }}
.form-field label {{ display: block; margin-bottom: 4px; font-weight: 600; }}
.form-input {{ width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; }}
.submit-btn {{ width: 100%; padding: 14px; background: #635BFF; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; }}
.submit-btn:hover {{ background: #4f46e5; }}
</style>'''
    
    async def handle_form_submission(
        self,
        form_id: str,
        submission_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle a form submission.
        
        Args:
            form_id: Form ID
            submission_data: Submitted form data
            ip_address: Submitter's IP
            user_agent: Submitter's user agent
            
        Returns:
            Submission result
        """
        try:
            # Get form configuration
            form = self.supabase.table("landing_forms")\
                .select("*")\
                .eq("id", form_id)\
                .single()\
                .execute()
            
            if not form.data:
                return {"error": "Form not found"}
            
            form_config = form.data
            
            # Store submission
            submission_id = str(uuid.uuid4())
            submission = {
                "id": submission_id,
                "form_id": form_id,
                "user_id": form_config["user_id"],
                "page_id": form_config["page_id"],
                "data": submission_data,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            self.supabase.table("form_submissions").insert(submission).execute()
            
            # Trigger webhook if configured
            if form_config.get("webhook_url"):
                await self._trigger_webhook(form_config["webhook_url"], submission)
            
            # Send email notification if configured
            if form_config.get("email_notification"):
                await self._send_notification_email(
                    form_config["email_notification"],
                    form_config["form_name"],
                    submission_data,
                )
            
            return {
                "success": True,
                "submission_id": submission_id,
                "message": "Form submitted successfully",
            }
            
        except Exception as e:
            logger.error(f"Form submission failed: {e}")
            return {"error": str(e)}
    
    async def _trigger_webhook(
        self,
        webhook_url: str,
        submission: Dict[str, Any],
    ) -> None:
        """Trigger webhook with submission data."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    webhook_url,
                    json=submission,
                    timeout=10.0,
                )
        except Exception as e:
            logger.warning(f"Webhook failed: {e}")
    
    async def _send_notification_email(
        self,
        email: str,
        form_name: str,
        data: Dict[str, Any],
    ) -> None:
        """Send email notification for form submission."""
        # Would integrate with Resend or other email service
        logger.info(f"Would send notification to {email} for {form_name}")
    
    async def list_submissions(
        self,
        user_id: str,
        form_id: Optional[str] = None,
        page_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List form submissions.
        
        Args:
            user_id: User ID
            form_id: Filter by form
            page_id: Filter by page
            limit: Max results
            
        Returns:
            List of submissions
        """
        try:
            query = self.supabase.table("form_submissions")\
                .select("*")\
                .eq("user_id", user_id)
            
            if form_id:
                query = query.eq("form_id", form_id)
            if page_id:
                query = query.eq("page_id", page_id)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            
            return {
                "success": True,
                "submissions": result.data,
                "count": len(result.data),
            }
            
        except Exception as e:
            logger.error(f"Failed to list submissions: {e}")
            return {"error": str(e)}
    
    async def get_landing_page(
        self,
        slug: str,
    ) -> Dict[str, Any]:
        """Get a landing page by slug for rendering.
        
        Args:
            slug: URL slug
            
        Returns:
            Page content and metadata
        """
        try:
            result = self.supabase.table("landing_pages")\
                .select("*")\
                .eq("slug", slug)\
                .eq("published", True)\
                .single()\
                .execute()
            
            if not result.data:
                return {"error": "Page not found", "status": 404}
            
            return {
                "success": True,
                "page": result.data,
            }
            
        except Exception as e:
            logger.error(f"Failed to get page: {e}")
            return {"error": str(e)}
    
    async def list_landing_pages(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """List all landing pages for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of landing pages
        """
        try:
            result = self.supabase.table("landing_pages")\
                .select("id, title, slug, published, created_at, updated_at")\
                .eq("user_id", user_id)\
                .order("updated_at", desc=True)\
                .execute()
            
            return {
                "success": True,
                "pages": result.data,
                "count": len(result.data),
            }
            
        except Exception as e:
            logger.error(f"Failed to list pages: {e}")
            return {"error": str(e)}


# Singleton instance
_landing_tool: Optional[SupabaseLandingTool] = None


def get_landing_tool() -> SupabaseLandingTool:
    """Get singleton landing tool instance."""
    global _landing_tool
    if _landing_tool is None:
        _landing_tool = SupabaseLandingTool()
    return _landing_tool


# ============================================================================
# Agent Tool Functions
# ============================================================================

async def create_landing_page(
    user_id: str,
    title: str,
    html_content: str,
    slug: Optional[str] = None,
    publish: bool = False,
) -> Dict[str, Any]:
    """Create and optionally publish a landing page.
    
    Use this after generating landing page HTML with Stitch or manually.
    Stores the page in the database and provides a URL.
    
    Args:
        user_id: User ID
        title: Page title (for SEO and display)
        html_content: Full HTML content of the page
        slug: URL slug (auto-generated if not provided)
        publish: Whether to publish immediately
        
    Returns:
        Page details including URL
    """
    tool = get_landing_tool()
    
    # Generate slug from title if not provided
    if not slug:
        slug = title.lower().replace(" ", "-")[:50]
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
    
    return await tool.create_landing_page(
        user_id=user_id,
        title=title,
        slug=slug,
        html_content=html_content,
        published=publish,
    )


async def add_form_to_page(
    user_id: str,
    page_id: str,
    form_name: str,
    fields: List[Dict[str, Any]],
    notification_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a form to a landing page for lead capture.
    
    Creates a form and returns the HTML to embed in the page.
    
    Args:
        user_id: User ID
        page_id: Landing page ID
        form_name: Name for the form (e.g., "Contact Form")
        fields: List of fields, each with:
            - name: field name
            - type: text, email, phone, textarea, select
            - label: display label
            - required: boolean
            - placeholder: placeholder text
        notification_email: Email to receive submissions
        
    Returns:
        Form HTML and submission endpoint
    """
    tool = get_landing_tool()
    
    return await tool.create_form(
        user_id=user_id,
        page_id=page_id,
        form_name=form_name,
        fields=fields,
        email_notification=notification_email,
    )


async def publish_page(
    user_id: str,
    page_id: str,
) -> Dict[str, Any]:
    """Publish a landing page to make it live.
    
    Args:
        user_id: User ID
        page_id: Page ID to publish
        
    Returns:
        Live URL
    """
    tool = get_landing_tool()
    return await tool.publish_landing_page(page_id=page_id, user_id=user_id)


async def get_form_submissions(
    user_id: str,
    form_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get form submissions (leads).
    
    Retrieves all form submissions, optionally filtered by form.
    
    Args:
        user_id: User ID
        form_id: Optional form ID to filter
        
    Returns:
        List of submissions
    """
    tool = get_landing_tool()
    return await tool.list_submissions(user_id=user_id, form_id=form_id)


async def list_pages(user_id: str) -> Dict[str, Any]:
    """List all landing pages for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        List of pages with status
    """
    tool = get_landing_tool()
    return await tool.list_landing_pages(user_id=user_id)


# ============================================================================
# Export for Agent Registration
# ============================================================================

SUPABASE_LANDING_TOOLS = [
    create_landing_page,
    add_form_to_page,
    publish_page,
    get_form_submissions,
    list_pages,
]

SUPABASE_LANDING_TOOLS_MAP = {
    "create_landing_page": create_landing_page,
    "add_form_to_page": add_form_to_page,
    "publish_page": publish_page,
    "get_form_submissions": get_form_submissions,
    "list_pages": list_pages,
}
