"""Configuration Agent Tools.

Provides agent capabilities to help users configure MCP tools and integrations.
Designed to guide non-technical users through the setup process.
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime

from app.services.supabase import get_service_client
from app.mcp.config import get_mcp_config

logger = logging.getLogger(__name__)


# ============================================================================
# Built-in Tools (System-level, not user-configurable)
# ============================================================================

BUILT_IN_TOOLS = {
    "tavily": {
        "name": "Web Search (Tavily)",
        "description": "AI-powered web search that automatically finds real-time information from the internet.",
        "use_cases": [
            "Research competitors and market trends",
            "Find current news and updates",
            "Gather information for content creation",
            "Answer questions requiring up-to-date information"
        ],
        "is_built_in": True,
    },
    "firecrawl": {
        "name": "Web Scraping (Firecrawl)",
        "description": "Automatically extracts content from any webpage and converts it to clean, readable text.",
        "use_cases": [
            "Extract content from competitor websites",
            "Gather data for market research",
            "Convert web articles to readable format",
            "Analyze website content and structure"
        ],
        "is_built_in": True,
    },
}


def _is_built_in_tool_configured(tool_id: str, config) -> bool:
    if tool_id == "tavily":
        return config.is_tavily_configured()
    if tool_id == "firecrawl":
        return config.is_firecrawl_configured()
    return False


def _get_built_in_tool_status(tool_id: str, config) -> str:
    configured = _is_built_in_tool_configured(tool_id, config)
    action = "used automatically" if configured else "available in code but not configured"
    provider = "research" if tool_id == "tavily" else "deep research"

    if configured:
        return f"Configured server-side and {action} for {provider}"
    return f"Built-in provider wrapper is {action}; add the API key to enable {provider}"

# ============================================================================
# User-Configurable MCP Tools
# ============================================================================

# ============================================================================
# User-Configurable MCP Tools
# ============================================================================

MCP_TOOL_GUIDES = {
    "stitch": {
        "name": "Stitch Landing Page Builder",
        "description": "AI-powered landing page generator that creates beautiful, responsive pages from descriptions.",
        "use_cases": [
            "Create product launch pages",
            "Build marketing campaign landing pages",
            "Generate lead capture pages",
            "Design event registration pages"
        ],
        "setup_steps": [
            "Visit https://stitch.withgoogle.com and sign in with Google",
            "Go to Settings > API Access",
            "Generate a new API key",
            "Copy the API key",
            "Share it with me and I'll set it up"
        ],
        "free_tier": "10 pages per month free",
        "env_var": "STITCH_API_KEY",
        "docs_url": "https://stitch.withgoogle.com/docs",
        "signup_url": "https://stitch.withgoogle.com"
    },
    "resend": {
        "name": "Resend Email Service",
        "description": "Modern email API for developers — reliable delivery, easy setup, and great deliverability.",
        "use_cases": [
            "Send email notifications to leads",
            "Deliver marketing campaigns",
            "Send transactional emails",
            "Automated follow-up sequences"
        ],
        "setup_steps": [
            "Go to https://resend.com and create a free account",
            "Verify your domain in Settings > Domains",
            "Navigate to API Keys in the sidebar",
            "Click 'Create API Key'",
            "Copy the key (starts with 're_')",
            "Paste it here for me to configure"
        ],
        "free_tier": "3,000 emails per month free, 100 per day",
        "env_var": "RESEND_API_KEY",
        "docs_url": "https://resend.com/docs",
        "signup_url": "https://resend.com"
    },
    "hubspot": {
        "name": "HubSpot CRM",
        "description": "Customer relationship management to track leads, deals, and customer interactions.",
        "use_cases": [
            "Store and manage customer contacts",
            "Track sales pipeline and deals",
            "Log customer interactions",
            "Sync leads from landing pages"
        ],
        "setup_steps": [
            "Sign up at https://www.hubspot.com (free CRM available)",
            "Go to Settings (gear icon) > Integrations > Private Apps",
            "Click 'Create a private app'",
            "Name it 'Pikar AI' and select CRM scopes",
            "Copy the access token after creation",
            "Share it with me to complete setup"
        ],
        "free_tier": "Free CRM with unlimited contacts",
        "env_var": "HUBSPOT_API_KEY",
        "docs_url": "https://developers.hubspot.com",
        "signup_url": "https://www.hubspot.com"
    },
    "stripe": {
        "name": "Stripe Payments",
        "description": "Accept payments on your landing pages. Create payment links, subscriptions, and checkout experiences.",
        "use_cases": [
            "Add payment buttons to landing pages",
            "Create subscription products",
            "Accept one-time payments",
            "Set up checkout flows for products/services"
        ],
        "setup_steps": [
            "Create a Stripe account at https://stripe.com",
            "Go to Developers > API Keys in the dashboard",
            "Copy your Secret Key (starts with 'sk_')",
            "For testing, use your test mode key (sk_test_...)",
            "Paste the key here and I'll set it up"
        ],
        "free_tier": "No monthly fees, 2.9% + 30¢ per transaction",
        "env_var": "STRIPE_API_KEY",
        "docs_url": "https://stripe.com/docs",
        "signup_url": "https://stripe.com"
    },
    "canva": {
        "name": "Canva Media Creation",
        "description": "Create professional images, social media posts, and graphics using AI-powered design tools.",
        "use_cases": [
            "Generate social media graphics",
            "Create marketing images and banners",
            "Design presentation slides",
            "Build brand assets automatically"
        ],
        "setup_steps": [
            "Go to https://www.canva.com/developers and sign in",
            "Create a new integration/app",
            "Go to the Credentials section",
            "Generate an API key",
            "Copy the key and share it with me"
        ],
        "free_tier": "Free tier with limited exports",
        "env_var": "CANVA_API_KEY",
        "docs_url": "https://www.canva.dev/docs",
        "signup_url": "https://www.canva.com/developers"
    }
}


# ============================================================================
# Agent Tool Functions
# ============================================================================

def get_available_tools() -> Dict[str, Any]:
    """Get list of all available MCP tools and their configuration status.

    Use this to show users what tools are available and which ones
    are already configured. Separates built-in tools from user-configurable tools.

    Returns:
        Dictionary with built-in tools, configurable tools, and summary.
    """
    config = get_mcp_config()

    built_in = []
    for tool_id, info in BUILT_IN_TOOLS.items():
        built_in.append({
            "id": tool_id,
            "name": info["name"],
            "description": info["description"],
            "is_built_in": True,
            "configured": _is_built_in_tool_configured(tool_id, config),
            "status": _get_built_in_tool_status(tool_id, config),
            "use_cases": info["use_cases"][:2],
        })

    tools = []
    for tool_id, guide in MCP_TOOL_GUIDES.items():
        env_value = os.environ.get(guide["env_var"])
        is_configured = bool(env_value and len(env_value) > 5)

        tools.append({
            "id": tool_id,
            "name": guide["name"],
            "description": guide["description"],
            "configured": is_configured,
            "free_tier": guide["free_tier"],
            "use_cases": guide["use_cases"][:2],
            "is_built_in": False,
        })

    configured_count = sum(1 for t in tools if t["configured"])
    built_in_ready = sum(1 for t in built_in if t["configured"])

    return {
        "success": True,
        "built_in_tools": built_in,
        "configurable_tools": tools,
        "summary": f"{configured_count} of {len(tools)} optional tools configured. {built_in_ready} of {len(built_in)} built-in research providers are ready.",
        "message": "Web search and scraping are built into the platform, but they only run when their server-side API keys are configured. You can optionally configure additional tools for payments, CRM, email, and more."
    }

def get_tool_setup_guide(tool_id: str) -> Dict[str, Any]:
    """Get detailed setup guide for a specific MCP tool.
    
    Use this when a user wants to configure a specific tool.
    Provides step-by-step instructions they can follow.
    
    Args:
        tool_id: The tool identifier (tavily, firecrawl, stitch, resend, hubspot)
    
    Returns:
        Detailed setup guide with steps and links.
    """
    tool_id = tool_id.lower().strip()
    
    if tool_id not in MCP_TOOL_GUIDES:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_id}",
            "available_tools": list(MCP_TOOL_GUIDES.keys())
        }
    
    guide = MCP_TOOL_GUIDES[tool_id]
    
    # Check current status
    env_value = os.environ.get(guide["env_var"])
    is_configured = bool(env_value and len(env_value) > 5)
    
    return {
        "success": True,
        "tool_id": tool_id,
        "name": guide["name"],
        "description": guide["description"],
        "configured": is_configured,
        "use_cases": guide["use_cases"],
        "setup_steps": guide["setup_steps"],
        "free_tier": guide["free_tier"],
        "signup_url": guide["signup_url"],
        "docs_url": guide["docs_url"],
        "env_var": guide["env_var"],
        "message": f"Here's how to set up {guide['name']}. Follow these steps and share your API key with me when ready."
    }


def explain_tool_benefits(tool_id: str) -> Dict[str, Any]:
    """Explain the benefits and use cases of a specific tool.
    
    Use this when a user is unsure whether they need a tool.
    Helps them understand the value before committing to setup.
    
    Args:
        tool_id: The tool identifier
    
    Returns:
        Benefits explanation in user-friendly language.
    """
    tool_id = tool_id.lower().strip()
    
    if tool_id not in MCP_TOOL_GUIDES:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_id}"
        }
    
    guide = MCP_TOOL_GUIDES[tool_id]
    
    # Generate user-friendly explanation
    benefits_text = f"""
