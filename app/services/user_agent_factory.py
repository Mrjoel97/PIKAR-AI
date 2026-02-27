"""UserAgentFactory - Factory for creating per-user ExecutiveAgent instances.

This service creates personalized ExecutiveAgent instances by loading user
configuration from the user_executive_agents table and injecting business
context into the agent's system prompt.
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from supabase import Client

from app.services.supabase import get_service_client
from app.services.cache import get_cache_service
import asyncio

# from google.adk.agents import Agent
# from google.adk.models import Gemini
# from google.genai import types

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from google.adk.agents import Agent

# NOTE: SPECIALIZED_AGENTS is imported lazily in create_executive_agent()
# to avoid circular dependency with agents that import workflow modules.

logger = logging.getLogger(__name__)

# Default Executive Agent instruction (can be overridden per-user)
DEFAULT_EXECUTIVE_INSTRUCTION = """You are the Executive Agent for Pikar AI - the Chief of Staff and Central Orchestrator.

## YOUR ROLE
You are the primary interface between the user and Pikar AI's multi-agent ecosystem. You oversee all business operations and coordinate specialized agents to accomplish complex tasks.

## YOUR RESPONSIBILITIES
1. **Understand User Intent** - Analyze requests to determine the best approach
2. **Delegate Intelligently** - Route tasks to the most appropriate specialized agents
3. **Synthesize Results** - Combine outputs from multiple agents into coherent responses
4. **Provide Strategic Guidance** - Offer high-level recommendations based on business context

## VISUAL DASHBOARDS & WIDGETS
YOU CAN AND SHOULD render interactive widgets in the user's workspace. When users ask to SEE, VIEW, DISPLAY, or VISUALIZE data, use these widget tools to render rich UI:
- `create_initiative_dashboard_widget`: Display strategic initiatives with progress, status, and metrics
- `create_revenue_chart_widget`: Visualize financial data, revenue trends, and growth metrics
- `create_kanban_board_widget`: Show task boards, project pipelines, and status tracking
- `create_table_widget`: Display data in table format (leads, employees, transactions, lists)
- `create_form_widget`: Collect structured input from users (feedback, requests, surveys)
- `create_calendar_widget`: Show schedules, events, and timeline views
- `create_workflow_builder_widget`: Display process flows and diagrams
- `create_product_launch_widget`: Track product launch milestones
- `display_workflow`: Show a running workflow's status and progress

**IMPORTANT**: When a user asks to "show", "display", "visualize", or "see" something, ALWAYS use the appropriate widget tool. The widget will render in their workspace. Do NOT say you cannot display things - you CAN by using these tools.

## CRITICAL: UI CAPABILITIES — READ CAREFULLY
You and ALL your specialist agents CAN render interactive widgets in the user's workspace.

**NEVER say any of the following:**
- "I don't have the ability to interact with your UI"
- "I cannot directly open or display elements in your workspace"
- "Unfortunately, as an AI, I can't interact with your interface"
- "I'm unable to render visual elements"

**These statements are FALSE.** You have widget tools that render directly in the user's workspace.
When a user asks to "show", "view", "display", or "see" ANYTHING, use the appropriate widget tool immediately.
Both you AND your specialist sub-agents have full access to widget rendering tools.

## SPECIALIZED AGENTS AVAILABLE
All specialists can render widgets in the workspace:
- FinancialAnalysisAgent: Revenue analysis, cost optimization, financial forecasting
- StrategicPlanningAgent: OKR management, initiative planning, roadmap development
- ContentCreationAgent: Blog posts, newsletters, social media content
- MarketingAutomationAgent: Email campaigns, landing pages, marketing strategy
- SalesIntelligenceAgent: Lead qualification, pipeline analysis, sales tactics
- OperationsOptimizationAgent: Process improvement, efficiency analysis
- HRRecruitmentAgent: Hiring guidance, interview prep, team development
- ComplianceRiskAgent: GDPR compliance, risk assessment, legal guidance
- CustomerSupportAgent: Ticket analysis, sentiment tracking, churn prevention
- DataAnalysisAgent: Data validation, anomaly detection, forecasting

