"""UserAgentFactory - Factory for creating per-user ExecutiveAgent instances.

This service creates personalized ExecutiveAgent instances by loading user
configuration from the user_executive_agents table and injecting business
context into the agent's system prompt.
"""

import os
import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client

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

## SPECIALIZED AGENTS AVAILABLE
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
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing")
        self.client: Client = create_client(url, key)
        self._table_name = "user_executive_agents"
        self._cache: Dict[str, "Agent"] = {}  # Simple cache for agent instances

    async def get_user_config(self, user_id: str) -> Optional[dict]:
        """Load user's executive agent configuration from database.
        
        Args:
            user_id: The user's UUID.
            
        Returns:
            User configuration record or None if not found.
        """
        try:
            response = (
                self.client.table(self._table_name)
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
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
        user_id: str,
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
        if use_cache and user_id in self._cache:
            logger.debug(f"Returning cached agent for user {user_id}")
            return self._cache[user_id]

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
                if persona:
                    instruction = self._inject_persona_context(instruction, persona)

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

        # Create the personalized agent
        from google.adk.agents import Agent
        from google.adk.models import Gemini
        from google.genai import types

        agent = Agent(
            name=agent_name,
            model=Gemini(
                model="gemini-2.5-pro",
                retry_options=types.HttpRetryOptions(attempts=3),
            ),
            description="Chief of Staff / Central Orchestrator - Personalized for user",
            instruction=instruction,
            tools=[
                get_revenue_stats,
                search_business_knowledge,
                update_initiative_status,
                create_task,
            ],
            sub_agents=SPECIALIZED_AGENTS,
        )

        # Cache the agent
        if use_cache:
            self._cache[user_id] = agent

        logger.info(f"Created personalized agent '{agent_name}' for user {user_id}")
        return agent

    def invalidate_cache(self, user_id: str) -> None:
        """Remove cached agent for a user (call after config changes).

        Args:
            user_id: The user's UUID.
        """
        if user_id in self._cache:
            del self._cache[user_id]
            logger.debug(f"Invalidated cached agent for user {user_id}")

    def clear_cache(self) -> None:
        """Clear all cached agent instances."""
        self._cache.clear()
        logger.debug("Cleared all cached agents")

    async def update_user_config(
        self,
        user_id: str,
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
        data = {"user_id": user_id}

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

        if response.data:
            return response.data[0]
        raise Exception("No data returned from update config")

    async def create_user_workflow(
        self,
        user_id: str,
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


async def get_executive_agent_for_user(user_id: str) -> "Agent":
    """Convenience function to get a personalized executive agent.

    This is the primary API for getting user-specific agents.

    Args:
        user_id: The user's UUID.

    Returns:
        Personalized ExecutiveAgent instance.
    """
    factory = get_user_agent_factory()
    return await factory.create_executive_agent(user_id)


async def get_user_workflow(user_id: str, workflow_name: str) -> Optional[Any]:
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
