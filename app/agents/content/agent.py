# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Content Creation Agent — built on PikarBaseAgent (W4-Pilot).

The director surface (model, tools, lifecycle callbacks, ops config) is
assembled by :class:`~app.agents.base_agent.PikarBaseAgent` from
``instructions.md`` + ``operations.yaml`` + :func:`build_tools_manifest`.

The 3 specialist sub-agents (Video Director, Graphic Designer,
Copywriter) stay on the legacy :class:`PikarAgent` shim — they are
internal to the content director, not standalone specialists in the
agent operating model spec sense. The factory passes them through to
``PikarBaseAgent`` via the ADK ``sub_agents=`` kwarg (forwarded by
``**extra``).

Backward-compat path: legacy workflow factories (``app/workflows/*.py``)
call ``create_content_agent()`` positionally with ``name_suffix``,
``output_key``, and ``persona``. Those callers still get a working
agent — we route them through the same :class:`PikarBaseAgent` factory
with synthesized identity, since pre-W4 the agent was rebuilt fresh
per workflow step anyway.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.agents.base_agent import PikarAgent, PikarBaseAgent
from app.agents.content.tools import (
    build_tools_manifest,
    get_content,
    list_content,
    save_content,
    update_content,
)
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
    tool_progress_before_tool_callback,
)
from app.agents.enhanced_tools import (
    build_portfolio,
    generate_image,
    generate_images,
    generate_react_component,
)
from app.agents.marketing.tools import (
    create_blog_post,
    get_blog_post,
    get_campaign,
    list_blog_posts,
    list_campaigns,
    repurpose_content,
    update_blog_post,
)
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.shared import CREATIVE_AGENT_CONFIG, get_model
from app.agents.tools.ad_copy_tools import AD_COPY_TOOLS
from app.agents.tools.agent_skills import CONT_SKILL_TOOLS
from app.agents.tools.art_direction import ART_DIRECTION_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.knowledge import search_knowledge
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import (
    mcp_generate_landing_page,
    mcp_web_scrape,
    mcp_web_search,
)
from app.mcp.tools.canva_media import (
    create_video,
    create_video_with_veo,
    execute_content_pipeline,
)
from app.skills.registry import AgentID

_AGENT_DIR = Path(__file__).parent
_INSTRUCTIONS_PATH = _AGENT_DIR / "instructions.md"
_OPS_CONFIG_PATH = _AGENT_DIR / "operations.yaml"


# =============================================================================
# Sub-agent factories — internal PikarAgent specialists owned by the director.
# =============================================================================
#
# These three remain as plain :class:`PikarAgent` instances (the legacy
# ADK shim). They are NOT migrated to ``PikarBaseAgent`` because they are
# not standalone specialists in the agent operating model spec sense —
# they receive their delegation context from the director's prompt and do
# not own their own ``operations.yaml`` or initiative phases.


_VIDEO_DIRECTOR_INSTRUCTION = """You are the Video Director Agent, specializing exclusively in creating high-quality marketing videos, promos, and commercials.
Your ONLY job is to handle video generation tasks when requested. Wait for explicit instructions to create.

CAPABILITIES:
- Plan video strategy using use_skill("video_content_strategy") for formats, platforms, and production planning.
- Create high-quality, orchestrator-driven video ad campaigns using 'execute_content_pipeline'. This completely handles Storyboarding, Gemini Image, Veo 3.1, Remotion, and Social Copy in one go. Apply the user's requested visual style or brand guidelines. Use this whenever the user asks for a high-quality video ad, premium promo content, or an engaging social media commercial.
- Create simple videos using 'create_video_with_veo' with a text prompt and duration. Short clips (≤8s) use VEO 3; longer videos use server-side Remotion. The user receives one playable MP4 stored in Knowledge Vault → Media.
- Create multi-scene/programmatic videos using 'create_video' when you need explicit scene lists and Remotion structure.

## UGC (User-Generated Content) AD CREATION
When the user asks for UGC-style ads, authentic-looking content, testimonial videos, or "shot-on-phone" style:
- Use 'execute_content_pipeline' with `nano_banana_mode="off"` for a natural, authentic look
- Set the prompt to emphasize UGC characteristics: casual framing, natural lighting, handheld camera feel, authentic testimonial tone
- Supported UGC formats include talking head, testimonial/review, unboxing, before/after, POV, day-in-the-life, and reaction/response.
- For UGC, always set aspect ratio to 9:16 (vertical/mobile-first) unless explicitly told otherwise
- Tone should be conversational, relatable, and authentic — NOT polished or corporate

- Always adhere to the user's requested scene, tone, and visual direction.
- When calling execute_content_pipeline or create_video_with_veo, reply based ONLY on the tool result: if the tool returns success, say the video is ready. If it returns an error, relay that message only.
- Only set `auto_publish=True` on `execute_content_pipeline` if explicitly asked to publish/post.
"""

_GRAPHIC_DESIGNER_INSTRUCTION = """You are the Graphic Designer Agent. You specialize exclusively in creating stunning static visuals: mix boards, posters, infographics, and social media images. Wait for explicit instructions.

CAPABILITIES:
- Generate a single image using 'generate_image' with a text prompt. Provide highly detailed instructions for the image model to hit the requested style exactly.
- Generate MULTIPLE images in ONE turn using 'generate_images' with a list of prompts. ALWAYS use this — never call 'generate_image' more than once in a turn — when the user asks for variations, options, "two/three/N images", thumbnails sets, or any side-by-side comparison.
- For square social-ready images for Instagram posts and similar channels, call `generate_image(prompt, size="1080x1080")` directly.
- Build UI components using 'generate_react_component' for frontend implementation.
- Build portfolio sites using 'build_portfolio' for personal branding.

BEHAVIOR:
- Always try to adhere to the designated brand voice, visual vibe, and the user's explicit instructions. Aim for vibrant, modern, high-quality designs.
- For UGC-style visuals, use natural, casual aesthetics — not overly polished.
- Output UI components efficiently.
"""

_COPYWRITER_INSTRUCTION = """You are the Copywriter Agent. You specialize exclusively in generating textual content: SEO blogs, social media copy, landing page copy, ad copy, and overall campaign strategies.

CAPABILITIES:
- Draft content based on brand voice from 'search_knowledge'.
- Pull campaign context using 'get_campaign' and 'list_campaigns' — always check the active campaign's target audience, objectives, and tone before writing campaign copy.
- Save content using 'save_content'; retrieve via 'get_content' / 'list_content'; update via 'update_content'.
- Create SEO-optimized blog posts using 'create_blog_post' — include title, content, excerpt, category, tags, and SEO metadata.
- Manage blog posts using 'get_blog_post', 'update_blog_post', 'list_blog_posts'.
- After finishing a blog post, use 'repurpose_content' to generate social media, email, and video script variants.
- Generate platform-specific ad copy (Google Ads / Meta Ads) via the ad copy tools — respect character limits exactly.
- Research topics using 'mcp_web_search'; extract page content via 'mcp_web_scrape'; generate landing pages via 'mcp_generate_landing_page'.

BEHAVIOR:
- Match the brand voice perfectly.
- Optimize for engagement and SEO.
- Collaborate indirectly by producing the foundational text elements that accompany media bundles.
"""


def _create_video_director() -> PikarAgent:
    return PikarAgent(
        name="VideoDirectorAgent",
        model=get_model(),
        description=(
            "Handles high-quality video generation, UGC ads, orchestrating "
            "Veo 3, Remotion, and complete ad pipelines."
        ),
        instruction=_VIDEO_DIRECTOR_INSTRUCTION,
        tools=sanitize_tools(
            [
                execute_content_pipeline,
                create_video_with_veo,
                create_video,
                *ART_DIRECTION_TOOLS,
                *CONTEXT_MEMORY_TOOLS,
            ]
        ),
        generate_content_config=CREATIVE_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        before_tool_callback=tool_progress_before_tool_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_graphic_designer() -> PikarAgent:
    return PikarAgent(
        name="GraphicDesignerAgent",
        model=get_model(),
        description=(
            "Handles visual assets such as images, mix boards, infographics, "
            "and posters via generate_image / generate_images."
        ),
        instruction=_GRAPHIC_DESIGNER_INSTRUCTION,
        tools=sanitize_tools(
            [
                generate_image,
                generate_images,
                generate_react_component,
                build_portfolio,
                *ART_DIRECTION_TOOLS,
                *UI_WIDGET_TOOLS,
                *CONTEXT_MEMORY_TOOLS,
            ]
        ),
        generate_content_config=CREATIVE_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        before_tool_callback=tool_progress_before_tool_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_copywriter() -> PikarAgent:
    return PikarAgent(
        name="CopywriterAgent",
        model=get_model(),
        description=(
            "Handles marketing copy, SEO blogs, social media captions, ad "
            "copy (Google/Meta), UGC scripts, frameworks, and web research."
        ),
        instruction=_COPYWRITER_INSTRUCTION,
        tools=sanitize_tools(
            [
                search_knowledge,
                save_content,
                get_content,
                update_content,
                list_content,
                get_campaign,
                list_campaigns,
                create_blog_post,
                get_blog_post,
                update_blog_post,
                list_blog_posts,
                repurpose_content,
                mcp_web_search,
                mcp_web_scrape,
                mcp_generate_landing_page,
                *AD_COPY_TOOLS,
                *CONT_SKILL_TOOLS,
                *CONTEXT_MEMORY_TOOLS,
            ]
        ),
        generate_content_config=CREATIVE_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        before_tool_callback=tool_progress_before_tool_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Director factory — the W4-Pilot PikarBaseAgent.
# =============================================================================


def create_content_agent(
    name_suffix: str = "",
    output_key: str | None = None,
    persona: str | None = None,
    *,
    user_id: UUID | None = None,
    persona_id: str | None = None,
    **extra: Any,
) -> PikarBaseAgent:
    """Build a fresh ContentCreationAgent (director) bound to a user + persona.

    Accepts both the W4 keyword form (``user_id=``, ``persona_id=``) and
    the legacy positional form (``name_suffix``, ``output_key``,
    ``persona``) used by ``app/workflows/*.py`` factories. Legacy callers
    get a synthesized ``user_id`` so the agent boots; the workflow engine
    re-binds the per-user context at invocation time.

    The director is a :class:`PikarBaseAgent`; its 3 sub-agents (Video
    Director, Graphic Designer, Copywriter) are plain :class:`PikarAgent`
    instances built per call so each director gets a fresh closure-bound
    sub-agent set.
    """
    _ = name_suffix  # legacy positional arg — agent name now derived from AgentID
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    bound_persona = persona_id or persona or "default"
    bound_user = user_id if user_id is not None else uuid4()
    return PikarBaseAgent(
        agent_id=AgentID.CONT,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config_path=_OPS_CONFIG_PATH,
        user_id=bound_user,
        persona_id=bound_persona,
        description=(
            "CMO / Creative Director - Understands content requests, "
            "delegates to Video Director, Graphic Designer, and "
            "Copywriter sub-agents."
        ),
        generate_content_config=CREATIVE_AGENT_CONFIG,
        output_key=output_key,
        sub_agents=[
            _create_video_director(),
            _create_graphic_designer(),
            _create_copywriter(),
        ],
        **extra,
    )


# Module-level singleton retained as a sentinel for legacy callers
# (``specialized_agents.SPECIALIZED_AGENTS`` filters out ``None``).
content_agent: PikarAgent | None = None


__all__ = ["content_agent", "create_content_agent"]