Simply describe the task and the system will route to the appropriate specialist.

## AUTO-INITIATIVE DETECTION
When a user shares a business idea, product concept, or service idea:
1. Acknowledge the idea enthusiastically
2. Delegate to the StrategicPlanningAgent which will auto-create an initiative using `start_initiative_from_idea`
3. The Strategic Agent will render the initiative dashboard widget
4. Guide the user through the 5-phase Initiative Framework:
   - Phase 1: Ideation and Empathy
   - Phase 2: Validation and Research
   - Phase 3: Prototype and Test
   - Phase 4: Build Product/Service
   - Phase 5: Scale Business
5. At each approval gate, ask the user before proceeding to the next phase

Trigger phrases: "I have an idea for...", "What if we...", "I want to build...", "Let's create...", "I'm thinking about starting..."

## SKILLS REGISTRY
Access domain expertise and create custom skills adapted to the user's context:
- `list_skills`: Discover available skills by category (finance, marketing, sales, hr, content, etc.)
- `use_skill`: Access domain knowledge, frameworks, and best practices from a skill
- `search_skills`: Find skills matching a topic or keyword
- `create_custom_skill`: Create NEW skills tailored to the user's specific business needs
- `list_user_skills`: See custom skills created for this user

**IMPORTANT**: Skills are like having domain experts on demand. When a user asks about specialized topics:
1. First, search or list skills to see if relevant expertise exists
2. Use the skill to get frameworks, checklists, and best practices
3. If no suitable skill exists AND the user has recurring needs, offer to CREATE a custom skill

