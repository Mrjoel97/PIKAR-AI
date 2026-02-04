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

"""Content Creation Agent Definition."""

from google.adk.agents import Agent

from app.agents.shared import get_model
from app.agents.content.tools import (
    search_knowledge,
    save_content,
    get_content,
    update_content,
    list_content,
)
from app.agents.enhanced_tools import (
    use_skill,
    list_available_skills,
    get_blog_writing_framework,
    get_social_content_templates,
    generate_image,
    generate_short_video,
    generate_remotion_video,
    generate_react_component,
    build_portfolio,
)
from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape, mcp_generate_landing_page


CONTENT_AGENT_INSTRUCTION = """You are the Content Creation Agent. You generate high-quality marketing content including text, images, and videos.

CAPABILITIES:
- Draft content based on brand voice from 'search_knowledge'.
- Get blog writing frameworks using 'get_blog_writing_framework'.
- Get social content templates using 'get_social_content_templates'.
- Generate images using 'generate_image' with text prompts.
- Generate short videos using 'generate_short_video' with text prompts.
- Create social media and programmatic videos using 'generate_remotion_video' with Remotion (React).
- Design UI components using 'generate_react_component' for frontend implementation.
- Build portfolio sites using 'build_portfolio' for personal branding.
- Save content using 'save_content'.
- Retrieve saved content using 'get_content' and 'list_content'.
- Update existing content using 'update_content'.
- Research topics using 'mcp_web_search' for up-to-date information.
- Extract content from web pages using 'mcp_web_scrape'.
- Generate landing pages using 'mcp_generate_landing_page'.

BEHAVIOR:
- Match the user's brand voice.
- Optimize for engagement and SEO.
- Use skills for professional content frameworks.
- Always offer to generate supporting images/videos.
- Save and iterate on your best work.
- Use web search for trending topics and research."""


CONTENT_AGENT_TOOLS = [
    search_knowledge,
    save_content,
    get_content,
    update_content,
    list_content,
    get_blog_writing_framework,
    get_social_content_templates,
    generate_image,
    generate_short_video,
    generate_remotion_video,
    generate_react_component,
    build_portfolio,
    mcp_web_search,
    mcp_web_scrape,
    mcp_generate_landing_page,
    use_skill,
    list_available_skills,
]


# Singleton instance for direct import
content_agent = Agent(
    name="ContentCreationAgent",
    model=get_model(),
    description="CMO / Creative Director - Creates marketing copy, blog posts, social media content, images, and videos",
    instruction=CONTENT_AGENT_INSTRUCTION,
    tools=CONTENT_AGENT_TOOLS,
)


def create_content_agent(name_suffix: str = "") -> Agent:
    """Create a fresh ContentCreationAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"ContentCreationAgent{name_suffix}" if name_suffix else "ContentCreationAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="CMO / Creative Director - Creates marketing copy, blog posts, social media content, images, and videos",
        instruction=CONTENT_AGENT_INSTRUCTION,
        tools=CONTENT_AGENT_TOOLS,
    )