**{guide['name']}** - {guide['description']}

**What you can do with it:**
"""
    for use_case in guide["use_cases"]:
        benefits_text += f"• {use_case}\n"
    
    benefits_text += f"""
**Cost:** {guide['free_tier']}

**Is it right for you?**
"""
    
    # Tool-specific recommendations
    recommendations = {
        "tavily": "If you want your AI assistant to find current information from the web, this is essential. Great for research and staying up-to-date.",
        "firecrawl": "Perfect if you need to analyze competitor websites or extract content from the web. Very useful for content research.",
        "stitch": "Ideal if you frequently need landing pages for campaigns, products, or events. Saves hours of design work.",
        "resend": "Essential if you want to send emails to leads or customers. Required for email marketing and notifications.",
        "hubspot": "Great for tracking leads and customers. Recommended if you're doing sales or want organized customer data."
    }
    
    benefits_text += recommendations.get(tool_id, "This tool can enhance your AI assistant's capabilities.")
    
    return {
        "success": True,
        "tool_id": tool_id,
        "name": guide["name"],
        "benefits": benefits_text,
        "free_tier": guide["free_tier"],
        "signup_url": guide["signup_url"]
    }


async def save_user_api_key(
    user_id: str,
    tool_id: str,
    api_key: str
) -> Dict[str, Any]:
    """Save a user's API key for an MCP tool.
    
    Use this after a user shares their API key. Validates the key
    format and saves it securely to their configuration.
    
    Args:
        user_id: The user's ID
        tool_id: The tool identifier
        api_key: The API key to save
    
    Returns:
        Success status and next steps.
    """
    tool_id = tool_id.lower().strip()
    
    if tool_id not in MCP_TOOL_GUIDES:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_id}"
        }
    
    guide = MCP_TOOL_GUIDES[tool_id]
    
    # Basic validation
    api_key = api_key.strip()
    if len(api_key) < 10:
        return {
            "success": False,
            "error": "That API key seems too short. Please check and try again."
        }
    
    # Tool-specific validation
    validation_errors = []
    if tool_id == "tavily" and not api_key.startswith("tvly-"):
        validation_errors.append("Tavily API keys usually start with 'tvly-'. Please verify you copied the correct key.")
    
    if validation_errors:
        return {
            "success": False,
            "error": validation_errors[0],
            "hint": "Make sure you're copying the API key, not the account ID or other credentials."
        }
    
    try:
        client = get_service_client()
        
        # Save to user_configurations
        client.table("user_configurations").upsert({
            "user_id": user_id,
            "config_key": guide["env_var"],
            "config_value": api_key,
            "is_sensitive": True,
            "updated_at": datetime.utcnow().isoformat()
        }, on_conflict="user_id,config_key").execute()
        
        logger.info(f"Saved {tool_id} API key for user {user_id}")
        
        return {
            "success": True,
            "tool_id": tool_id,
            "name": guide["name"],
            "message": f"Great! I've saved your {guide['name']} API key. The tool is now configured and ready to use.",
            "next_steps": [
                f"You can now use {guide['name']} features",
                "Try asking me to use this tool for a task",
                "You can update or remove this key anytime in Configuration settings"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to save API key: {e}")
        return {
            "success": False,
            "error": "I couldn't save the API key. Please try again or contact support."
        }


def get_configuration_help() -> Dict[str, Any]:
    """Get general help about configuration and available tools.
    
    Use this when a user asks about configuration, settings,
    or wants to know what they can customize.
    
    Returns:
        Overview of configuration options and how to proceed.
    """
    get_mcp_config()
    
    # Check what's configured
    configured_tools = []
    unconfigured_tools = []
    
    for tool_id, guide in MCP_TOOL_GUIDES.items():
        env_value = os.environ.get(guide["env_var"])
        if env_value and len(env_value) > 5:
            configured_tools.append(guide["name"])
        else:
            unconfigured_tools.append({
                "id": tool_id,
                "name": guide["name"],
                "benefit": guide["use_cases"][0]
            })
    
    help_text = """
