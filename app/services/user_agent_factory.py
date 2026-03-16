"""UserAgentFactory - Factory for creating per-user ExecutiveAgent instances.

This service creates personalized ExecutiveAgent instances by loading user
configuration from the database and injecting business context into the
agent's system prompt.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from supabase import Client

from app.personas.prompt_fragments import (
    build_delegation_handoff_fragment,
    build_persona_policy_block,
    resolve_agent_name,
)
from app.services.cache import CacheResult, get_cache_service
from app.services.supabase_client import get_service_client

if TYPE_CHECKING:
    from google.adk.agents import Agent

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_DEFAULT_EXECUTIVE_INSTRUCTION_PATH = _PROMPTS_DIR / "executive_instruction.txt"

_USER_EXEC_AGENTS_TABLE = "user_executive_agents"
_USERS_PROFILE_TABLE = "users_profile"

_EMBEDDED_EXECUTIVE_INSTRUCTION = """You are the Executive Agent for Pikar AI - the Chief of Staff and Central Orchestrator.

## YOUR ROLE
You are the primary interface between the user and Pikar AI's multi-agent ecosystem. You oversee all business operations and coordinate specialized agents to accomplish complex tasks.
"""

USER_AGENT_PERSONALIZATION_STATE_KEY = "user_agent_personalization"


def _load_default_executive_instruction() -> str:
    """Load the canonical executive prompt from disk, falling back to an embedded copy."""
    try:
        return _DEFAULT_EXECUTIVE_INSTRUCTION_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "Falling back to embedded executive instruction; could not read %s: %s",
            _DEFAULT_EXECUTIVE_INSTRUCTION_PATH,
            exc,
        )
        return _EMBEDDED_EXECUTIVE_INSTRUCTION


DEFAULT_EXECUTIVE_INSTRUCTION = _load_default_executive_instruction()


def _extract_cache_value(result: Any) -> Any:
    """Return the payload from CacheResult or pass through mocked values in tests."""
    if isinstance(result, CacheResult):
        return result.value if result.found else None
    if hasattr(result, "found") and hasattr(result, "value"):
        return result.value if getattr(result, "found") else None
    return result


def _format_listish(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None)
    return str(value)


def build_business_context_section(business_context: Dict[str, Any]) -> str:
    """Build a reusable business-context section for prompt injection."""
    if not isinstance(business_context, dict) or not business_context:
        return ""

    lines = ["## YOUR USER'S BUSINESS CONTEXT"]
    if business_context.get("company_name"):
        lines.append(f"- Company: {business_context['company_name']}")
    if business_context.get("industry"):
        lines.append(f"- Industry: {business_context['industry']}")
    if business_context.get("team_size"):
        lines.append(f"- Team size: {business_context['team_size']}")
    if business_context.get("role"):
        lines.append(f"- Role: {business_context['role']}")
    if business_context.get("business_model"):
        lines.append(f"- Business model: {business_context['business_model']}")
    if business_context.get("goals"):
        lines.append(f"- Goals: {_format_listish(business_context['goals'])}")
    if business_context.get("challenges"):
        lines.append(f"- Challenges: {_format_listish(business_context['challenges'])}")
    if business_context.get("description"):
        lines.append(f"- Description: {business_context['description']}")
    if business_context.get("website"):
        lines.append(f"- Website: {business_context['website']}")
    lines.append("Use this context to make recommendations concrete and relevant to this business.")
    return "\n".join(lines)


def build_preferences_section(preferences: Dict[str, Any]) -> str:
    """Build a reusable communication-preferences section."""
    if not isinstance(preferences, dict) or not preferences:
        return ""

    lines = ["## COMMUNICATION PREFERENCES"]
    if preferences.get("tone"):
        lines.append(f"- Tone: {preferences['tone']}")
    if preferences.get("verbosity"):
        lines.append(f"- Verbosity: {preferences['verbosity']}")
    if preferences.get("communication_style"):
        lines.append(f"- Communication style: {preferences['communication_style']}")
    if preferences.get("format_preference"):
        lines.append(f"- Format preference: {preferences['format_preference']}")
    if preferences.get("notification_frequency"):
        lines.append(f"- Notification cadence preference: {preferences['notification_frequency']}")
    return "\n".join(lines)


def build_runtime_personalization_block(
    personalization: Dict[str, Any],
    *,
    agent_name: str | None = None,
) -> str:
    """Build the additive personalization block for live chat sessions."""
    if not isinstance(personalization, dict) or not personalization:
        return ""

    sections: list[str] = []

    business_section = build_business_context_section(personalization.get("business_context") or {})
    if business_section:
        sections.append(business_section)

    resolved_agent_name = resolve_agent_name(agent_name)
    include_routing = resolved_agent_name in {None, "ExecutiveAgent"}
    persona_block = build_persona_policy_block(
        personalization.get("persona"),
        agent_name=agent_name,
        include_routing=include_routing,
    )
    if persona_block:
        sections.append(persona_block)

    if resolved_agent_name and resolved_agent_name != "ExecutiveAgent":
        delegation_block = build_delegation_handoff_fragment(
            personalization.get("persona"),
            resolved_agent_name,
        )
        if delegation_block:
            sections.append(delegation_block)

    preferences_section = build_preferences_section(personalization.get("preferences") or {})
    if preferences_section:
        sections.append(preferences_section)

    if not sections:
        return ""

    body = "\n\n".join(section.strip() for section in sections if section.strip())
    return (
        "\n[USER PERSONALIZATION PROFILE - tailor planning, tone, recommendations, and execution accordingly]\n"
        f"{body}\n"
        "[END USER PERSONALIZATION PROFILE]\n"
    )


class UserAgentFactory:
    """Factory for creating personalized ExecutiveAgent instances."""

    def __init__(self):
        self.client: Client = get_service_client()
        self._table_name = _USER_EXEC_AGENTS_TABLE
        self._cache: Dict[str, "Agent"] = {}
        self._redis_cache = get_cache_service()

    async def get_user_config(self, user_id: str | UUID) -> Optional[dict[str, Any]]:
        """Load merged user configuration from profile and agent tables."""
        user_id_str = str(user_id)

        try:
            cached_config = _extract_cache_value(await self._redis_cache.get_user_config(user_id_str))
            if isinstance(cached_config, dict) and cached_config:
                logger.debug("Cache hit for user config %s", user_id_str)
                return cached_config
        except Exception as exc:
            logger.warning("Cache read failed for %s: %s", user_id_str, exc)

        config: dict[str, Any] = {}
        found_any = False

        try:
            agent_response = await execute_async(
                self.client.table(self._table_name)
                .select("agent_name, persona, system_prompt_override, configuration")
                .eq("user_id", user_id_str)
                .single(),
                op_name="user_agent_factory.agent_config",
            )
            agent_data = agent_response.data or {}
            if agent_data:
                found_any = True
                stored_configuration = agent_data.get("configuration")
                if isinstance(stored_configuration, dict):
                    config.update(stored_configuration)
                if agent_data.get("agent_name"):
                    config["agent_name"] = agent_data["agent_name"]
                if agent_data.get("system_prompt_override"):
                    config["system_prompt_override"] = agent_data["system_prompt_override"]
                if agent_data.get("persona"):
                    config["persona"] = agent_data["persona"]
        except Exception as exc:
            logger.debug("No agent config found for user %s: %s", user_id_str, exc)

        try:
            profile_response = await execute_async(
                self.client.table(_USERS_PROFILE_TABLE)
                .select("business_context, preferences, persona")
                .eq("user_id", user_id_str)
                .single(),
                op_name="user_agent_factory.profile_config",
            )
            profile_data = profile_response.data or {}
            if profile_data:
                found_any = True
                if isinstance(profile_data.get("business_context"), dict):
                    config["business_context"] = profile_data["business_context"]
                if isinstance(profile_data.get("preferences"), dict):
                    config["preferences"] = profile_data["preferences"]
                if profile_data.get("persona"):
                    config["persona"] = profile_data["persona"]
        except Exception as exc:
            logger.debug("No profile config found for user %s: %s", user_id_str, exc)

        if found_any:
            try:
                await self._redis_cache.set_user_config(user_id_str, config)
            except Exception as exc:
                logger.warning("Could not cache merged config for %s: %s", user_id_str, exc)
            return config
        return None

    def _inject_business_context(self, base_instruction: str, business_context: Dict[str, Any]) -> str:
        context_section = build_business_context_section(business_context)
        if not context_section:
            return base_instruction
        if "## YOUR RESPONSIBILITIES" in base_instruction:
            return base_instruction.replace(
                "## YOUR RESPONSIBILITIES",
                f"{context_section}\n\n## YOUR RESPONSIBILITIES",
                1,
            )
        return f"{base_instruction}\n\n{context_section}"

    def _inject_persona_context(self, base_instruction: str, persona: str) -> str:
        guide = build_persona_policy_block(persona, agent_name="ExecutiveAgent", include_routing=True)
        if not guide:
            return base_instruction
        if "## YOUR ROLE" in base_instruction:
            return base_instruction.replace("## YOUR ROLE", f"{guide}\n\n## YOUR ROLE", 1)
        return f"{guide}\n\n{base_instruction}"

    def _apply_preferences(self, instruction: str, preferences: Dict[str, Any]) -> str:
        pref_section = build_preferences_section(preferences)
        if not pref_section:
            return instruction
        return f"{instruction}\n\n{pref_section}"

    async def _resolve_persona(
        self,
        user_id: str | UUID,
        config: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        if config and config.get("persona"):
            return str(config["persona"]).strip().lower()

        user_id_str = str(user_id)
        try:
            cached_persona = _extract_cache_value(await self._redis_cache.get_user_persona(user_id_str))
            if cached_persona:
                return str(cached_persona).strip().lower()
        except Exception as exc:
            logger.warning("Persona cache lookup failed for %s: %s", user_id_str, exc)

        if not config:
            config = await self.get_user_config(user_id_str)
        if config and config.get("persona"):
            return str(config["persona"]).strip().lower()
        return None

    async def get_runtime_personalization(self, user_id: str | UUID) -> Dict[str, Any]:
        """Return lightweight personalization state for live chat sessions."""
        config = await self.get_user_config(user_id)
        persona = await self._resolve_persona(user_id, config)

        personalization: Dict[str, Any] = {}
        if config:
            business_context = config.get("business_context", {})
            if isinstance(business_context, dict) and business_context:
                personalization["business_context"] = business_context

            preferences = config.get("preferences", {})
            if isinstance(preferences, dict) and preferences:
                personalization["preferences"] = preferences

            if config.get("agent_name"):
                personalization["agent_name"] = config["agent_name"]

            system_prompt_override = config.get("system_prompt_override")
            if isinstance(system_prompt_override, str) and system_prompt_override.strip():
                personalization["system_prompt_override"] = system_prompt_override.strip()

        if persona:
            personalization["persona"] = persona

        return personalization

    async def create_executive_agent(
        self,
        user_id: str | UUID,
        use_cache: bool = True,
    ) -> "Agent":
        """Create a personalized ExecutiveAgent for the user."""
        user_id_str = str(user_id)
        if use_cache and user_id_str in self._cache:
            logger.debug("Returning cached agent for user %s", user_id_str)
            return self._cache[user_id_str]

        config = await self.get_user_config(user_id)

        if config and config.get("system_prompt_override"):
            instruction = str(config["system_prompt_override"])
        else:
            instruction = DEFAULT_EXECUTIVE_INSTRUCTION
            if config:
                business_context = config.get("business_context", {})
                if business_context:
                    instruction = self._inject_business_context(instruction, business_context)

                persona = await self._resolve_persona(user_id, config)
                if persona:
                    instruction = self._inject_persona_context(instruction, persona)

                preferences = config.get("preferences", {})
                if preferences:
                    instruction = self._apply_preferences(instruction, preferences)

        agent_name = "ExecutiveAgent"
        if config and config.get("agent_name"):
            agent_name = str(config["agent_name"])

        try:
            from app.agent import _EXECUTIVE_TOOLS as executive_tools
        except Exception:
            executive_tools = []

        from app.agents.context_extractor import (
            context_memory_after_tool_callback,
            context_memory_before_model_callback,
        )
        from app.agents.shared import ROUTING_AGENT_CONFIG, get_routing_model
        from app.agents.specialized_agents import SPECIALIZED_AGENTS
        from google.adk.agents import Agent

        agent = Agent(
            name=agent_name,
            model=get_routing_model(),
            description="Chief of Staff / Central Orchestrator - Personalized for user",
            instruction=instruction,
            tools=executive_tools,
            sub_agents=SPECIALIZED_AGENTS,
            generate_content_config=ROUTING_AGENT_CONFIG,
            before_model_callback=context_memory_before_model_callback,
            after_tool_callback=context_memory_after_tool_callback,
        )

        if use_cache:
            self._cache[user_id_str] = agent

        logger.info("Created personalized agent '%s' for user %s", agent_name, user_id_str)
        return agent

    def invalidate_cache(self, user_id: str | UUID) -> None:
        user_id_str = str(user_id)
        if user_id_str in self._cache:
            del self._cache[user_id_str]
            logger.debug("Invalidated cached agent for user %s", user_id_str)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._redis_cache.invalidate_user_all(user_id_str))
        except RuntimeError:
            logger.debug("No running loop available to invalidate Redis cache for %s", user_id_str)

    def clear_cache(self) -> None:
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
        """Update user's executive agent configuration."""
        user_id_str = str(user_id)
        agent_data = {"user_id": user_id_str}
        profile_updates: dict[str, Any] = {"user_id": user_id_str}
        update_profile = False

        if agent_name is not None:
            agent_data["agent_name"] = agent_name
        if system_prompt_override is not None:
            agent_data["system_prompt_override"] = system_prompt_override
        if business_context is not None:
            profile_updates["business_context"] = business_context
            update_profile = True
        if preferences is not None:
            profile_updates["preferences"] = preferences
            update_profile = True

        response = await execute_async(
            self.client.table(self._table_name).upsert(agent_data, on_conflict="user_id"),
            op_name="user_agent_factory.upsert_agent",
        )
        if update_profile:
            await execute_async(
                self.client.table(_USERS_PROFILE_TABLE).upsert(profile_updates, on_conflict="user_id"),
                op_name="user_agent_factory.upsert_profile",
            )

        self.invalidate_cache(user_id_str)
        await self._redis_cache.invalidate_user_config(user_id_str)

        if response.data:
            return response.data[0]
        raise Exception("No data returned from update config")

    async def create_user_workflow(
        self,
        user_id: str | UUID,
        workflow_name: str,
    ) -> Optional[Any]:
        """Create a user-specific workflow instance."""
        from app.workflows.registry import get_workflow_factory

        factory = get_workflow_factory(workflow_name)
        if factory is None:
            logger.warning("Workflow '%s' not found in registry", workflow_name)
            return None

        try:
            workflow = factory()
            logger.debug("Created workflow '%s' for user %s", workflow_name, user_id)
            return workflow
        except Exception as exc:
            logger.error("Failed to create workflow '%s': %s", workflow_name, exc)
            return None

    def list_available_workflows(self) -> list[str]:
        from app.workflows.registry import list_workflows

        return list_workflows()

    def get_workflow_metadata(self, workflow_name: str) -> dict:
        from app.workflows.registry import workflow_registry

        return workflow_registry.get_metadata(workflow_name)


_user_agent_factory: Optional[UserAgentFactory] = None


def get_user_agent_factory() -> UserAgentFactory:
    global _user_agent_factory
    if _user_agent_factory is None:
        _user_agent_factory = UserAgentFactory()
    return _user_agent_factory


async def get_executive_agent_for_user(user_id: str | UUID) -> "Agent":
    factory = get_user_agent_factory()
    return await factory.create_executive_agent(user_id)


async def get_user_workflow(user_id: str | UUID, workflow_name: str) -> Optional[Any]:
    factory = get_user_agent_factory()
    return await factory.create_user_workflow(user_id, workflow_name)


__all__ = [
    "UserAgentFactory",
    "get_user_agent_factory",
    "get_executive_agent_for_user",
    "get_user_workflow",
    "DEFAULT_EXECUTIVE_INSTRUCTION",
    "USER_AGENT_PERSONALIZATION_STATE_KEY",
    "build_business_context_section",
    "build_preferences_section",
    "build_runtime_personalization_block",
]
