"""Landing Page Tool - Generate and manage landing pages.

This module provides landing page generation with HTML/React components
and storage in Supabase for the landing page builder feature.

Features:
- Generate HTML landing pages from templates
- Generate React components for modern apps
- Store landing page configurations in Supabase
- Retrieve and manage landing pages
"""

import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from supabase import create_client, Client

from app.mcp.config import get_mcp_config
from app.mcp.security.audit_logger import log_mcp_call


class LandingPageTool:
    """Landing page generation and management tool."""
    
    def __init__(self):
        self.config = get_mcp_config()
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Optional[Client]:
        """Get Supabase client."""
        if self._client is None and self.config.is_supabase_configured():
            self._client = create_client(
                self.config.supabase_url,
                self.config.supabase_service_key
            )
        return self._client
    
    def generate_html(
        self,
        title: str,
        headline: str,
        subheadline: str,
        cta_text: str = "Get Started",
        style: str = "modern",
        include_form: bool = True,
        form_fields: Optional[List[Dict]] = None,
    ) -> str:
        """Generate HTML landing page."""
        if form_fields is None:
            form_fields = [
                {"name": "name", "type": "text", "placeholder": "Your Name", "required": True},
                {"name": "email", "type": "email", "placeholder": "Your Email", "required": True},
            ]
        
        # Build form HTML
        form_html = ""
        if include_form:
            fields_html = "\n".join([
                f'<input type="{f["type"]}" name="{f["name"]}" placeholder="{f["placeholder"]}" {"required" if f.get("required") else ""} class="form-input">'
                for f in form_fields
            ])
            form_html = f'''
            <form class="lead-form" data-form-id="{{form_id}}">
                {fields_html}
                <button type="submit" class="cta-button">{cta_text}</button>
            </form>'''
        
        # Style configurations
        styles = {
            "modern": {"bg": "#ffffff", "text": "#1a1a2e", "accent": "#4361ee", "font": "Inter"},
            "minimal": {"bg": "#fafafa", "text": "#333333", "accent": "#000000", "font": "Helvetica"},
            "bold": {"bg": "#1a1a2e", "text": "#ffffff", "accent": "#f72585", "font": "Poppins"},
        }
        s = styles.get(style, styles["modern"])
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: '{s["font"]}', sans-serif; background: {s["bg"]}; color: {s["text"]}; }}
        .hero {{ min-height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 2rem; text-align: center; }}
        h1 {{ font-size: 3rem; margin-bottom: 1rem; max-width: 800px; }}
        .subheadline {{ font-size: 1.25rem; opacity: 0.8; margin-bottom: 2rem; max-width: 600px; }}
        .lead-form {{ display: flex; flex-direction: column; gap: 1rem; width: 100%; max-width: 400px; }}
        .form-input {{ padding: 1rem; border: 2px solid {s["accent"]}20; border-radius: 8px; font-size: 1rem; }}
        .form-input:focus {{ outline: none; border-color: {s["accent"]}; }}
        .cta-button {{ padding: 1rem 2rem; background: {s["accent"]}; color: #fff; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; transition: transform 0.2s; }}
        .cta-button:hover {{ transform: translateY(-2px); }}
    </style>
</head>
<body>
    <section class="hero">
        <h1>{headline}</h1>
        <p class="subheadline">{subheadline}</p>
        {form_html}
    </section>
</body>
</html>'''
    
    def generate_react(
        self,
        title: str,
        headline: str,
        subheadline: str,
        cta_text: str = "Get Started",
        style: str = "modern",
        include_form: bool = True,
    ) -> str:
        """Generate React component for landing page."""
        form_jsx = ""
        if include_form:
            form_jsx = f'''
      <form onSubmit={{handleSubmit}} className="flex flex-col gap-4 w-full max-w-md">
        <input type="text" name="name" placeholder="Your Name" required className="p-4 border-2 rounded-lg" />
        <input type="email" name="email" placeholder="Your Email" required className="p-4 border-2 rounded-lg" />
        <button type="submit" className="p-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          {cta_text}
        </button>
      </form>'''
        
        return f'''import React, {{ useState }} from 'react';

export default function LandingPage() {{
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {{
    e.preventDefault();
    const formData = new FormData(e.target);
    // Submit to your API endpoint
    await fetch('/api/submit-form', {{
      method: 'POST',
      body: JSON.stringify(Object.fromEntries(formData)),
      headers: {{ 'Content-Type': 'application/json' }},
    }});
    setSubmitted(true);
  }};

  if (submitted) return <div className="text-center p-8">Thanks! We'll be in touch.</div>;

  return (
    <section className="min-h-screen flex flex-col justify-center items-center p-8 text-center">
      <h1 className="text-5xl font-bold mb-4 max-w-4xl">{headline}</h1>
      <p className="text-xl opacity-80 mb-8 max-w-2xl">{subheadline}</p>
      {form_jsx}
    </section>
  );
}}'''

    async def save_page(
        self,
        page_id: str,
        user_id: str,
        title: str,
        html_content: str,
        react_content: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Save landing page to Supabase."""
        if not self.client:
            return {"success": False, "error": "Supabase not configured"}

        try:
            data = {
                "id": page_id,
                "user_id": user_id,
                "title": title,
                "html_content": html_content,
                "react_content": react_content,
                "config": config,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            result = self.client.table("landing_pages").upsert(data).execute()
            return {"success": True, "page_id": page_id, "data": result.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve landing page from Supabase."""
        if not self.client:
            return {"success": False, "error": "Supabase not configured"}

        try:
            result = self.client.table("landing_pages").select("*").eq("id", page_id).single().execute()
            return {"success": True, "page": result.data}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
_page_tool: Optional[LandingPageTool] = None


def _get_page_tool() -> LandingPageTool:
    """Get the singleton landing page tool instance."""
    global _page_tool
    if _page_tool is None:
        _page_tool = LandingPageTool()
    return _page_tool


async def generate_landing_page(
    title: str,
    description: str,
    headline: Optional[str] = None,
    subheadline: Optional[str] = None,
    style: str = "modern",
    include_form: bool = True,
    cta_text: str = "Get Started",
    agent_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a landing page with HTML and React components.

    Creates both HTML and React versions of a landing page based on
    the provided configuration.

    Args:
        title: Page title for SEO and browser tab.
        description: Brief description of the page purpose.
        headline: Main headline (defaults to title if not provided).
        subheadline: Supporting text (defaults to description).
        style: Visual style - "modern", "minimal", or "bold".
        include_form: Whether to include a lead capture form.
        cta_text: Call-to-action button text.

    Returns:
        Dictionary with generated HTML and React code.
    """
    start_time = time.time()
    tool = _get_page_tool()

    html_content = tool.generate_html(
        title=title,
        headline=headline or title,
        subheadline=subheadline or description,
        cta_text=cta_text,
        style=style,
        include_form=include_form,
    )

    react_content = tool.generate_react(
        title=title,
        headline=headline or title,
        subheadline=subheadline or description,
        cta_text=cta_text,
        style=style,
        include_form=include_form,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    log_mcp_call(
        tool_name="generate_landing_page",
        query_sanitized=f"title={title}, style={style}",
        success=True,
        agent_name=agent_name,
        user_id=user_id,
        duration_ms=duration_ms,
    )

    return {
        "success": True,
        "page_id": str(uuid.uuid4()),
        "title": title,
        "html": html_content,
        "react": react_content,
        "config": {
            "title": title,
            "headline": headline or title,
            "subheadline": subheadline or description,
            "style": style,
            "include_form": include_form,
            "cta_text": cta_text,
        },
    }


async def save_landing_page(
    page_id: str,
    user_id: str,
    title: str,
    html_content: str,
    react_content: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Save a landing page to Supabase.

    Args:
        page_id: Unique page identifier.
        user_id: Owner user ID.
        title: Page title.
        html_content: Generated HTML.
        react_content: Generated React component.
        config: Page configuration.

    Returns:
        Save result dictionary.
    """
    tool = _get_page_tool()
    return await tool.save_page(
        page_id=page_id,
        user_id=user_id,
        title=title,
        html_content=html_content,
        react_content=react_content,
        config=config,
    )


async def get_landing_page(page_id: str) -> Dict[str, Any]:
    """Retrieve a landing page from Supabase.

    Args:
        page_id: Page identifier.

    Returns:
        Landing page data.
    """
    tool = _get_page_tool()
    return await tool.get_page(page_id)

