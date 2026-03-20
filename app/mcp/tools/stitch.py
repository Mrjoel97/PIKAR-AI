"""Stitch MCP Tool - Landing page generation via Google Stitch.

This module provides integration with Google Stitch (stitch.withgoogle.com)
for AI-powered landing page generation. It includes both direct generation
capabilities and export-to-workspace functionality.

Features:
- Generate landing pages from natural language descriptions
- Multiple style presets (modern, minimal, bold, tech, startup)
- Export generated pages to user's workspace
- Integration with the landing page storage system
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from supabase import Client
from app.mcp.config import get_mcp_config
from app.mcp.security.audit_logger import log_mcp_call
from app.mcp.security.external_call_guard import protect_text_payload

logger = logging.getLogger(__name__)


@dataclass
class StitchPageConfig:
    """Configuration for a Stitch-generated landing page."""
    title: str
    description: str
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    style: str = "modern"
    include_form: bool = True
    cta_text: str = "Get Started"
    sections: Optional[List[str]] = None
    branding: Optional[Dict[str, str]] = None


class StitchMCPTool:
    """Stitch MCP Tool for landing page generation.
    
    This tool provides a high-level interface for generating landing pages
    using Google Stitch or falling back to local generation when Stitch
    API is not available.
    """
    
    STYLE_PRESETS = {
        "modern": {
            "colors": {"primary": "#4361ee", "background": "#ffffff", "text": "#1a1a2e"},
            "font": "Inter",
            "border_radius": "8px",
        },
        "minimal": {
            "colors": {"primary": "#000000", "background": "#fafafa", "text": "#333333"},
            "font": "Helvetica Neue",
            "border_radius": "4px",
        },
        "bold": {
            "colors": {"primary": "#f72585", "background": "#1a1a2e", "text": "#ffffff"},
            "font": "Poppins",
            "border_radius": "12px",
        },
        "tech": {
            "colors": {"primary": "#00d9ff", "background": "#0a0a0f", "text": "#e0e0e0"},
            "font": "JetBrains Mono",
            "border_radius": "6px",
        },
        "startup": {
            "colors": {"primary": "#6366f1", "background": "#fefefe", "text": "#18181b"},
            "font": "DM Sans",
            "border_radius": "16px",
        },
    }
    
    def __init__(self):
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Optional[Client]:
        """Get Supabase client for storage."""
        if self._client is None:
            try:
                from app.services.supabase import get_service_client
                self._client = get_service_client()
            except Exception as e:
                logger.warning(f"Failed to get Supabase client: {e}")
        return self._client
    
    def _stitch_api_available(self) -> bool:
        """Check if Stitch API is configured and available."""
        config = get_mcp_config()
        return config.is_stitch_configured()
    
    async def generate_with_stitch(self, config: StitchPageConfig) -> Optional[Dict[str, Any]]:
        """Generate landing page using Stitch API."""
        if not self._stitch_api_available():
            logger.info("Stitch API not configured, using fallback generation")
            return None

        prompt_guard = protect_text_payload(f"Create a {config.style} landing page for: {config.description}", field_name="stitch_prompt")
        title_guard = protect_text_payload(config.title, field_name="stitch_title")
        headline_guard = protect_text_payload(config.headline or config.title, field_name="stitch_headline")
        subheadline_guard = protect_text_payload(config.subheadline or config.description, field_name="stitch_subheadline")

        try:
            import httpx

            mcp_config = get_mcp_config()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{mcp_config.stitch_api_url}/generate",
                    headers={
                        "Authorization": f"Bearer {mcp_config.stitch_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "prompt": prompt_guard.outbound_value,
                        "title": title_guard.outbound_value,
                        "headline": headline_guard.outbound_value,
                        "subheadline": subheadline_guard.outbound_value,
                        "style": config.style,
                        "include_form": config.include_form,
                        "cta_text": config.cta_text,
                        "sections": config.sections or ["hero", "features", "cta"],
                        "branding": config.branding,
                    },
                    timeout=60.0,
                )

            guard_metadata = {
                "prompt_guard": prompt_guard.metadata,
                "title_guard": title_guard.metadata,
                "headline_guard": headline_guard.metadata,
                "subheadline_guard": subheadline_guard.metadata,
                "style": config.style,
            }
            if response.status_code == 200:
                log_mcp_call(
                    tool_name="stitch_generate_page",
                    query_sanitized=prompt_guard.audit_value,
                    success=True,
                    response_status="success",
                    metadata=guard_metadata,
                )
                return response.json()

            logger.warning(f"Stitch API returned {response.status_code}")
            log_mcp_call(
                tool_name="stitch_generate_page",
                query_sanitized=prompt_guard.audit_value,
                success=False,
                response_status="error",
                error_message=f"Stitch API returned {response.status_code}",
                metadata={**guard_metadata, "status_code": response.status_code},
            )
            return None

        except Exception as e:
            logger.error(f"Stitch API error: {e}")
            log_mcp_call(
                tool_name="stitch_generate_page",
                query_sanitized=prompt_guard.audit_value,
                success=False,
                response_status="error",
                error_message=str(e),
                metadata={
                    "prompt_guard": prompt_guard.metadata,
                    "title_guard": title_guard.metadata,
                    "headline_guard": headline_guard.metadata,
                    "subheadline_guard": subheadline_guard.metadata,
                    "style": config.style,
                },
            )
            return None

    def generate_html_fallback(self, config: StitchPageConfig) -> str:
        """Generate HTML landing page locally (fallback when Stitch unavailable)."""
        style = self.STYLE_PRESETS.get(config.style, self.STYLE_PRESETS["modern"])
        colors = style["colors"]
        font = style["font"]
        radius = style["border_radius"]
        
        # Build sections
        sections_html = ""
        for section in (config.sections or ["hero", "features", "cta"]):
            if section == "hero":
                sections_html += f'''
        <section class="hero">
            <h1>{config.headline or config.title}</h1>
            <p class="subheadline">{config.subheadline or config.description}</p>
            {self._build_form_html(config) if config.include_form else f'<a href="#" class="cta-button">{config.cta_text}</a>'}
        </section>'''
            elif section == "features":
                sections_html += '''
        <section class="features">
            <div class="feature">
                <h3>Feature One</h3>
                <p>Description of the first key feature.</p>
            </div>
            <div class="feature">
                <h3>Feature Two</h3>
                <p>Description of the second key feature.</p>
            </div>
            <div class="feature">
                <h3>Feature Three</h3>
                <p>Description of the third key feature.</p>
            </div>
        </section>'''
            elif section == "cta":
                sections_html += f'''
        <section class="cta-section">
            <h2>Ready to get started?</h2>
            <a href="#" class="cta-button">{config.cta_text}</a>
        </section>'''
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title}</title>
    <meta name="description" content="{config.subheadline or config.description}">
    <meta property="og:title" content="{config.headline or config.title}">
    <meta property="og:description" content="{config.subheadline or config.description}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{config.headline or config.title}">
    <meta name="twitter:description" content="{config.subheadline or config.description}">
    <link href="https://fonts.googleapis.com/css2?family={font.replace(' ', '+')}:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: '{font}', sans-serif; 
            background: {colors['background']}; 
            color: {colors['text']}; 
            line-height: 1.6;
        }}
        .hero {{ 
            min-height: 100vh; 
            display: flex; 
            flex-direction: column; 
            justify-content: center; 
            align-items: center; 
            padding: 2rem; 
            text-align: center; 
        }}
        h1 {{ font-size: clamp(2rem, 5vw, 4rem); margin-bottom: 1rem; max-width: 900px; font-weight: 700; }}
        .subheadline {{ font-size: 1.25rem; opacity: 0.8; margin-bottom: 2rem; max-width: 600px; }}
        .cta-button {{ 
            display: inline-block;
            padding: 1rem 2.5rem; 
            background: {colors['primary']}; 
            color: #fff; 
            border: none; 
            border-radius: {radius}; 
            font-size: 1rem; 
            font-weight: 600;
            cursor: pointer; 
            text-decoration: none;
            transition: transform 0.2s, box-shadow 0.2s; 
        }}
        .cta-button:hover {{ transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0,0,0,0.15); }}
        .lead-form {{ 
            display: flex; 
            flex-direction: column; 
            gap: 1rem; 
            width: 100%; 
            max-width: 400px; 
        }}
        .form-input {{ 
            padding: 1rem; 
            border: 2px solid {colors['primary']}20; 
            border-radius: {radius}; 
            font-size: 1rem;
            font-family: inherit;
        }}
        .form-input:focus {{ outline: none; border-color: {colors['primary']}; }}
        .features {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 2rem;
            padding: 4rem 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .feature {{
            padding: 2rem;
            background: {colors['primary']}08;
            border-radius: {radius};
        }}
        .feature h3 {{ margin-bottom: 0.5rem; color: {colors['primary']}; }}
        .cta-section {{
            text-align: center;
            padding: 4rem 2rem;
            background: {colors['primary']}10;
        }}
        .cta-section h2 {{ margin-bottom: 1.5rem; }}
    </style>
</head>
<body>
    {sections_html}
</body>
</html>'''
    
    def _build_form_html(self, config: StitchPageConfig) -> str:
        """Build form HTML for landing page."""
        return f'''
            <form class="lead-form" data-form-id="stitch-form">
                <input type="text" name="name" placeholder="Your Name" required class="form-input">
                <input type="email" name="email" placeholder="Your Email" required class="form-input">
                <button type="submit" class="cta-button">{config.cta_text}</button>
            </form>'''
    
    def generate_react_component(self, config: StitchPageConfig) -> str:
        """Generate React component for landing page."""
        self.STYLE_PRESETS.get(config.style, self.STYLE_PRESETS["modern"])
        
        return f'''import React, {{ useState }} from 'react';

export default function LandingPage() {{
  const [submitted, setSubmitted] = useState(false);
  const [formData, setFormData] = useState({{ name: '', email: '' }});

  const handleSubmit = async (e) => {{
    e.preventDefault();
    try {{
      await fetch('/api/submit-lead', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(formData),
      }});
      setSubmitted(true);
    }} catch (error) {{
      console.error('Submission failed:', error);
    }}
  }};

  if (submitted) {{
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Thank you!</h2>
          <p className="text-gray-600">We'll be in touch soon.</p>
        </div>
      </div>
    );
  }}

  return (
    <div className="min-h-screen bg-white">
      {{/* Hero Section */}}
      <section className="min-h-screen flex flex-col justify-center items-center px-4 py-20 text-center">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 max-w-4xl">
          {config.headline or config.title}
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl">
          {config.subheadline or config.description}
        </p>
        {f"""
        <form onSubmit={{handleSubmit}} className="flex flex-col gap-4 w-full max-w-md">
          <input
            type="text"
            placeholder="Your Name"
            required
            className="px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 outline-none"
            value={{formData.name}}
            onChange={{(e) => setFormData({{...formData, name: e.target.value}})}}
          />
          <input
            type="email"
            placeholder="Your Email"
            required
            className="px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 outline-none"
            value={{formData.email}}
            onChange={{(e) => setFormData({{...formData, email: e.target.value}})}}
          />
          <button
            type="submit"
            className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
          >
            {config.cta_text}
          </button>
        </form>
        """ if config.include_form else f"""
        <a
          href="#"
          className="px-8 py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
        >
          {config.cta_text}
        </a>
        """}
      </section>

      {{/* Features Section */}}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-8">
          <div className="p-6 bg-white rounded-xl shadow-sm">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Feature One</h3>
            <p className="text-gray-600">Description of the first key feature that sets you apart.</p>
          </div>
          <div className="p-6 bg-white rounded-xl shadow-sm">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Feature Two</h3>
            <p className="text-gray-600">Description of the second key feature that adds value.</p>
          </div>
          <div className="p-6 bg-white rounded-xl shadow-sm">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Feature Three</h3>
            <p className="text-gray-600">Description of the third key feature that builds trust.</p>
          </div>
        </div>
      </section>

      {{/* CTA Section */}}
      <section className="py-20 px-4 text-center bg-blue-50">
        <h2 className="text-3xl font-bold text-gray-900 mb-6">Ready to get started?</h2>
        <a
          href="#"
          className="inline-block px-8 py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
        >
          {config.cta_text}
        </a>
      </section>
    </div>
  );
}}
'''
    
    async def save_to_workspace(
        self,
        page_id: str,
        user_id: str,
        title: str,
        html_content: str,
        react_content: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Save generated landing page to user's workspace."""
        if not self.client:
            return {"success": False, "error": "Database not configured"}
        
        try:
            slug = title.lower().replace(" ", "-")[:50]
            slug = "".join(c for c in slug if c.isalnum() or c == "-")

            data = {
                "id": page_id,
                "user_id": user_id,
                "title": title,
                "slug": slug,
                "html_content": html_content,
                "metadata": {
                    "react_content": react_content,
                    "config": config,
                    "source": "stitch",
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            self.client.table("landing_pages").upsert(data).execute()
            
            return {
                "success": True,
                "page_id": page_id,
                "message": f"Landing page '{title}' saved to workspace",
            }
        except Exception as e:
            logger.error(f"Failed to save page: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_stitch_tool: Optional[StitchMCPTool] = None


def get_stitch_tool() -> StitchMCPTool:
    """Get the singleton Stitch tool instance."""
    global _stitch_tool
    if _stitch_tool is None:
        _stitch_tool = StitchMCPTool()
    return _stitch_tool


# Agent Tool Functions
async def stitch_generate_landing_page(
    title: str,
    description: str,
    headline: Optional[str] = None,
    subheadline: Optional[str] = None,
    style: str = "modern",
    include_form: bool = True,
    cta_text: str = "Get Started",
    sections: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    save_to_workspace: bool = True,
) -> Dict[str, Any]:
    """Generate a landing page using Stitch MCP.
    
    Creates a complete landing page with HTML and React versions.
    Optionally saves to the user's workspace for later access.
    
    Args:
        title: Page title for SEO and browser tab.
        description: Brief description of the page purpose.
        headline: Main headline (defaults to title).
        subheadline: Supporting text (defaults to description).
        style: Visual style - "modern", "minimal", "bold", "tech", or "startup".
        include_form: Whether to include a lead capture form.
        cta_text: Call-to-action button text.
        sections: List of sections to include (default: hero, features, cta).
        user_id: User ID for workspace storage.
        save_to_workspace: Whether to save to workspace.
    
    Returns:
        Dictionary with generated HTML, React code, and page details.
    """
    tool = get_stitch_tool()
    
    config = StitchPageConfig(
        title=title,
        description=description,
        headline=headline,
        subheadline=subheadline,
        style=style,
        include_form=include_form,
        cta_text=cta_text,
        sections=sections,
    )
    
    # Try Stitch API first, fall back to local generation
    stitch_result = await tool.generate_with_stitch(config)
    
    if stitch_result:
        html_content = stitch_result.get("html", "")
        react_content = stitch_result.get("react", "")
        source = "stitch_api"
    else:
        html_content = tool.generate_html_fallback(config)
        react_content = tool.generate_react_component(config)
        source = "local_fallback"
    
    page_id = str(uuid.uuid4())
    
    result = {
        "success": True,
        "page_id": page_id,
        "title": title,
        "html": html_content,
        "react": react_content,
        "source": source,
        "config": {
            "title": title,
            "description": description,
            "headline": headline or title,
            "subheadline": subheadline or description,
            "style": style,
            "include_form": include_form,
            "cta_text": cta_text,
            "sections": sections or ["hero", "features", "cta"],
        },
    }
    
    # Save to workspace if requested
    if save_to_workspace and user_id:
        save_result = await tool.save_to_workspace(
            page_id=page_id,
            user_id=user_id,
            title=title,
            html_content=html_content,
            react_content=react_content,
            config=result["config"],
        )
        result["workspace_saved"] = save_result["success"]
        if not save_result["success"]:
            result["workspace_error"] = save_result.get("error")
    
    logger.info(f"Generated landing page '{title}' via {source}")
    
    return result


async def stitch_export_to_workspace(
    page_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Export a previously generated landing page to user's workspace.
    
    Args:
        page_id: The page ID from a previous generation.
        user_id: User ID for workspace storage.
    
    Returns:
        Dictionary with export status.
    """
    tool = get_stitch_tool()
    
    if not tool.client:
        return {"success": False, "error": "Database not configured"}
    
    try:
        # Retrieve the page
        result = tool.client.table("landing_pages").select("*").eq("id", page_id).single().execute()
        
        if not result.data:
            return {"success": False, "error": "Page not found"}
        
        page = result.data
        
        # Update ownership if needed
        if page.get("user_id") != user_id:
            # Create a copy for this user
            new_page_id = str(uuid.uuid4())
            new_slug = f"{page.get('slug', 'export')}-{new_page_id[:8]}"
            new_page = {
                "id": new_page_id,
                "user_id": user_id,
                "title": page["title"],
                "slug": new_slug,
                "html_content": page.get("html_content"),
                "metadata": {
                    "react_content": page.get("metadata", {}).get("react_content"),
                    "config": page.get("metadata", {}).get("config"),
                    "source": "stitch_export",
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            tool.client.table("landing_pages").insert(new_page).execute()
            return {
                "success": True,
                "page_id": new_page_id,
                "message": "Page exported to your workspace",
            }
        
        return {
            "success": True,
            "page_id": page_id,
            "message": "Page already in your workspace",
        }
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return {"success": False, "error": str(e)}


# Export tools for agent registration
STITCH_TOOLS = [
    stitch_generate_landing_page,
    stitch_export_to_workspace,
]
