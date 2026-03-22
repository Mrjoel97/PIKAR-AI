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

"""Enhanced Agent Tools with Skills Integration.

This module contains tools with unique logic beyond simple skill wrappers.
For basic skill access, agents should call use_skill("skill_name") directly
via the *_SKILL_TOOLS provided by agent_skills.py.
"""

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from app.agents.tools import media
from app.skills import skills_registry
from app.skills.registry import AgentID

# =============================================================================
# Core Skills Access Tool
# =============================================================================


def use_skill(skill_name: str, agent_id: str | None = None, **kwargs: Any) -> dict:
    """Use a skill from the Skills Registry to get domain knowledge or execute a function.

    This is the primary interface for agents to access the skills system.
    Skills provide either:
    - Knowledge: Domain expertise as context/instructions
    - Functions: Executable logic with parameters

    Args:
        skill_name: Name of the skill to use (e.g., 'analyze_financial_statement').
        agent_id: Optional agent ID string (e.g., 'FIN', 'HR') for access control.
                  If not provided, no access control is enforced.
        **kwargs: Additional arguments to pass to function-based skills.

    Returns:
        Dictionary containing skill output, knowledge, or error message.
    """
    # Convert string agent_id to AgentID enum if provided
    parsed_agent_id = None
    if agent_id:
        try:
            parsed_agent_id = AgentID(agent_id)
        except ValueError:
            return {"success": False, "error": f"Invalid agent_id: '{agent_id}'"}

    return skills_registry.use_skill(skill_name, agent_id=parsed_agent_id, **kwargs)


def list_available_skills(category: str = None) -> dict:
    """List all available skills, optionally filtered by category.

    Args:
        category: Optional category filter (finance, hr, marketing, sales,
                  compliance, content, data, support, operations).

    Returns:
        Dictionary with list of available skill names and descriptions.
    """
    if category:
        skills = skills_registry.get_by_category(category)
    else:
        skills = skills_registry.list_all()

    return {
        "success": True,
        "count": len(skills),
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "has_implementation": s.implementation is not None,
            }
            for s in skills
        ],
    }


# =============================================================================
# Operations Agent Tools (unique logic)
# =============================================================================


def _validate_audit_target(target: str) -> str | None:
    """Validate that target is a URL (http/https), IP address, or relative path.

    Returns None if valid, or an error message if invalid.
    """
    # Check if it's a valid URL with http/https scheme
    parsed = urlparse(target)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return None

    # Check if it's a valid IP address (v4 or v6)
    try:
        ipaddress.ip_address(target)
        return None
    except ValueError:
        pass

    # Check if it's a relative file path (no scheme, no null bytes, no '..' traversal)
    if (
        not parsed.scheme
        and "\x00" not in target
        and not re.search(r"(^|[\\/])\.\.($|[\\/])", target)
        and not target.startswith("/")
        and not target.startswith("\\")
    ):
        return None

    return (
        "Invalid target. Must be an HTTP/HTTPS URL, an IP address, "
        "or a relative file path."
    )


def run_security_audit(target: str, audit_type: str = "general") -> dict:
    """Run a security audit on a target system or code.

    Access: OPS agents

    Args:
        target: IP, URL, or code path to audit.
        audit_type: 'general', 'active-directory', 'cloud'.

    Returns:
        Dictionary with audit results and vulnerabilities.
    """
    validation_error = _validate_audit_target(target)
    if validation_error:
        return {"error": validation_error}

    skill = (
        "active-directory-attacks"
        if audit_type == "active-directory"
        else "pentest-checklist"
    )
    return skills_registry.use_skill(skill, agent_id=AgentID.OPS, target=target)


def deploy_container(image_name: str, platform: str = "aws") -> dict:
    """Generate deployment configuration for containers.

    Access: OPS agents

    Args:
        image_name: Name of the container image.
        platform: Deployment platform (aws, gcp, azure).

    Returns:
        Dictionary with Dockerfiles and deployment scripts.
    """
    skill = "docker-expert"
    return skills_registry.use_skill(
        skill, agent_id=AgentID.OPS, context=f"Deploy {image_name} to {platform}"
    )


def architect_cloud_solution(requirements: str, provider: str = "aws") -> dict:
    """Design a cloud infrastructure solution.

    Access: OPS agents

    Args:
        requirements: System requirements and constraints.
        provider: Cloud provider (aws, gcp).

    Returns:
        Dictionary with architecture diagram description and IaC snippets.
    """
    skill = "aws-serverless" if provider == "aws" else "gcp-cloud-run"
    return skills_registry.use_skill(skill, agent_id=AgentID.OPS, context=requirements)


async def audit_user_setup_tool() -> dict:
    """Audit user's current agent configuration and suggest improvements.

    Access: OPS, EXEC agents

    Returns:
        Dictionary with audit score, metrics, and recommendations.
    """
    from app.services.journey_audit import audit_user_setup

    try:
        from app.services.request_context import get_current_user_id

        user_id = get_current_user_id()
        return await audit_user_setup(user_id)
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Data Analysis Agent Tools (unique logic)
# =============================================================================


