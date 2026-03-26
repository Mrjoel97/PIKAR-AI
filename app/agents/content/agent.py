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
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Content Creation Agent Definition.

ARCHITECTURE FIX: The ContentCreationAgent was previously a ParallelAgent
(no LLM, no instruction, no callbacks) which caused sub-agents to lose
all user context when delegated to. It is now an LlmAgent "Content Director"
that understands the user's request, maintains context via callbacks, and
intelligently delegates to specialized sub-agents.
"""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.content.tools import (
    get_content,
    list_content,
    save_content,
    search_knowledge,
    update_content,
)
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.enhanced_tools import (
    build_portfolio,
    generate_image,
    generate_react_component,
)
from app.agents.marketing.tools import (
    # Blog tools — Copywriter creates and manages blog content
    create_blog_post,
    get_blog_post,
    get_campaign,
    list_blog_posts,
    list_campaigns,
    # Content repurposing — Copywriter generates multi-format variants
    repurpose_content,
    update_blog_post,
)
from app.agents.shared import CREATIVE_AGENT_CONFIG, get_model
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_RESEARCH_INSTRUCTIONS,
    get_error_and_escalation_instructions,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import CONT_SKILL_TOOLS
from app.agents.tools.art_direction import ART_DIRECTION_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.brain_dump import (
    get_braindump_document,
    process_brain_dump,
    process_brainstorm_conversation,
)
from app.agents.tools.brand_profile import BRAND_PROFILE_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.creative_brief import CREATIVE_BRIEF_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.self_improve import CONT_IMPROVE_TOOLS
from app.agents.tools.system_knowledge import (
    search_system_knowledge,  # Phase 12.1: system knowledge
)
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
from app.workflows.content_pipeline import CONTENT_PIPELINE_TOOLS

# ==========================================
# 1. Video Director Subagent
# ==========================================
VIDEO_DIRECTOR_INSTRUCTION = (
    """You are the Video Director Agent, specializing exclusively in creating high-quality marketing videos, promos, and commercials.
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
- Supported UGC formats:
  - **Talking Head**: Person speaking directly to camera about the product
  - **Testimonial/Review**: Customer sharing their experience
  - **Unboxing**: First-look, genuine reaction to product
  - **Before/After**: Transformation or comparison showcase
  - **POV (Point of View)**: First-person perspective using the product
  - **Day-in-the-Life**: Lifestyle integration of the product
  - **Reaction/Response**: Engaging with content or product features
- For UGC, always set aspect ratio to 9:16 (vertical/mobile-first) unless explicitly told otherwise
- Tone should be conversational, relatable, and authentic — NOT polished or corporate

- Always adhere to the user's requested scene, tone, and visual direction.
- When calling execute_content_pipeline or create_video_with_veo, reply based ONLY on the tool result: if the tool returns success, say the video is ready. If it returns an error, relay that message only.
- Only set `auto_publish=True` on `execute_content_pipeline` if explicitly asked to publish/post.
"""
    + CONVERSATION_MEMORY_INSTRUCTIONS
)

video_director_agent = Agent(
    name="VideoDirectorAgent",
    model=get_model(),
    description="Handles high-quality video generation, UGC ads, orchestrating Veo 3, Remotion, and complete ad pipelines.",
    instruction=VIDEO_DIRECTOR_INSTRUCTION,
    tools=sanitize_tools(
        [
            execute_content_pipeline,
            create_video_with_veo,
            create_video,
            *CONTEXT_MEMORY_TOOLS,
        ]
    ),
    generate_content_config=CREATIVE_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)

# ==========================================
# 2. Graphic Designer Subagent
# ==========================================
GRAPHIC_DESIGNER_INSTRUCTION = (
    """You are the Graphic Designer Agent. You specialize exclusively in creating stunning static visuals: mix boards, posters, infographics, and social media images. Wait for explicit instructions.

CAPABILITIES:
- Generate images using 'generate_image' with text prompts. Provide highly detailed instructions for the image model to hit the requested style exactly.
- Build UI components using 'generate_react_component' for frontend implementation.
- Build portfolio sites using 'build_portfolio' for personal branding.