Examples:
- User asks about SEO -> `search_skills("SEO")` then `use_skill("seo_checklist")`
- User needs financial analysis -> `use_skill("analyze_financial_statement")`
- User has unique business process -> `create_custom_skill` with their specific knowledge
"""


class UserAgentFactory:
    """Factory for creating personalized ExecutiveAgent instances.
    
    Each user can have customized:
    - Agent name
    - Business context injected into system prompt
    - Custom system prompt override
    - Preferences (tone, verbosity, etc.)
    """
    
    def __init__(self):
        self.client: Client = get_service_client()
        self._table_name = "user_executive_agents"
        self._cache: Dict[str, "Agent"] = {}  # Simple cache for agent instances
        self._redis_cache = get_cache_service()

    async def get_user_config(self, user_id: str) -> Optional[dict]:
        """Load user's executive agent configuration from database.
        
        Args:
            user_id: The user's UUID.
            
        Returns:
            User configuration record or None if not found.
        """
        # Try Redis cache first
        try:
            cached_config = await self._redis_cache.get_user_config(str(user_id))
            if cached_config:
                logger.debug(f"Cache hit for user config {user_id}")
                return cached_config
        except Exception as e:
            logger.warning(f"Cache read failed for {user_id}: {e}")

        try:
            response = (
                self.client.table(self._table_name)
                .select("*")
                .eq("user_id", str(user_id))
                .single()
                .execute()
            )
            
            if response.data:
                # Cache the result
                await self._redis_cache.set_user_config(str(user_id), response.data)
                
            return response.data
        except Exception as e:
            logger.debug(f"No config found for user {user_id}: {e}")
            return None

    def _inject_business_context(
        self,
        base_instruction: str,
        business_context: Dict[str, Any]
    ) -> str:
        """Inject business context into the system prompt.
        
        Args:
            base_instruction: The base system prompt.
            business_context: User's business context (company, industry, etc.)
            
        Returns:
            Enhanced system prompt with business context.
        """
        if not business_context:
            return base_instruction
        
        context_section = "\n## YOUR USER'S BUSINESS CONTEXT\n"
        
        if business_context.get("company_name"):
            context_section += f"- **Company**: {business_context['company_name']}\n"
        if business_context.get("industry"):
            context_section += f"- **Industry**: {business_context['industry']}\n"
        if business_context.get("team_size"):
            context_section += f"- **Team Size**: {business_context['team_size']}\n"
        if business_context.get("business_model"):
            context_section += f"- **Business Model**: {business_context['business_model']}\n"
        if business_context.get("goals"):
            goals = business_context['goals']
            if isinstance(goals, list):
                goals_str = ", ".join(goals)
            else:
                goals_str = str(goals)
            context_section += f"- **Goals**: {goals_str}\n"
        if business_context.get("challenges"):
            challenges = business_context['challenges']
            if isinstance(challenges, list):
                challenges_str = ", ".join(challenges)
            else:
                challenges_str = str(challenges)
            context_section += f"- **Challenges**: {challenges_str}\n"
        
        context_section += "\nUse this context to provide more relevant and personalized recommendations.\n"
        
        # Insert after the role section
        if "## YOUR RESPONSIBILITIES" in base_instruction:
            return base_instruction.replace(
                "## YOUR RESPONSIBILITIES",
                context_section + "\n## YOUR RESPONSIBILITIES"
            )
        else:
            return base_instruction + context_section

    def _inject_persona_context(self, base_instruction: str, persona: str) -> str:
        """Inject persona-specific behavioral instructions.
        
        Args:
            base_instruction: The base system prompt.
            persona: The user's persona (solopreneur, startup, sme, enterprise).
            
        Returns:
            Enhanced system prompt.
        """
        persona = persona.lower()
        
        persona_guides = {
            "solopreneur": (
                "## YOUR USER PERSONA: SOLOPRENEUR\n"
                "- **Focus**: Efficiency, Action, Low-Overhead.\n"
                "- **Traits**: Time-poor, wears many hats, needs immediate results.\n"
                "- **Guidance**: Propose simple, low-cost solutions. Avoid bureaucracy. "
                "Prioritize 'done' over 'perfect'. automate routine tasks immediately."
            ),
            "startup": (
                "## YOUR USER PERSONA: STARTUP TEAM\n"
                "- **Focus**: Growth, Speed, Iteration.\n"
                "- **Traits**: Collaborative, metrics-driven, chaotic but ambitious.\n"
                "- **Guidance**: Focus on MRR/Growth metrics. Suggest scalable processes but don't over-engineer yet. "
                "Help align the team."
            ),
            "sme": (
                "## YOUR USER PERSONA: SME MANAGER\n"
                "- **Focus**: Optimization, Stability, Compliance.\n"
                "- **Traits**: Process-oriented, managing risk, steady growth.\n"
                "- **Guidance**: Prioritize reliability and compliance. Ensure policies are followed. "
                "Look for cost optimization and efficiency gains."
            ),
            "enterprise": (
                "## YOUR USER PERSONA: ENTERPRISE EXECUTIVE\n"
                "- **Focus**: Strategy, Security, Integration.\n"
                "- **Traits**: Strategic, navigating complexity, risk-averse.\n"
                "- **Guidance**: Speak in terms of ROI and Strategy. Ensure strict data governance. "
                "Consider cross-departmental impact."
            )
        }
        
        guide = persona_guides.get(persona)
        if not guide:
            return base_instruction
            
        # Insert at the very top or after Role
        return base_instruction.replace(
            "## YOUR ROLE",
            f"{guide}\n\n## YOUR ROLE"
        ) if "## YOUR ROLE" in base_instruction else f"{guide}\n\n{base_instruction}"

    def _apply_preferences(
        self,
        instruction: str,
        preferences: Dict[str, Any]
    ) -> str:
        """Apply user preferences to the system prompt.
        
        Args:
            instruction: The system prompt to modify.
            preferences: User preferences (tone, verbosity, etc.)
            
        Returns:
            Modified system prompt.
        """
        if not preferences:
            return instruction
        
        pref_section = "\n## COMMUNICATION PREFERENCES\n"
        
        if preferences.get("tone"):
            pref_section += f"- Use a {preferences['tone']} tone in your responses.\n"
        if preferences.get("verbosity"):
            pref_section += f"- Keep responses {preferences['verbosity']}.\n"
        if preferences.get("format_preference"):
            pref_section += f"- Format preference: {preferences['format_preference']}\n"

        return instruction + pref_section

    async def create_executive_agent(
        self,
        user_id: str | UUID,
        use_cache: bool = True
    ) -> "Agent":
        """Create a personalized ExecutiveAgent for the user.

        Args:
            user_id: The user's UUID.
            use_cache: Whether to use cached agent instances.

        Returns:
            Personalized Agent instance.
        """
        # Check cache first
        user_id_str = str(user_id)
        if use_cache and user_id_str in self._cache:
            logger.debug(f"Returning cached agent for user {user_id}")
            return self._cache[user_id_str]

        # Load user configuration
        config = await self.get_user_config(user_id)

        # Build the instruction
        if config and config.get("system_prompt_override"):
            # User has a complete custom system prompt
            instruction = config["system_prompt_override"]
        else:
            # Start with default and customize
            instruction = DEFAULT_EXECUTIVE_INSTRUCTION

            if config:
                # Inject business context
                business_context = config.get("business_context", {})
                if business_context:
                    instruction = self._inject_business_context(
                        instruction, business_context
                    )

                # Inject Persona Context
                persona = config.get("persona")
                
                # If not in config, try cache/db lookup (fallback)
                if not persona:
                    cached_persona = await self._redis_cache.get_user_persona(str(user_id))
                    if cached_persona:
                        persona = cached_persona
                
                if persona:
                    logger.info(f"Loading persona '{persona}' for user {user_id}")
                    instruction = self._inject_persona_context(instruction, persona)
                    logger.debug(f"Injected persona context for {persona}")

                # Apply preferences
                preferences = config.get("preferences", {})
                if preferences:
                    instruction = self._apply_preferences(instruction, preferences)

        # Determine agent name
        agent_name = "ExecutiveAgent"
        if config and config.get("agent_name"):
            agent_name = config["agent_name"]

        # Import tools from main agent module
        from app.agent import (
            get_revenue_stats,
            search_business_knowledge,
            update_initiative_status,
            create_task,
        )
        # Lazy import to avoid circular dependency
        from app.agents.specialized_agents import SPECIALIZED_AGENTS
        
        # Import all tool sets to ensure feature parity with main agent
        from app.orchestration.knowledge_tools import KNOWLEDGE_INJECTION_TOOLS
        from app.agents.tools.notifications import NOTIFICATION_TOOLS
        from app.agents.tools.workflows import WORKFLOW_TOOLS
        from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
        from app.agents.tools.skills import SKILL_TOOLS

        # Create the personalized agent
        from google.adk.agents import Agent
        from app.agents.shared import get_model

        agent = Agent(
            name=agent_name,
            model=get_model(),
            description="Chief of Staff / Central Orchestrator - Personalized for user",
            instruction=instruction,
            tools=[
                # Business tools
                get_revenue_stats,
                search_business_knowledge,
                update_initiative_status,
                create_task,
                # Knowledge injection tools
                *KNOWLEDGE_INJECTION_TOOLS,
                # Notification tools
                *NOTIFICATION_TOOLS,
                # Workflow tools
                *WORKFLOW_TOOLS,
                # UI Widget tools for agent-to-UI
                *UI_WIDGET_TOOLS,
                # Skill tools for accessing and creating domain expertise
                *SKILL_TOOLS,
            ],
            sub_agents=SPECIALIZED_AGENTS,
        )

        # Cache the agent
        if use_cache:
            self._cache[user_id_str] = agent

        logger.info(f"Created personalized agent '{agent_name}' for user {user_id}")
        return agent

    def invalidate_cache(self, user_id: str) -> None:
        """Remove cached agent for a user (call after config changes).

        Args:
            user_id: The user's UUID.
        """
        user_id_str = str(user_id)
        if user_id_str in self._cache:
            del self._cache[user_id_str]
            logger.debug(f"Invalidated cached agent for user {user_id}")
        
        # Invalidate Redis cache
        asyncio.create_task(self._redis_cache.invalidate_user_all(user_id_str))

    def clear_cache(self) -> None:
        """Clear all cached agent instances."""
        self._cache.clear()
        logger.debug("Cleared all cached agents")

    async def update_user_config(
        self,
        user_id: str | UUID,
        agent_name: Optional[str] = None,
        business_context: Optional[Dict[str, Any]] = None,
        system_prompt_override: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Update user's executive agent configuration.

        Creates a new record if none exists.

        Args:
            user_id: The user's UUID.
            agent_name: Custom name for the agent.
            business_context: Business context dict.
            system_prompt_override: Complete custom system prompt.
            preferences: User preferences dict.

        Returns:
            Updated configuration record.
        """
        data = {"user_id": str(user_id)}

        if agent_name is not None:
            data["agent_name"] = agent_name
        if business_context is not None:
            data["business_context"] = business_context
        if system_prompt_override is not None:
            data["system_prompt_override"] = system_prompt_override
        if preferences is not None:
            data["preferences"] = preferences

        response = (
            self.client.table(self._table_name)
            .upsert(data, on_conflict="user_id")
            .execute()
        )

        # Invalidate cache after config change
        self.invalidate_cache(user_id)
        await self._redis_cache.invalidate_user_config(str(user_id))

        if response.data:
            return response.data[0]
        raise Exception("No data returned from update config")

    async def create_user_workflow(
        self,
        user_id: str | UUID,
        workflow_name: str,
    ) -> Optional[Any]:
        """Create a user-specific workflow instance.

        Uses the workflow registry to look up factory functions and creates
        a fresh workflow instance. This ensures workflows don't share agent
        instances that might have parent conflicts.

        Args:
            user_id: The user's UUID (for future user-specific customization).
            workflow_name: The catalog name of the workflow in the registry.

        Returns:
            A fresh workflow instance or None if not found.
        """
        from app.workflows.registry import get_workflow_factory

        # Get the factory function from registry
        factory = get_workflow_factory(workflow_name)
        if factory is None:
            logger.warning(f"Workflow '{workflow_name}' not found in registry")
            return None

        # Create fresh workflow instance using the factory
        try:
            workflow = factory()
            logger.debug(f"Created workflow '{workflow_name}' for user {user_id}")
            return workflow
        except Exception as e:
            logger.error(f"Failed to create workflow '{workflow_name}': {e}")
            return None

    def list_available_workflows(self) -> list[str]:
        """List all available workflow names from the registry.

        Returns:
            List of workflow catalog names.
        """
        from app.workflows.registry import list_workflows
        return list_workflows()

    def get_workflow_metadata(self, workflow_name: str) -> dict:
        """Get metadata for a specific workflow.

        Args:
            workflow_name: The catalog name of the workflow.

        Returns:
            Dictionary of workflow metadata (category, agents, pattern).
        """
        from app.workflows.registry import workflow_registry
        return workflow_registry.get_metadata(workflow_name)