def design_rag_pipeline(requirements: str) -> dict:
    """Design a RAG (Retrieval Augmented Generation) system architecture.

    Access: DATA agents

    Args:
        requirements: Requirements for the RAG system (data sources, latency, scale).

    Returns:
        Dictionary with vector DB choice, embedding model, and retrieval strategy.
    """
    return skills_registry.use_skill(
        "rag-implementation", agent_id=AgentID.DATA, context=requirements
    )


# =============================================================================
# Sales Agent Tools (unique logic)
# =============================================================================


def manage_hubspot(action: str, data: dict = None) -> dict:
    """Manage HubSpot CRM data.

    Access: SALES agents

    Args:
        action: 'create_contact', 'update_deal', 'log_activity'.
        data: Dictionary of fields to update/create.

    Returns:
        Dictionary with API response.
    """
    if data is None:
        data = {}
    return skills_registry.use_skill(
        "hubspot-integration", agent_id=AgentID.SALES, action=action, data=data
    )


# =============================================================================
# Marketing Agent Tools (unique logic)
# =============================================================================


def perform_seo_audit(url: str) -> dict:
    """Analyze a webpage for SEO performance.

    Access: MKT, CONT agents

    Args:
        url: URL of the page to audit.

    Returns:
        Dictionary with SEO score, issues, and recommendations.
    """
    return skills_registry.use_skill(
        "seo-fundamentals", agent_id=AgentID.MKT, target=url
    )


# =============================================================================
# Strategic Agent Tools (unique logic)
# =============================================================================


def generate_product_roadmap(product_name: str, timeframe: str = "12 months") -> dict:
    """Generate a strategic product roadmap.

    Access: STRAT agents

    Args:
        product_name: Name of the product.
        timeframe: Duration of the roadmap (default: 12 months).

    Returns:
        Dictionary with roadmap phases, milestones, and deliverables.
    """
    return skills_registry.use_skill(
        "product-manager-toolkit",
        agent_id=AgentID.STRAT,
        context=f"{product_name} over {timeframe}",
    )


# =============================================================================
# Content Creation Agent Tools (unique logic)
# =============================================================================


async def generate_image(prompt: str, size: str = "1024x1024") -> dict:
    """Generate an image from a text prompt.

    Access: CONT agents

    Args:
        prompt: Text description of the image to generate.
        size: Image dimensions (default: 1024x1024).

    Returns:
        Dictionary with generated image info.
    """
    # Parse dimensions from size string (e.g., "1024x1024")
    width, height = 1024, 1024
    if "x" in size:
        try:
            parts = size.split("x")
            width = int(parts[0])
            height = int(parts[1])
        except ValueError:
            pass

    return await media.generate_image(
        prompt=prompt, dimensions={"width": width, "height": height}
    )


async def generate_short_video(prompt: str, duration: int = 6) -> dict:
    """Generate a short video from a text prompt.

    Access: CONT agents

    Args:
        prompt: Text description of the video to generate.
        duration: Video duration in seconds (default: 6).

    Returns:
        Dictionary with generated video info.
    """
    return await media.generate_video(prompt=prompt, duration_seconds=duration)


def generate_remotion_video(
    requirements: str, duration_seconds: int = 15, video_type: str = "social_media"
) -> dict:
    """Generate a programmatic video using Remotion (React) for social media or marketing.

    Access: CONT agents

    Use this tool when the user asks to "create a video", "make a video for social media",
    "create a promotional video", or "generate a video post".

    Args:
        requirements: Detailed requirements for the video content, style, and message.
        duration_seconds: Target duration in seconds (default: 15).
        video_type: Type of video (e.g., 'social_media', 'promotional', 'informational').

    Returns:
        Dictionary with Remotion framework knowledge and code generation instructions.
    """
    # Get Remotion skill knowledge
    skill_result = skills_registry.use_skill("remotion", agent_id=AgentID.CONT)

    if not skill_result.get("success"):
        return skill_result

    return {
        "success": True,
        "framework": "Remotion (React)",
        "knowledge": skill_result.get("knowledge"),
        "instructions": f"Generate a Remotion composition for a {video_type} video. Requirements: {requirements}. Duration: {duration_seconds}s ({duration_seconds * 30} frames at 30fps). Output the comprehensive React code including necessary imports from 'remotion'.",
        "next_steps": [
            "1. Generate the React component code based on the requirements and knowledge.",
            "2. Ensure useCurrentFrame() and interpolate() are used for animations.",
            "3. Provide instructions to the user to save the file in the frontend/src/videos directory (or similar).",
        ],
    }


def generate_react_component(description: str) -> dict:
    """Generate a React component using best practices.

    Access: CONT agents

    Args:
        description: Description of the component functionality and style.

    Returns:
        Dictionary with React component code (TSX).
    """
    return skills_registry.use_skill(
        "react-patterns", agent_id=AgentID.CONT, context=description
    )


def build_portfolio(user_info: str) -> dict:
    """Create a structure for a personal portfolio site.

    Access: CONT agents

    Args:
        user_info: Information about the user (role, projects, skills).

    Returns:
        Dictionary with portfolio site structure and content.
    """
    return skills_registry.use_skill(
        "interactive-portfolio", agent_id=AgentID.CONT, context=user_info
    )
