# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Design Brief Service — research orchestration and design system synthesis.

Coordinates Tavily web research and Gemini Flash synthesis to produce
a complete design system document, color/typography/spacing tokens,
sitemap, and a phase-based build plan from a creative brief.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

try:
    from google import genai
    from google.genai import types as genai_types
except (
    Exception
):  # pragma: no cover - import guard for environments without google-genai
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

from app.mcp.tools.web_search import TavilySearchTool
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

DESIGN_SYSTEM_PROMPT = """You are an expert UI/UX designer creating a complete design system from a creative brief and web research.

Creative Brief:
{brief}

Research Findings:
{research}

Produce the following sections in EXACT order with EXACT section markers:

DESIGN_SYSTEM_MARKDOWN:
[Full markdown document covering brand identity, design principles, component guidelines]

PALETTE:
[JSON array of color objects, e.g. [{{"hex": "#F5E6D3", "name": "Warm Cream"}}, ...]]

TYPOGRAPHY:
[JSON object, e.g. {{"heading": "Playfair Display", "body": "Lato", "scale": "1.25"}}]

SPACING:
[JSON object, e.g. {{"base_unit": 8, "section_padding": 64, "card_padding": 24}}]

SITEMAP_JSON:
[JSON array of page objects, e.g. [{{"page": "home", "title": "Homepage", "sections": ["hero", "features"], "device_targets": ["DESKTOP", "MOBILE"]}}, ...]]

Important: Each section must start on a new line with the exact marker followed by a newline.
Output valid JSON for PALETTE, TYPOGRAPHY, SPACING, and SITEMAP_JSON sections."""

BUILD_PLAN_PROMPT = """You are a technical project planner creating a phased build plan from a sitemap and design system.

Sitemap:
{sitemap}

Design System Summary:
{design_summary}

Create a JSON array of build phases. Each phase should group related screens and specify dependencies.

Output ONLY a valid JSON array with this structure:
[
  {{
    "phase": 1,
    "label": "Phase label",
    "screens": [
      {{"name": "Screen Name", "page": "page-slug", "device": "DESKTOP"}},
      {{"name": "Screen Name Mobile", "page": "page-slug", "device": "MOBILE"}}
    ],
    "dependencies": []
  }},
  ...
]

Rules:
- Group screens by page — one phase per page is a good default
- device must be "DESKTOP" or "MOBILE" based on the page's device_targets
- dependencies is a list of phase numbers that must complete before this phase
- Output ONLY the JSON array, no other text"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_design_research(
    creative_brief: dict,
    project_id: str,
    user_id: str,
) -> AsyncGenerator[dict, None]:
    """Orchestrate design research: search, synthesize, save, and stream progress.

    Args:
        creative_brief: Dict with keys like "what", "vibe", "audience", etc.
        project_id: UUID of the app project.
        user_id: UUID of the owning user.

    Yields:
        Progress event dicts with at minimum a "step" key.
        Steps in order: "searching", "synthesizing", "saving", "ready".
        On error: {"step": "error", "message": "..."}.
    """
    if genai is None:
        logger.error("run_design_research: google-genai unavailable")
        yield {"step": "error", "message": "Gemini not available"}
        return

    yield {"step": "searching", "message": "Researching design space..."}

    # Build search queries from the creative brief
    what = creative_brief.get("what", "website")
    vibe = creative_brief.get("vibe", "modern")
    queries = [
        f"{what} design inspiration {vibe} aesthetic",
        f"{what} competitor websites UI design trends",
    ]

    search_tool = TavilySearchTool()
    try:
        search_results = await asyncio.gather(
            *[
                search_tool.search(q, max_results=5, search_depth="basic")
                for q in queries
            ]
        )
    except Exception as exc:
        logger.warning("Design research search failed: %s", exc)
        search_results = []

    research_summary = _flatten_search_results(list(search_results))

    yield {"step": "synthesizing", "message": "Generating design brief..."}

    try:
        client = genai.Client()
        prompt = DESIGN_SYSTEM_PROMPT.format(
            brief=json.dumps(creative_brief),
            research=research_summary,
        )
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=3000,
            ),
        )
        design_doc = _parse_design_response(response.text)
    except Exception as exc:
        logger.error("Design synthesis failed: %s", exc)
        yield {"step": "error", "message": f"Synthesis failed: {exc}"}
        return

    yield {"step": "saving", "message": "Saving design brief..."}

    try:
        await _persist_design_draft(design_doc, project_id, user_id)
    except Exception as exc:
        logger.warning("Failed to persist design draft: %s", exc)
        # Non-fatal — still return the design doc

    yield {"step": "ready", "data": design_doc}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _flatten_search_results(results: list[dict]) -> str:
    """Flatten multiple Tavily search result sets into a single summary string.

    Args:
        results: List of Tavily result dicts, each with a "results" list
                 containing {"title": ..., "content": ...} items.

    Returns:
        A single concatenated string of titles and content snippets.
    """
    parts: list[str] = []
    for track_result in results:
        if not isinstance(track_result, dict):
            continue
        for item in track_result.get("results", []):
            title = item.get("title", "")
            content = item.get("content", "")
            if title or content:
                parts.append(f"{title}: {content}")
    return "\n".join(parts)


def _parse_design_response(text: str) -> dict:
    """Parse a structured Gemini design system response into typed fields.

    Expects the response to contain section markers:
      DESIGN_SYSTEM_MARKDOWN:, PALETTE:, TYPOGRAPHY:, SPACING:, SITEMAP_JSON:

    Args:
        text: Raw Gemini response text.

    Returns:
        Dict with keys: raw_markdown (str), colors (list), typography (dict),
        spacing (dict), sitemap (list).
    """

    def _extract_section(
        content: str, start_marker: str, end_markers: list[str]
    ) -> str:
        """Extract text between start_marker and the first end_marker found."""
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return ""
        start_idx += len(start_marker)
        end_idx = len(content)
        for em in end_markers:
            idx = content.find(em, start_idx)
            if idx != -1 and idx < end_idx:
                end_idx = idx
        return content[start_idx:end_idx].strip()

    raw_markdown = _extract_section(
        text,
        "DESIGN_SYSTEM_MARKDOWN:",
        ["PALETTE:", "TYPOGRAPHY:", "SPACING:", "SITEMAP_JSON:"],
    )

    palette_text = _extract_section(
        text, "PALETTE:", ["TYPOGRAPHY:", "SPACING:", "SITEMAP_JSON:"]
    )
    typography_text = _extract_section(
        text, "TYPOGRAPHY:", ["SPACING:", "SITEMAP_JSON:"]
    )
    spacing_text = _extract_section(text, "SPACING:", ["SITEMAP_JSON:"])
    sitemap_text = _extract_section(text, "SITEMAP_JSON:", [])

    def _safe_json(raw: str, default):  # type: ignore[return]
        """Attempt JSON parse; return default on failure."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return default

    return {
        "raw_markdown": raw_markdown,
        "colors": _safe_json(palette_text, []),
        "typography": _safe_json(typography_text, {}),
        "spacing": _safe_json(spacing_text, {}),
        "sitemap": _safe_json(sitemap_text, []),
    }


