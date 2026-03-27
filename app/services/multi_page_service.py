# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Multi-Page Service — baton-loop generator and navigation link injection.

Provides two exported functions:

* ``build_all_pages`` — async generator that iterates through a sitemap, calls Stitch
  once per page with a growing nav-context baton, persists assets, and yields
  SSE-compatible event dicts.

* ``inject_navigation_links`` — post-processor that re-downloads persisted HTML for
  each page, rewrites all ``<a href="/slug">`` anchors to absolute Supabase Storage
  URLs, and re-uploads the modified HTML in-place.

CRITICAL: All Stitch calls are sequential ``await`` calls — never ``asyncio.gather``.
The StitchMCPService serialises calls through an asyncio.Lock; gathering would
cause a deadlock.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from html.parser import HTMLParser
from typing import Any
from uuid import uuid4

import httpx

from app.services.stitch_assets import persist_screen_assets
from app.services.stitch_mcp import get_stitch_service
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

_STITCH_ASSETS_BUCKET = "stitch-assets"


# ---------------------------------------------------------------------------
# Baton loop — main entry point
# ---------------------------------------------------------------------------


async def build_all_pages(
    project_id: str,
    user_id: str,
    sitemap: list[dict[str, Any]],
    design_markdown: str,
    stitch_project_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Generate all sitemap pages sequentially using the baton pattern.

    Iterates through each page in ``sitemap`` in order, calling Stitch once per
    page with (a) the locked design system prepended to the prompt and (b) a
    growing nav-context baton from already-generated pages. Persists HTML and
    screenshot assets to Supabase Storage before yielding each ``page_complete``
    event so callers always receive permanent URLs.

    Yields SSE-compatible event dicts:

    * ``{"step": "page_started", "page_index": i, "page_slug": ..., "total_pages": n}``
    * ``{"step": "page_complete", "page_index": i, "page_slug": ...,
         "screen_id": ..., "html_url": ..., "screenshot_url": ...,
         "page_title": ..., "variant_id": ...}``
    * ``{"step": "build_complete", "total_pages": n, "screens": [...]}``

    Args:
        project_id: App project UUID.
        user_id: Authenticated user UUID.
        sitemap: List of page dicts with keys ``page`` (slug), ``title``,
                 and optionally ``sections``.
        design_markdown: Locked design system raw Markdown (from design_systems table).
        stitch_project_id: Stitch project ID shared across all pages.

    Yields:
        Event dicts suitable for JSON-serialising into SSE data lines.
    """
    service = get_stitch_service()
    supabase = get_service_client()
    total = len(sitemap)
    screens_built: list[dict[str, Any]] = []

    for i, page in enumerate(sitemap):
        page_slug: str = page.get("page", f"page-{i + 1}")
        page_title: str = page.get("title", page_slug.replace("-", " ").title())
        sections: list[str] = page.get("sections", [])

        yield {
            "step": "page_started",
            "page_index": i,
            "page_slug": page_slug,
            "total_pages": total,
        }

        # Build baton: growing nav context from already-generated pages
        nav_context = _build_nav_baton(screens_built)

        # Assemble prompt: design system + page spec + nav context
        prompt = _build_page_prompt(
            design_markdown=design_markdown,
            page_title=page_title,
            page_slug=page_slug,
            sections=sections,
            nav_context=nav_context,
        )

        # Sequential Stitch call — CRITICAL: never asyncio.gather, Lock deadlocks
        stitch_response = await service.call_tool(
            "generate_screen_from_text",
            {
                "prompt": prompt,
                "projectId": stitch_project_id,
                "deviceType": "DESKTOP",
            },
        )

        screen_id = str(uuid4())

        # Insert app_screens row with page_slug for multi-page tracking
        supabase.table("app_screens").insert(
            {
                "id": screen_id,
                "project_id": project_id,
                "user_id": user_id,
                "name": page_title,
                "page_slug": page_slug,
                "device_type": "DESKTOP",
                "order_index": i,
                "approved": False,
                "stitch_project_id": stitch_project_id,
            }
        ).execute()

        # Persist assets BEFORE yielding — callers must receive permanent URLs
        persisted = await persist_screen_assets(
            stitch_response=stitch_response,
            user_id=user_id,
            project_id=project_id,
            screen_id=screen_id,
            variant_index=0,
        )

        # Insert screen_variants row — single variant (is_selected=True, iteration=1)
        stitch_screen_id: str = stitch_response.get("screenId") or stitch_response.get(
            "screen_id", ""
        )
        variant_id = str(uuid4())
        supabase.table("screen_variants").insert(
            {
                "id": variant_id,
                "screen_id": screen_id,
                "user_id": user_id,
                "variant_index": 0,
                "stitch_screen_id": stitch_screen_id,
                "html_url": persisted["html_url"],
                "screenshot_url": persisted["screenshot_url"],
                "prompt_used": prompt,
                "is_selected": True,
                "iteration": 1,
            }
        ).execute()

        screen_entry: dict[str, Any] = {
            "page_index": i,
            "page_slug": page_slug,
            "page_title": page_title,
            "screen_id": screen_id,
            "variant_id": variant_id,
            "html_url": persisted["html_url"],
            "screenshot_url": persisted["screenshot_url"],
        }
        screens_built.append(screen_entry)

        yield {"step": "page_complete", **screen_entry}

    yield {
        "step": "build_complete",
        "total_pages": total,
        "screens": screens_built,
    }


# ---------------------------------------------------------------------------
# Baton helpers
# ---------------------------------------------------------------------------


def _build_nav_baton(screens_built: list[dict[str, Any]]) -> str:
    """Build a navigation context string from already-generated pages.

    Returns an empty string for the first page (no nav context yet). For
    subsequent pages, returns a human-readable nav map listing all previously
    generated pages and their slugs. The baton grows with each page, ensuring
    every page after the first is prompted with consistent navigation awareness.

    Args:
        screens_built: List of screen entry dicts from the baton loop.

    Returns:
        Empty string if no screens built yet; otherwise a navigation context block.
    """
    if not screens_built:
        return ""
    nav_lines = ["Navigation structure — link to these pages:"]
    for s in screens_built:
        nav_lines.append(f"  - {s['page_title']} \u2192 /{s['page_slug']}")
    return "\n".join(nav_lines)


def _build_page_prompt(
    design_markdown: str,
    page_title: str,
    page_slug: str,
    sections: list[str],
    nav_context: str,
) -> str:
    """Assemble the generation prompt for a single page.

    Prepends the design system Markdown, adds the page specification, optionally
    includes sections, and appends the nav baton context when present.

    Args:
        design_markdown: Raw Markdown from the locked design system.
        page_title: Human-readable page title (e.g. "Home").
        page_slug: URL slug (e.g. "home").
        sections: List of section names to include on the page.
        nav_context: Growing nav baton from ``_build_nav_baton``.

    Returns:
        The complete generation prompt string.
    """
    parts: list[str] = []
    if design_markdown:
        parts.append(f"DESIGN SYSTEM:\n{design_markdown}")
    parts.append(f"Generate the '{page_title}' page (slug: {page_slug})")
    if sections:
        parts.append(f"Sections: {', '.join(sections)}")
    if nav_context:
        parts.append(nav_context)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Navigation link injection — post-processing
# ---------------------------------------------------------------------------


class NavLinkRewriter(HTMLParser):
    """Rewrite ``<a href="/slug">`` anchors to absolute Supabase Storage URLs.

    Walks the HTML token stream via stdlib ``html.parser``. For each anchor tag
    found, strips the leading slash from the ``href`` value and checks whether
    the resulting slug exists in ``slug_to_url``. If it does, the href is
    replaced with the absolute Supabase Storage URL. All other content
    (end tags, data, declarations, comments, entity/char refs) is reproduced
    verbatim to preserve full HTML fidelity.

    Args:
        slug_to_url: Mapping of page slug (without leading slash) to absolute URL.

    Attributes:
        output: List of HTML string fragments; join with ``""`` for final HTML.
    """

    def __init__(self, slug_to_url: dict[str, str]) -> None:
        """Initialise with slug-to-URL mapping."""
        super().__init__()
        self.slug_to_url = slug_to_url
        self.output: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Rewrite href on anchor tags; emit all other tags unchanged."""
        if tag == "a":
            new_attrs: list[tuple[str, str | None]] = []
            for name, val in attrs:
                if name == "href" and val:
                    # Match /page-slug or page-slug (relative without leading slash)
                    slug = val.lstrip("/")
                    if slug in self.slug_to_url:
                        val = self.slug_to_url[slug]
                new_attrs.append((name, val))
            attrs = new_attrs
        attr_str = "".join(
            f' {k}="{v}"' if v is not None else f" {k}" for k, v in attrs
        )
        self.output.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag: str) -> None:
        """Emit closing tag verbatim."""
        self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        """Emit text content verbatim."""
        self.output.append(data)

    def handle_decl(self, decl: str) -> None:
        """Emit DOCTYPE and other declarations verbatim."""
        self.output.append(f"<!{decl}>")

    def handle_comment(self, data: str) -> None:
        """Emit HTML comments verbatim."""
        self.output.append(f"<!--{data}-->")

    def handle_entityref(self, name: str) -> None:
        """Emit named entity references verbatim."""
        self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """Emit numeric character references verbatim."""
        self.output.append(f"&#{name};")