BEHAVIOR:
- Always try to adhere to the designated brand voice, visual vibe, and the user's explicit instructions. Aim for vibrant, modern, high-quality designs.
- For UGC-style visuals, use natural, casual aesthetics — not overly polished.
- Output UI components efficiently.
"""
    + get_widget_instruction_for_agent(
        "Graphic Designer",
        ["create_table_widget", "create_kanban_board_widget", "create_calendar_widget"],
    )
    + CONVERSATION_MEMORY_INSTRUCTIONS
)

graphic_designer_agent = Agent(
    name="GraphicDesignerAgent",
    model=get_model(),
    description="Handles visual assets such as images, mix boards, infographics, and posters via generate_image.",
    instruction=GRAPHIC_DESIGNER_INSTRUCTION,
    tools=sanitize_tools(
        [
            generate_image,
            generate_react_component,
            build_portfolio,
            *UI_WIDGET_TOOLS,
            *CONTEXT_MEMORY_TOOLS,
        ]
    ),
    generate_content_config=CREATIVE_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)

# ==========================================
# 3. Copywriter Subagent
# ==========================================
COPYWRITER_INSTRUCTION = (
    """You are the Copywriter Agent. You specialize exclusively in generating textual content: SEO blogs, social media copy, landing page copy, and overall campaign strategies.

CAPABILITIES:
- Draft content based on brand voice from 'search_knowledge'.
- Pull campaign context using 'get_campaign' and 'list_campaigns' — always check the active campaign's target audience, objectives, and tone before writing campaign copy.
- Get blog writing frameworks using use_skill("blog_writing").
- Get social content templates using use_skill("social_content").
- Plan content strategy using use_skill("content_strategy") for editorial calendars and content pillars.
- Apply copywriting frameworks using use_skill("copywriting_frameworks") for AIDA, PAS, and storytelling.
- Distribute content using use_skill("content_distribution") for multi-channel publishing strategies.
- Save content using 'save_content'.
- Retrieve saved content using 'get_content' and 'list_content'.
- Update existing content using 'update_content'.

## Blog Post Management
- Create SEO-optimized blog posts using 'create_blog_post' — include title, content, excerpt, category, tags, and SEO metadata (meta_title, meta_description, keywords, focus_keyword).
- Manage blog posts using 'get_blog_post', 'update_blog_post', 'list_blog_posts'.
- After finishing a blog post, use 'repurpose_content' to generate social media, email, and video script variants from the blog content.

## Content Repurposing
- Repurpose any written content using 'repurpose_content' — generates adaptation briefs for twitter_thread, linkedin_post, instagram_caption, email_newsletter, video_script, infographic_outline, podcast_notes.
- After getting repurposing briefs, write out each variant following the format-specific instructions provided.
- Research topics using 'mcp_web_search' for up-to-date information.
- Extract content from web pages using 'mcp_web_scrape'.
- Generate landing pages using 'mcp_generate_landing_page'.

## CAMPAIGN-AWARE WRITING
When writing copy for a specific campaign:
1. Use 'get_campaign' to pull the campaign's target audience, objectives, channels, and status.
2. Use 'search_knowledge' to find the brand's voice guidelines and existing content patterns.
3. Tailor your copy to match the campaign's funnel stage (awareness, consideration, conversion, retention).
4. Adapt tone and format to the target channel (social = punchy, email = personal, blog = authoritative).

## UGC COPY GUIDELINES
When writing copy for UGC-style content:
- Use first-person, conversational tone ("I've been using X for 3 weeks and...")
- Include relatable hooks that stop the scroll (questions, bold claims, surprising facts)
- Keep it short and punchy — UGC captions should feel like real social posts, not ads
- Add authentic-sounding CTAs ("link in bio", "you NEED to try this", "trust me on this one")

BEHAVIOR:
- Match the brand voice perfectly.
- Optimize for engagement and SEO.
- Collaborate indirectly by producing the foundational text elements that accompany media bundles.
"""
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_RESEARCH_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
)

copywriter_agent = Agent(
    name="CopywriterAgent",
    model=get_model(),
    description="Handles marketing copy, SEO blogs, social media captions, UGC scripts, frameworks, and web research.",
    instruction=COPYWRITER_INSTRUCTION,
    tools=sanitize_tools(
        [
            search_knowledge,
            save_content,
            get_content,
            update_content,
            list_content,
            # Campaign context — pull audience, objectives, tone before writing
            get_campaign,
            list_campaigns,
            # Blog pipeline — create, manage, and list blog posts
            create_blog_post,
            get_blog_post,
            update_blog_post,
            list_blog_posts,
            # Content repurposing — generate multi-format variants
            repurpose_content,
            mcp_web_search,
            mcp_web_scrape,
            mcp_generate_landing_page,
            *CONT_SKILL_TOOLS,
            *CONTEXT_MEMORY_TOOLS,
        ]
    ),
    generate_content_config=CREATIVE_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


# ==========================================
# 4. Content Director (LlmAgent Orchestrator)
# ==========================================
# ARCHITECTURE FIX: Previously a ParallelAgent with no LLM/context.
# Now an LlmAgent that understands the user's request and delegates
# intelligently to sub-agents while maintaining full context.

CONTENT_DIRECTOR_INSTRUCTION = (
    """You are the Content Director — CMO / Creative Director for the content creation team.