async def _persist_design_draft(
    design_doc: dict, project_id: str, user_id: str
) -> None:
    """Upsert design_systems and update app_projects with the design draft.

    Args:
        design_doc: Parsed design document from _parse_design_response.
        project_id: UUID of the app project.
        user_id: UUID of the owning user.
    """
    supabase = get_service_client()

    supabase.table("design_systems").upsert(
        {
            "project_id": project_id,
            "user_id": user_id,
            "colors": design_doc.get("colors", []),
            "typography": design_doc.get("typography", {}),
            "spacing": design_doc.get("spacing", {}),
            "raw_markdown": design_doc.get("raw_markdown", ""),
            "locked": False,
        },
        on_conflict="project_id",
    ).execute()

    supabase.table("app_projects").update(
        {
            "design_system": {
                "colors": design_doc.get("colors", []),
                "typography": design_doc.get("typography", {}),
                "spacing": design_doc.get("spacing", {}),
            },
            "sitemap": design_doc.get("sitemap", []),
        }
    ).eq("id", project_id).execute()


async def _generate_build_plan(sitemap: list[dict], design_system: dict) -> list[dict]:
    """Generate a phased build plan from the sitemap and design system.

    Calls Gemini Flash to produce a JSON array of build phases.
    Falls back to one phase per sitemap page (sequential) on any error.

    Args:
        sitemap: List of page dicts from _parse_design_response.
        design_system: Design tokens dict (colors, typography, spacing).

    Returns:
        List of phase dicts with keys: phase (int), label (str),
        screens (list of {name, page, device}), dependencies (list of ints).
    """
    fallback = _build_fallback_plan(sitemap)

    if genai is None:
        logger.warning("_generate_build_plan: google-genai unavailable, using fallback")
        return fallback

    try:
        client = genai.Client()
        design_summary = json.dumps(
            {
                k: design_system.get(k)
                for k in ("colors", "typography", "spacing")
                if k in design_system
            }
        )
        prompt = BUILD_PLAN_PROMPT.format(
            sitemap=json.dumps(sitemap),
            design_summary=design_summary,
        )
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2000,
                response_mime_type="application/json",
            ),
        )
        plan = json.loads(response.text)
        if not isinstance(plan, list):
            logger.warning(
                "_generate_build_plan: unexpected response shape, using fallback"
            )
            return fallback

        # Validate each phase has required keys
        validated = []
        for item in plan:
            if all(k in item for k in ("phase", "label", "screens", "dependencies")):
                validated.append(item)

        return validated if validated else fallback

    except Exception as exc:
        logger.warning("_generate_build_plan failed: %s — using fallback", exc)
        return fallback


def _build_fallback_plan(sitemap: list[dict]) -> list[dict]:
    """Generate a simple sequential build plan: one phase per sitemap page.

    Args:
        sitemap: List of page dicts.

    Returns:
        List of phase dicts with sequential dependencies.
    """
    phases = []
    for idx, page in enumerate(sitemap):
        phase_num = idx + 1
        page_slug = page.get("page", f"page-{phase_num}")
        page_title = page.get("title", page_slug.title())
        device_targets = page.get("device_targets", ["DESKTOP"])
        screens = [
            {
                "name": f"{page_title} {device.title()}",
                "page": page_slug,
                "device": device,
            }
            for device in device_targets
        ]
        phases.append(
            {
                "phase": phase_num,
                "label": page_title,
                "screens": screens,
                "dependencies": list(range(1, phase_num)),
            }
        )
    return phases