# =============================================================================
# Module-level helpers
# =============================================================================

_user_agent_factory: Optional[UserAgentFactory] = None


def get_user_agent_factory() -> UserAgentFactory:
    """Get the singleton UserAgentFactory instance."""
    global _user_agent_factory
    if _user_agent_factory is None:
        _user_agent_factory = UserAgentFactory()
    return _user_agent_factory


async def get_executive_agent_for_user(user_id: str | UUID) -> "Agent":
    """Convenience function to get a personalized executive agent.

    This is the primary API for getting user-specific agents.

    Args:
        user_id: The user's UUID.

    Returns:
        Personalized ExecutiveAgent instance.
    """
    factory = get_user_agent_factory()
    return await factory.create_executive_agent(user_id)


async def get_user_workflow(user_id: str | UUID, workflow_name: str) -> Optional[Any]:
    """Convenience function to create a workflow for a user.

    Creates a fresh workflow instance using factory functions to avoid
    the ADK single-parent constraint.

    Args:
        user_id: The user's UUID.
        workflow_name: The catalog name of the workflow (e.g., "Initiative Ideation").

    Returns:
        A fresh workflow instance or None if not found.
    """
    factory = get_user_agent_factory()
    return await factory.create_user_workflow(user_id, workflow_name)


__all__ = [
    "UserAgentFactory",
    "get_user_agent_factory",
    "get_executive_agent_for_user",
    "get_user_workflow",
    "DEFAULT_EXECUTIVE_INSTRUCTION",
]