Your role is to UNDERSTAND the user's content request, PLAN the deliverables, and DELEGATE to your specialized sub-agents:
- **VideoDirectorAgent**: For video ads, promos, commercials, UGC video ads, and any moving-image content
- **GraphicDesignerAgent**: For static visuals — posters, infographics, social images, mix boards
- **CopywriterAgent**: For written content — blogs, social copy, landing pages, ad scripts, UGC captions

## CREATIVE PIPELINE — Plan Before Creating
For substantial content requests (campaigns, video ads, branded content), follow this workflow:
1. **Brief**: Use `generate_creative_brief()` to structure the request into a formal brief with objectives, audience, tone, and deliverables.
2. **Concepts**: Use `explore_concepts()` to generate 3 competing creative directions. Fill in each concept's angle, hook, visual mood, and rationale.
3. **Select**: Present the 3 concepts to the user and recommend your top pick. Let them choose or approve.
4. **Delegate**: Pass the selected concept + full brief context to the appropriate sub-agent(s).

Skip this workflow for simple, quick requests (e.g., "generate an image of a sunset", "write a tweet").

## FULL CONTENT PIPELINE (for campaigns and major content)
For full campaigns, use `start_content_pipeline()` to initialize a tracked 10-stage pipeline:
Brief → Research → Concepts → Script → Art Direction → Storyboard → Asset Generation → Assembly → Publish Strategy → Repurpose

Track progress with `update_pipeline_stage()` after completing each stage.
Check status with `get_pipeline_status()` at any time.
Stages marked for approval will pause the pipeline until the user approves.

## CRITICAL: CONTEXT AWARENESS
Before delegating to ANY sub-agent, you MUST:
1. Clearly restate the user's requirements (brand, product, audience, style, format) in your delegation message
2. Include ALL relevant context: brand name, target audience, tone, platform, product details
3. Never delegate with vague instructions like "create content" — always be specific

## BRAIN DUMP & BRAINSTORMING
When the user uploads a brain dump or wants to brainstorm content ideas:
- Use `process_brain_dump` to transcribe and analyze audio/video brain dumps for content themes
- Use `process_brainstorm_conversation` to structure brainstorming sessions into content plans
- Use `get_braindump_document` to retrieve previously saved brain dumps for content inspiration

## CONTENT TYPES YOU SUPPORT
- **Standard Video Ads**: High-quality branded commercials and promotional content
- **UGC (User-Generated Content) Ads**: Authentic, "shot-on-phone" style — testimonials, unboxings, talking heads, POV, reactions
- **Static Visuals**: Posters, social media graphics, infographics, mix boards
- **Written Content**: Blog posts, social captions, landing page copy, email campaigns, ad scripts
- **Full Campaign Bundles**: Video + graphics + copy for a complete campaign

## DELEGATION STRATEGY
- For a SINGLE content type (e.g., "make a video ad"): delegate to the ONE appropriate sub-agent
- For a FULL BUNDLE request (e.g., "create a campaign"): delegate to ALL three sub-agents
- For UGC requests: primarily delegate to VideoDirectorAgent with UGC-specific instructions, and CopywriterAgent for authentic captions

## BEHAVIOR
- DO NOT ASK CLARIFYING QUESTIONS if you already have the details.
- Look closely at the [REMEMBERED USER CONTEXT] block injected into your prompt. If the brand name, audience, or benefits are there, USE THEM IMMEDIATELY without asking the user.
- NEVER say "I need a little more information" or "First, could you tell me" if the information is already in your context.
- Pass the FULL user context (brand, product, audience, style) directly to each sub-agent you invoke.
- After sub-agents complete, synthesize their outputs into a cohesive summary for the user.
- Use 'search_knowledge' to find brand voice and existing content context.