I can help you configure tools that enhance what I can do for you. Here's what's available:

**🔧 MCP Tools** - These give me extra capabilities:
"""
    
    for tool_id, guide in MCP_TOOL_GUIDES.items():
        env_value = os.environ.get(guide["env_var"])
        status = "✅ Configured" if (env_value and len(env_value) > 5) else "⚪ Not set up"
        help_text += f"• **{guide['name']}**: {status}\n"
    
    help_text += """
**📱 Social Media Accounts** - Connect for publishing:
• Twitter/X, LinkedIn, Facebook, Instagram, YouTube

**How to get started:**
Just tell me which tool you'd like to set up, and I'll guide you through it step by step. For example, say "Help me set up web search" or "I want to configure email."
"""
    
    return {
        "success": True,
        "help_text": help_text,
        "configured_count": len(configured_tools),
        "total_tools": len(MCP_TOOL_GUIDES),
        "suggestions": [
            f"Set up {t['name']} to {t['benefit'].lower()}" 
            for t in unconfigured_tools[:3]
        ]
    }


def recommend_tools_for_goal(goal: str) -> Dict[str, Any]:
    """Recommend which tools to configure based on user's goal.
    
    Use this when a user describes what they want to achieve,
    to suggest relevant tools.
    
    Args:
        goal: Description of what the user wants to accomplish
    
    Returns:
        Tool recommendations based on the goal.
    """
    goal_lower = goal.lower()
    
    recommendations = []
    
    # Research/Information goals
    if any(word in goal_lower for word in ["research", "find", "search", "information", "news", "competitor", "market"]):
        recommendations.append({
            "tool_id": "tavily",
            "name": "Tavily Web Search",
            "reason": "Essential for finding current information and doing research online"
        })
    
    # Content/Website goals
    if any(word in goal_lower for word in ["website", "scrape", "content", "extract", "article", "competitor"]):
        recommendations.append({
            "tool_id": "firecrawl",
            "name": "Firecrawl Web Scraping",
            "reason": "Perfect for extracting and analyzing content from websites"
        })
    
    # Landing page/Marketing goals
    if any(word in goal_lower for word in ["landing", "page", "campaign", "launch", "marketing", "lead"]):
        recommendations.append({
            "tool_id": "stitch",
            "name": "Stitch Landing Pages",
            "reason": "Creates beautiful landing pages quickly for your campaigns"
        })
    
    # Email goals
    if any(word in goal_lower for word in ["email", "send", "notify", "newsletter", "outreach"]):
        recommendations.append({
            "tool_id": "resend",
            "name": "Resend Email",
            "reason": "Enables sending professional emails and notifications"
        })
    
    # CRM/Sales goals
    if any(word in goal_lower for word in ["crm", "customer", "lead", "sales", "track", "contact", "deal"]):
        recommendations.append({
            "tool_id": "hubspot",
            "name": "HubSpot CRM",
            "reason": "Helps track and manage your customers and leads"
        })
    
    if not recommendations:
        # Default recommendations for general use
        recommendations = [
            {
                "tool_id": "tavily",
                "name": "Tavily Web Search",
                "reason": "Most versatile - helps with research and finding information"
            }
        ]
    
    return {
        "success": True,
        "goal": goal,
        "recommendations": recommendations,
        "message": f"Based on your goal, I recommend setting up {len(recommendations)} tool(s). Would you like me to help you configure any of these?"
    }


# ============================================================================
# Export for Agent Registration
# ============================================================================

CONFIGURATION_TOOLS = [
    get_available_tools,
    get_tool_setup_guide,
    explain_tool_benefits,
    save_user_api_key,
    get_configuration_help,
    recommend_tools_for_goal,
]

CONFIGURATION_TOOLS_MAP = {
    "get_available_tools": get_available_tools,
    "get_tool_setup_guide": get_tool_setup_guide,
    "explain_tool_benefits": explain_tool_benefits,
    "save_user_api_key": save_user_api_key,
    "get_configuration_help": get_configuration_help,
    "recommend_tools_for_goal": recommend_tools_for_goal,
}

