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

This module provides skill-enhanced tools that agents can use to access
domain-specific knowledge and capabilities from the Skills Registry.

Each tool is associated with specific agent IDs for access control.
"""

from typing import Any
from app.skills import skills_registry
from app.skills.registry import AgentID
from app.agents.tools import media



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
# Financial Agent Enhanced Tools
# Access: FIN, EXEC
# =============================================================================

def analyze_financial_health() -> dict:
    """Analyze financial health using the analyze_financial_statement skill.
    
    Access: FIN, EXEC agents
    
    Returns:
        Dictionary containing the financial analysis framework and guidance.
    """
    return skills_registry.use_skill("analyze_financial_statement", agent_id=AgentID.FIN)


def get_revenue_forecast_guidance() -> dict:
    """Get revenue forecasting methodology and framework.
    
    Access: FIN, DATA, STRAT agents
    
    Returns:
        Dictionary with forecasting frameworks and best practices.
    """
    return skills_registry.use_skill("forecast_revenue_growth", agent_id=AgentID.FIN)


def calculate_burn_rate_guidance() -> dict:
    """Get burn rate calculation guidance for startups.
    
    Access: FIN, EXEC agents
    
    
    Returns:
        Dictionary with bottleneck analysis methodology.
    """
    return skills_registry.use_skill("process_bottleneck_analysis", agent_id=AgentID.OPS)


def get_sop_template() -> dict:
    """Get Standard Operating Procedure template and guidelines.
    
    Access: OPS, HR agents
    
    Returns:
        Dictionary with SOP structure and writing guidelines.
    """
    return skills_registry.use_skill("sop_generation", agent_id=AgentID.OPS)


def run_security_audit(target: str, audit_type: str = "general") -> dict:
    """Run a security audit on a target system or code.
    
    Access: OPS agents
    
    Args:
        target: IP, URL, or code path to audit.
        audit_type: 'general', 'active-directory', 'cloud'.
        
    Returns:
        Dictionary with audit results and vulnerabilities.
    """
    skill = "active-directory-attacks" if audit_type == "active-directory" else "pentest-checklist"
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
    return skills_registry.use_skill(skill, agent_id=AgentID.OPS, context=f"Deploy {image_name} to {platform}")


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


# =============================================================================
# Data Analysis Agent Enhanced Tools  
# Access: DATA, OPS
# =============================================================================

def get_anomaly_detection_guidance() -> dict:
    """Get framework for detecting data anomalies and outliers.
    
    Access: DATA, OPS agents
    
    Returns:
        Dictionary with anomaly detection methods and thresholds.
    """
    return skills_registry.use_skill("anomaly_detection", agent_id=AgentID.DATA)


def get_trend_analysis_framework() -> dict:
    """Get methodology for analyzing data trends.
    
    Access: DATA, FIN, STRAT agents
    
    Returns:
        Dictionary with trend analysis techniques and reporting structure.
    """
    return skills_registry.use_skill("trend_analysis", agent_id=AgentID.DATA)


def design_rag_pipeline(requirements: str) -> dict:
    """Design a RAG (Retrieval Augmented Generation) system architecture.
    
    Access: DATA agents
    
    Args:
        requirements: Requirements for the RAG system (data sources, latency, scale).
        
    Returns:
        Dictionary with vector DB choice, embedding model, and retrieval strategy.
    """
    return skills_registry.use_skill("rag-implementation", agent_id=AgentID.DATA, context=requirements)


# =============================================================================
# Operations Agent Enhanced Tools
# Access: OPS
# =============================================================================

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


def analyze_process_bottlenecks() -> dict:
    """Get framework for analyzing customer sentiment in support tickets.
    
    Access: SUPP agents
    
    Returns:
        Dictionary with bottleneck analysis methodology.
    """
    return skills_registry.use_skill("process_bottleneck_analysis", agent_id=AgentID.OPS)


# =============================================================================
# Customer Support Agent Enhanced Tools
# Access: SUPP
# =============================================================================

def analyze_ticket_sentiment() -> dict:
    """Get framework for analyzing customer sentiment in support tickets.
    
    Access: SUPP agents
    
    Returns:
        Dictionary with sentiment classification and response templates.
    """
    return skills_registry.use_skill("ticket_sentiment_analysis", agent_id=AgentID.SUPP)


def assess_churn_risk() -> dict:
    """Get framework for identifying customers at risk of churning.
    
    Access: SUPP, SALES agents
    
    Returns:
        Dictionary with churn indicators and intervention playbook.
    """
    return skills_registry.use_skill("churn_risk_indicators", agent_id=AgentID.SUPP)


# =============================================================================
# Sales Agent Enhanced Tools
# Access: SALES
# =============================================================================

def get_lead_qualification_framework() -> dict:
    """Get lead qualification frameworks (BANT, MEDDIC, CHAMP).
    
    Access: SALES agents
    
    Returns:
        Dictionary with qualification criteria and scoring matrix.
    """
    return skills_registry.use_skill("lead_qualification_framework", agent_id=AgentID.SALES)


def get_objection_handling_scripts() -> dict:
    """Get objection handling techniques and response scripts.
    
    Access: SALES agents
    
    Returns:
        Dictionary with LAER method and common objection responses.
    """
    return skills_registry.use_skill("objection_handling", agent_id=AgentID.SALES)


def get_competitive_analysis_framework() -> dict:
    """Get framework for analyzing competitors.
    
    Access: SALES, MKT, STRAT agents
    
    Returns:
        Dictionary with competitive intelligence methodology.
    """
    return skills_registry.use_skill("competitive_analysis", agent_id=AgentID.SALES)


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
    return skills_registry.use_skill("hubspot-integration", agent_id=AgentID.SALES, action=action, data=data)


# =============================================================================
# Marketing Agent Enhanced Tools
# Access: MKT, CONT
# =============================================================================

def generate_campaign_ideas() -> dict:
    """Get campaign ideation framework and theme generators.
    
    Access: MKT, CONT agents
    
    Returns:
        Dictionary with campaign strategy and theme formulas.
    """
    return skills_registry.use_skill("campaign_ideation", agent_id=AgentID.MKT)


def get_seo_checklist() -> dict:
    """Get comprehensive SEO audit and optimization checklist.
    
    Access: MKT, CONT agents
    
    Returns:
        Dictionary with on-page, off-page, and technical SEO checklist.
    """
    return skills_registry.use_skill("seo_checklist", agent_id=AgentID.MKT)


def get_social_media_guide() -> dict:
    """Get platform-specific social media best practices.
    
    Access: MKT, CONT agents
    
    Returns:
        Dictionary with posting guidelines per platform.
    """
    return skills_registry.use_skill("social_media_guide", agent_id=AgentID.MKT)


def perform_seo_audit(url: str) -> dict:
    """Analyze a webpage for SEO performance.
    
    Access: MKT, CONT agents
    
    Args:
        url: URL of the page to audit.
        
    Returns:
        Dictionary with SEO score, issues, and recommendations.
    """
    return skills_registry.use_skill("seo-fundamentals", agent_id=AgentID.MKT, target=url)


# =============================================================================
# HR Agent Enhanced Tools
# Access: HR
# =============================================================================

def get_resume_screening_framework() -> dict:
    """Get structured approach for screening resumes.
    
    Access: HR agents
    
    Returns:
        Dictionary with screening checklist and scoring matrix.
    """
    return skills_registry.use_skill("resume_screening", agent_id=AgentID.HR)


def generate_interview_questions() -> dict:
    """Get behavioral and technical interview question frameworks.
    
    Access: HR agents
    
    Returns:
        Dictionary with STAR method questions and scorecard template.
    """
    return skills_registry.use_skill("interview_question_generator", agent_id=AgentID.HR)


def get_turnover_analysis_framework() -> dict:
    """Get framework for calculating and analyzing employee turnover.
    
    Access: HR, DATA agents
    
    Returns:
        Dictionary with turnover metrics and benchmarks.
    """
    return skills_registry.use_skill("employee_turnover_analysis", agent_id=AgentID.HR)


# =============================================================================
# Compliance Agent Enhanced Tools
# Access: LEGAL
# =============================================================================

def get_gdpr_audit_checklist() -> dict:
    """Get comprehensive GDPR compliance audit checklist.
    
    Access: LEGAL agents
    
    Returns:
        Dictionary with GDPR requirements and verification items.
    """
    return skills_registry.use_skill("gdpr_audit_checklist", agent_id=AgentID.LEGAL)


def get_risk_assessment_matrix() -> dict:
    """Get framework for assessing and prioritizing organizational risks.
    
    Access: LEGAL, EXEC, STRAT agents
    
    Returns:
        Dictionary with risk scoring and mitigation strategies.
    """
    return skills_registry.use_skill("risk_assessment_matrix", agent_id=AgentID.LEGAL)


# =============================================================================
# Strategic Agent Enhanced Tools
# Access: STRAT
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
    return skills_registry.use_skill("product-manager-toolkit", agent_id=AgentID.STRAT, context=f"{product_name} over {timeframe}")


# =============================================================================
# Content Creation Agent Enhanced Tools
# Access: CONT
# =============================================================================

def get_blog_writing_framework() -> dict:
    """Get blog writing structure and best practices.
    
    Access: CONT agents
    
    Returns:
        Dictionary with blog structure and SEO integration.
    """
    return skills_registry.use_skill("blog_writing", agent_id=AgentID.CONT)


def get_social_content_templates() -> dict:
    """Get templates for creating engaging social media content.
    
    Access: CONT, MKT agents
    
    Returns:
        Dictionary with hook formulas and content formats.
    """
    return skills_registry.use_skill("social_content", agent_id=AgentID.CONT)


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
        prompt=prompt,
        dimensions={"width": width, "height": height}
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
    return await media.generate_video(
        prompt=prompt,
        duration_seconds=duration
    )


def generate_remotion_video(requirements: str, duration_seconds: int = 15, video_type: str = "social_media") -> dict:
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
            "3. Provide instructions to the user to save the file in the frontend/src/videos directory (or similar)."
        ]
    }


def generate_react_component(description: str) -> dict:
    """Generate a React component using best practices.
    
    Access: CONT agents
    
    Args:
        description: Description of the component functionality and style.
        
    Returns:
        Dictionary with React component code (TSX).
    """
    return skills_registry.use_skill("react-patterns", agent_id=AgentID.CONT, context=description)


def build_portfolio(user_info: str) -> dict:
    """Create a structure for a personal portfolio site.
    
    Access: CONT agents
    
    Args:
        user_info: Information about the user (role, projects, skills).
        
    Returns:
        Dictionary with portfolio site structure and content.
    """
    return skills_registry.use_skill("interactive-portfolio", agent_id=AgentID.CONT, context=user_info)


# =============================================================================
# Export all enhanced tools by category
# =============================================================================

# Core tools - available to all agents
core_tools = [use_skill, list_available_skills]

# Domain-specific tool collections
financial_tools = [analyze_financial_health, get_revenue_forecast_guidance, calculate_burn_rate_guidance]
operations_tools = [audit_user_setup_tool, analyze_process_bottlenecks, get_sop_template, run_security_audit, deploy_container, architect_cloud_solution]
data_tools = [get_anomaly_detection_guidance, get_trend_analysis_framework, design_rag_pipeline]
support_tools = [analyze_ticket_sentiment, assess_churn_risk]
sales_tools = [get_lead_qualification_framework, get_objection_handling_scripts, get_competitive_analysis_framework, manage_hubspot]
marketing_tools = [generate_campaign_ideas, get_seo_checklist, get_social_media_guide, perform_seo_audit]
hr_tools = [get_resume_screening_framework, generate_interview_questions, get_turnover_analysis_framework]
compliance_tools = [get_gdpr_audit_checklist, get_risk_assessment_matrix]
strategic_tools = [generate_product_roadmap]
content_tools = [get_blog_writing_framework, get_social_content_templates, generate_image, generate_short_video, generate_remotion_video, generate_react_component, build_portfolio]