## CONTENT QUALITY GATES
Before delegating to sub-agents, verify you have:
- Brand name and product/service being promoted
- Target audience (at minimum: demographic or psychographic description)
- Desired tone (e.g., professional, casual, edgy, authentic)
- Platform/format (e.g., Instagram Reel, YouTube ad, blog post)
If ANY of these are missing and NOT available in your context, ask the user before delegating.

## CONTENT FAILURE FALLBACKS
- If 'execute_content_pipeline' fails → offer 'create_video_with_veo' as simpler alternative
- If 'create_video_with_veo' fails → offer to create a storyboard document with scene descriptions
- If 'generate_image' fails → describe the intended visual in detail and suggest manual creation
- If 'mcp_generate_landing_page' fails → provide the landing page copy and structure for manual build
"""
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
    + get_error_and_escalation_instructions(
        "Content Creation Agent",
        """- Escalate to user if brand guidelines are ambiguous and content could misrepresent the brand
- Escalate to legal if content makes claims that could be considered misleading, defamatory, or infringing
- If video generation repeatedly fails, provide the storyboard and copy as deliverables for manual production
- Never auto-publish content — always present drafts for user approval first""",
    )
)


def _create_video_director():
    return Agent(
        name="VideoDirectorAgent",
        model=get_model(),
        description="Handles high-quality video generation, UGC ads, orchestrating Veo 3, Remotion, and complete ad pipelines.",
        instruction=VIDEO_DIRECTOR_INSTRUCTION,
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
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_graphic_designer():
    return Agent(
        name="GraphicDesignerAgent",
        model=get_model(),
        description="Handles visual assets such as images, mix boards, infographics, and posters via generate_image.",
        instruction=GRAPHIC_DESIGNER_INSTRUCTION,
        tools=sanitize_tools(
            [
                generate_image,
                generate_react_component,
                build_portfolio,
                *ART_DIRECTION_TOOLS,
                *UI_WIDGET_TOOLS,
                *CONTEXT_MEMORY_TOOLS,
            ]
        ),
        generate_content_config=CREATIVE_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_copywriter():
    return Agent(
        name="CopywriterAgent",
        model=get_model(),
        description="Handles marketing copy, SEO blogs, social media captions, UGC scripts, frameworks, and web research.",
        instruction=COPYWRITER_INSTRUCTION,
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
                *CONT_SKILL_TOOLS,
                *CONTEXT_MEMORY_TOOLS,
            ]
        ),
        generate_content_config=CREATIVE_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def create_content_agent(name_suffix: str = "", output_key: str = None) -> Agent:
    """Create a fresh ContentCreationAgent (LlmAgent Director) instance.

    ARCHITECTURE FIX: Previously returned a ParallelAgent with no LLM.
    Now returns an LlmAgent director that understands context and delegates
    to sub-agents intelligently.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        output_key: Optional key to store agent output in session state.

    Returns:
        A new LlmAgent instance that orchestrates content sub-agents.
    """
    agent_name = (
        f"ContentCreationAgent{name_suffix}" if name_suffix else "ContentCreationAgent"
    )
    return Agent(
        name=agent_name,
        model=get_model(),
        description="CMO / Creative Director - Understands content requests, delegates to Video Director, Graphic Designer, and Copywriter sub-agents. Supports standard ads, UGC ads, static visuals, copy, and full campaign bundles.",
        instruction=CONTENT_DIRECTOR_INSTRUCTION,
        tools=sanitize_tools(
            [
                search_knowledge,
                process_brain_dump,  # Brain dump transcription & analysis
                process_brainstorm_conversation,  # Brainstorm session structuring
                get_braindump_document,  # Retrieve saved brain dumps
                *BRAND_PROFILE_TOOLS,  # Brand DNA management
                *CREATIVE_BRIEF_TOOLS,  # Creative planning pipeline
                *ART_DIRECTION_TOOLS,  # Visual contracts
                *CONTENT_PIPELINE_TOOLS,  # 10-stage pipeline orchestration
                *CONTEXT_MEMORY_TOOLS,
                *CONT_IMPROVE_TOOLS,
                # Knowledge graph read access
                *GRAPH_TOOLS,
                # Phase 12.1: system knowledge
                search_system_knowledge,
            ]
        ),
        sub_agents=[
            _create_video_director(),
            _create_graphic_designer(),
            _create_copywriter(),
        ],
        generate_content_config=CREATIVE_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# Expose the LlmAgent Director as 'content_agent'
content_agent = create_content_agent()