async def inject_navigation_links(
    screens: list[dict[str, Any]],
    user_id: str,
    project_id: str,
) -> None:
    """Re-download, rewrite nav hrefs, and re-upload each page's HTML.

    For each screen in ``screens``, downloads the persisted HTML from its
    ``html_url``, runs ``NavLinkRewriter`` to replace ``/slug`` anchors with
    absolute sibling page URLs, then re-uploads the modified HTML to the same
    Supabase Storage path using upsert. This is a non-fatal operation — any
    failure is logged as a warning and execution continues to the next page.

    Args:
        screens: List of screen entry dicts (from ``build_all_pages`` baton loop).
                 Each dict must have ``page_slug``, ``screen_id``, and ``html_url``.
        user_id: Authenticated user UUID (used to construct storage path).
        project_id: App project UUID (used to construct storage path).
    """
    slug_to_url: dict[str, str] = {
        s["page_slug"]: s["html_url"]
        for s in screens
        if s.get("html_url")
    }
    supabase = get_service_client()

    async with httpx.AsyncClient() as client:
        for screen in screens:
            try:
                resp = await client.get(
                    screen["html_url"], follow_redirects=True, timeout=30.0
                )
                html_content = resp.text

                rewriter = NavLinkRewriter(slug_to_url)
                rewriter.feed(html_content)
                new_html = "".join(rewriter.output)

                # Re-upload to same path — upsert=true to overwrite in-place
                storage_path = (
                    f"{user_id}/{project_id}/{screen['screen_id']}/v0/screen.html"
                )
                loop = asyncio.get_event_loop()
                _path = storage_path
                _html_bytes = new_html.encode("utf-8")
                await loop.run_in_executor(
                    None,
                    lambda p=_path, b=_html_bytes: supabase.storage.from_(
                        _STITCH_ASSETS_BUCKET
                    ).upload(
                        path=p,
                        file=b,
                        file_options={"content-type": "text/html", "upsert": "true"},
                    ),
                )

            except Exception:
                logger.warning(
                    "Nav injection failed for page '%s' — skipping",
                    screen.get("page_slug", "unknown"),
                )
                # Non-fatal: page still works, just without rewritten nav links
