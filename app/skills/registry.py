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

"""Skills Registry - Central registry for agent capabilities.

This module defines the Skill model and SkillsRegistry class that provides
a centralized way for agents to access domain-specific knowledge and tools.
"""

import hashlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Per-skill experiment cache TTL.  Short enough that a promote/revert decision
# made by the evaluator becomes visible quickly without restart; long enough
# that the hot path is not constantly hitting Supabase.
_EXPERIMENT_CACHE_TTL_SECONDS = 60


@dataclass(frozen=True)
class SkillResolution:
    """Result of resolving a skill for a specific user.

    Returned by SkillsRegistry.get_for_user().  The interaction logger reads
    these fields back from request_context to stamp interaction_logs rows.
    """

    skill: "Skill | None"
    skill_version_id: str | None  # active or experiment-arm version, when known
    experiment_id: str | None     # populated only when a running experiment was joined
    variant: str | None           # 'control' | 'treatment' | None when no experiment


class AgentID(str, Enum):
    """Unique identifiers for all agents in the Pikar AI ecosystem.

    Each agent has a short ID that can be used to map skills to agents.
    Skills can be assigned to multiple agents via their agent_ids field.
    """

    # Executive Agent - Central Orchestrator
    EXEC = "EXEC"  # ExecutiveAgent - Chief of Staff

    # Specialized Domain Agents
    FIN = "FIN"  # FinancialAnalysisAgent - CFO / Financial Analyst
    CONT = "CONT"  # ContentCreationAgent - CMO / Creative Director
    STRAT = "STRAT"  # StrategicPlanningAgent - Chief Strategy Officer
    SALES = "SALES"  # SalesIntelligenceAgent - Head of Sales
    MKT = "MKT"  # MarketingAutomationAgent - Marketing Director
    OPS = "OPS"  # OperationsOptimizationAgent - COO / Operations Manager
    HR = "HR"  # HRRecruitmentAgent - Human Resources Manager
    LEGAL = "LEGAL"  # ComplianceRiskAgent - Legal Counsel
    SUPP = "SUPP"  # CustomerSupportAgent - Customer Success Manager
    DATA = "DATA"  # DataAnalysisAgent - Data Analyst

    # Reserved for future agents (extensibility)
    # PRODUCT = "PRODUCT"    # ProductManagementAgent
    # RESEARCH = "RESEARCH"  # MarketResearchAgent
    # CUSTOMER = "CUSTOMER"  # CustomerSuccessAgent


# Mapping from AgentID to agent class names for reference
AGENT_ID_TO_NAME = {
    AgentID.EXEC: "ExecutiveAgent",
    AgentID.FIN: "FinancialAnalysisAgent",
    AgentID.CONT: "ContentCreationAgent",
    AgentID.STRAT: "StrategicPlanningAgent",
    AgentID.SALES: "SalesIntelligenceAgent",
    AgentID.MKT: "MarketingAutomationAgent",
    AgentID.OPS: "OperationsOptimizationAgent",
    AgentID.HR: "HRRecruitmentAgent",
    AgentID.LEGAL: "ComplianceRiskAgent",
    AgentID.SUPP: "CustomerSupportAgent",
    AgentID.DATA: "DataAnalysisAgent",
}


class Skill(BaseModel):
    """A modular capability or knowledge unit that agents can use.

    Skills can be:
    - Knowledge-based: Provide context/instructions (e.g., SEO checklist)
    - Function-based: Provide executable logic (e.g., calculation)

    Each skill is mapped to one or more agents via the agent_ids field.
    This allows agents to query which skills they have access to.
    """

    name: str = Field(..., description="Unique identifier for the skill")
    description: str = Field(..., description="What this skill does")
    category: str = Field(
        ...,
        description="Category: finance, hr, marketing, sales, compliance, content, data, support, operations",
    )

    # Agent mapping - which agents can use this skill
    agent_ids: list[AgentID] = Field(
        default_factory=list,
        description="List of agent IDs that can use this skill. Empty list means available to all agents.",
    )

    # Versioning
    version: str = Field(default="1.0.0", description="Semantic version of the skill")
    changelog: str | None = Field(
        default=None, description="What changed in this version"
    )

    # Knowledge content (for prompt injection)
    knowledge: str | None = Field(
        default=None, description="Domain knowledge to inject into agent context"
    )
    knowledge_summary: str | None = Field(
        default=None,
        description="2-3 line summary for fast injection; full knowledge used on-demand via use_skill(full_knowledge=True)",
    )

    # Optional callable for function-based skills
    implementation: Callable[..., Any] | None = Field(
        default=None, exclude=True, description="Optional function implementation"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SkillsRegistry:
    """Central registry for managing and accessing skills.

    Usage:
        registry = SkillsRegistry()
        registry.register(my_skill)
        skill = registry.get("my_skill_name")
    """

    _instance: "SkillsRegistry | None" = None

    def __new__(cls) -> "SkillsRegistry":
        """Singleton pattern to ensure one global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._skills: dict[str, Skill] = {}
            self._initialized = True

            # Custom skills should be loaded explicitly or lazily
            self._custom_skills_loaded = False

            # Per-skill A/B experiment cache.  Key = skill_name.
            # Value = (cached_entry, expires_at_monotonic).
            # cached_entry is a dict with keys: experiment_id, control_skill,
            # candidate_skill, or None to negatively cache "no experiment".
            self._experiment_cache: dict[str, tuple[dict | None, float]] = {}

    def _ensure_custom_skills_loaded(self) -> None:
        """Lazily load custom skills to avoid circular imports."""
        if not getattr(self, "_custom_skills_loaded", False):
            try:
                # Local import to avoid circular dependency at module level
                from app.skills.loader import load_custom_skills

                load_custom_skills()
                self._custom_skills_loaded = True
            except ImportError:
                # Log error but don't crash if loader isn't ready
                # useful during very early initialization or testing
                pass
            except Exception as e:
                logger.warning("Error loading custom skills: %s", e)

    def _fetch_running_experiment(self, name: str) -> dict | None:
        """Fetch the running experiment for *name* from Supabase, if any.

        Returns a dict with experiment_id, control_skill, candidate_skill,
        or None when no experiment is running.  Always swallows errors and
        returns None on failure — the caller must fall back to active version.
        """
        try:
            # Lazy import: avoid pulling Supabase into module-load chain.
            from app.services.supabase import get_service_client

            client = get_service_client()
            exp_resp = (
                client.table("skill_experiments")
                .select(
                    "id, control_version_id, candidate_version_id, "
                    "control:skill_versions!skill_experiments_control_version_id_fkey(id, knowledge), "
                    "candidate:skill_versions!skill_experiments_candidate_version_id_fkey(id, knowledge)"
                )
                .eq("skill_name", name)
                .eq("state", "running")
                .limit(1)
                .execute()
            )
        except Exception as e:
            logger.debug("experiment fetch failed for %s: %s", name, e)
            return None

        rows = getattr(exp_resp, "data", None) or []
        if not rows:
            return None

        row = rows[0]
        control_row = row.get("control") or {}
        candidate_row = row.get("candidate") or {}
        if not control_row or not candidate_row:
            return None

        base = self._skills.get(name)
        if base is None:
            # We must overlay onto an in-memory base to keep description/category
            # consistent.  If the base disappeared, fall through to active.
            return None

        return {
            "experiment_id": row["id"],
            "_control_version_id": control_row["id"],
            "_candidate_version_id": candidate_row["id"],
            "control_skill": self._skill_with_knowledge(
                base, control_row["id"], control_row.get("knowledge")
            ),
            "candidate_skill": self._skill_with_knowledge(
                base, candidate_row["id"], candidate_row.get("knowledge")
            ),
        }

    @staticmethod
    def _skill_with_knowledge(
        base: "Skill", version_id: str, knowledge: str | None
    ) -> "Skill":
        """Copy *base* with the version's knowledge content substituted in.

        The version_id is tracked separately via SkillResolution rather than
        being stored on the Skill model itself.
        """
        del version_id  # carried alongside in the cache entry / SkillResolution
        return base.model_copy(update={"knowledge": knowledge})

    def _get_cached_experiment(self, name: str) -> dict | None:
        """Return cached experiment entry for *name*, refreshing on TTL miss.

        Negative results are also cached so we don't hammer Supabase for
        skills that have no running experiment (the common case).
        """
        now = time.monotonic()
        cached = self._experiment_cache.get(name)
        if cached is not None and cached[1] > now:
            return cached[0]

        fresh = self._fetch_running_experiment(name)
        self._experiment_cache[name] = (fresh, now + _EXPERIMENT_CACHE_TTL_SECONDS)
        return fresh

    def _invalidate_experiment(self, name: str) -> None:
        """Drop the cached experiment entry for *name*.

        Called by the evaluator on promote/revert so the next request sees
        the updated state without waiting for TTL.
        """
        self._experiment_cache.pop(name, None)

    @staticmethod
    def _bucket(user_id: str, experiment_id: str) -> str:
        """Per-user sticky variant assignment.

        SHA-256 hash of user_id + experiment_id, mod 2.  Same user always
        sees the same variant for a given experiment.  Treat as a stable
        feature flag — never re-randomize mid-experiment.
        """
        key = f"{user_id}:{experiment_id}".encode()
        h = int(hashlib.sha256(key).hexdigest(), 16)
        return "control" if h % 2 == 0 else "treatment"

    def get_for_user(self, name: str, user_id: str | None) -> "SkillResolution":
        """Resolve a skill for a specific user, honoring any running experiment.

        Falls back to the active in-memory skill (no version stamping) when:
          - user_id is None (system jobs, schedulers, anonymous paths)
          - no experiment is running for this skill
          - any DB error or cache miss the fetcher couldn't resolve

        The returned SkillResolution is the canonical place callers should
        stash into request_context for downstream logging.
        """
        self._ensure_custom_skills_loaded()
        base = self._skills.get(name)
        if base is None:
            return SkillResolution(
                skill=None, skill_version_id=None, experiment_id=None, variant=None
            )

        if user_id is None:
            return SkillResolution(
                skill=base, skill_version_id=None, experiment_id=None, variant=None
            )

        entry = self._get_cached_experiment(name)
        if entry is None:
            return SkillResolution(
                skill=base, skill_version_id=None, experiment_id=None, variant=None
            )

        variant = self._bucket(user_id, entry["experiment_id"])
        if variant == "control":
            chosen_skill = entry["control_skill"]
            # Re-fetch the version_id from the raw entry (carried alongside).
            # The cache stores _skill_with_knowledge output without the id;
            # we re-derive it from the cached row via a parallel structure.
            version_id = entry.get("_control_version_id")
        else:
            chosen_skill = entry["candidate_skill"]
            version_id = entry.get("_candidate_version_id")

        return SkillResolution(
            skill=chosen_skill,
            skill_version_id=version_id,
            experiment_id=entry["experiment_id"],
            variant=variant,
        )

    def reload_skill_from_db(self, name: str) -> bool:
        """Re-read the active version's knowledge from skill_versions into memory.

        Called by the evaluator after promote so the in-memory `_skills[name]`
        carries the promoted candidate's knowledge.  Returns True on success.
        """
        try:
            from app.services.supabase import get_service_client

            client = get_service_client()
            resp = (
                client.table("skill_versions")
                .select("id, knowledge")
                .eq("skill_name", name)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
        except Exception as e:
            logger.warning("reload_skill_from_db failed for %s: %s", name, e)
            return False

        rows = getattr(resp, "data", None) or []
        if not rows:
            return False

        active = rows[0]
        existing = self._skills.get(name)
        if existing is None:
            return False
        self._skills[name] = existing.model_copy(
            update={"knowledge": active.get("knowledge")}
        )
        self._invalidate_experiment(name)
        return True

    def register(self, skill: Skill) -> None:
        """Register a skill in the registry."""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        self._ensure_custom_skills_loaded()
        return self._skills.get(name)

    def get_by_category(self, category: str) -> list[Skill]:
        """Get all skills in a category."""
        self._ensure_custom_skills_loaded()
        return [s for s in self._skills.values() if s.category == category]

    def get_by_agent_id(self, agent_id: AgentID) -> list[Skill]:
        """Get all skills assigned to a specific agent.

        Args:
            agent_id: The agent ID to filter skills by.

        Returns:
            List of skills that the agent has access to.
            Skills with empty agent_ids list are considered available to all.
        """
        self._ensure_custom_skills_loaded()
        return [
            s
            for s in self._skills.values()
            if agent_id in s.agent_ids or len(s.agent_ids) == 0
        ]

    def get_agent_skills_summary(self, agent_id: AgentID) -> dict[str, list[str]]:
        """Get a summary of skills for an agent, organized by category.

        Args:
            agent_id: The agent ID to get skills for.

        Returns:
            Dictionary mapping category -> list of skill names.
        """
        # get_by_agent_id already calls ensure_loaded
        skills = self.get_by_agent_id(agent_id)
        summary: dict[str, list[str]] = {}
        for skill in skills:
            if skill.category not in summary:
                summary[skill.category] = []
            summary[skill.category].append(skill.name)
        return summary

    def list_all(self) -> list[Skill]:
        """List all registered skills."""
        self._ensure_custom_skills_loaded()
        return list(self._skills.values())

    def list_names(self) -> list[str]:
        """List all skill names."""
        self._ensure_custom_skills_loaded()
        return list(self._skills.keys())

    def semantic_search(
        self,
        query: str,
        agent_id: "AgentID | None" = None,
        limit: int = 10,
        threshold: float = 0.45,
    ) -> list[dict]:
        """Search skills by semantic similarity using pre-computed embeddings.

        Args:
            query: Natural language search query.
            agent_id: Optional agent filter — only return skills this agent can access.
            limit: Maximum results.
            threshold: Minimum cosine similarity score (0.0–1.0).

        Returns:
            List of dicts with 'score' and 'skill' keys, sorted by score desc.
            Empty list if embeddings are unavailable (caller should fall back to keyword).
        """
        from app.skills.skill_embeddings import (
            cosine_similarity,
            get_skill_embedding,
            is_warmed,
        )

        if not is_warmed():
            return []

        try:
            from app.rag.embedding_service import generate_embedding

            query_emb = generate_embedding(query)
        except Exception:
            return []

        if not query_emb or all(v == 0.0 for v in query_emb):
            return []

        self._ensure_custom_skills_loaded()

        # Get skills available to this agent (or all)
        if agent_id is not None:
            candidates = self.get_by_agent_id(agent_id)
        else:
            candidates = list(self._skills.values())

        results = []
        for skill in candidates:
            skill_emb = get_skill_embedding(skill.name)
            if skill_emb:
                score = cosine_similarity(query_emb, skill_emb)
                if score >= threshold:
                    results.append({"score": score, "skill": skill})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def use_skill(
        self, name: str, agent_id: AgentID | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Use a skill - returns knowledge or executes function.

        Resolves the per-user variant when a skill_experiments row is running
        for this skill, then stashes the resolution into request_context so
        the interaction logger can stamp the eventual row.

        Args:
            name: The skill name to use.
            agent_id: The ID of the agent attempting to use the skill.
                     If provided, validates the agent has permission.
            **kwargs: Arguments to pass if skill has an implementation.

        Returns:
            Dictionary with skill output or knowledge.
            Returns error if agent lacks permission.
        """
        start_time = time.monotonic()

        # Resolve under any running A/B experiment.  Pulls user_id from the
        # request-scoped ContextVar; system paths (user_id=None) get the
        # in-memory active version unchanged.
        from app.services.request_context import (
            get_current_user_id,
            set_current_skill_resolution,
        )

        user_id = get_current_user_id()
        resolution = self.get_for_user(name, user_id)
        skill = resolution.skill

        if not skill:
            # Skill missing entirely: clear any stale resolution before logging.
            set_current_skill_resolution(None)
            self._log_usage(
                name,
                agent_id,
                success=False,
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {"success": False, "error": f"Skill '{name}' not found"}

        # Stamp downstream loggers with which version / variant served this turn.
        set_current_skill_resolution(
            {
                "skill_version_id": resolution.skill_version_id,
                "experiment_id": resolution.experiment_id,
                "variant": resolution.variant,
            }
        )

        # Validate agent has permission to use this skill
        if agent_id is not None and len(skill.agent_ids) > 0:
            if agent_id not in skill.agent_ids:
                allowed_agents = [aid.value for aid in skill.agent_ids]
                self._log_usage(
                    name,
                    agent_id,
                    success=False,
                    duration_ms=int((time.monotonic() - start_time) * 1000),
                )
                return {
                    "success": False,
                    "error": f"Agent '{agent_id.value}' does not have access to skill '{name}'. "
                    f"Allowed agents: {allowed_agents}",
                }

        result = {
            "success": True,
            "skill_name": name,
            "description": skill.description,
            "version": skill.version,
        }

        # If skill has implementation, execute it
        if skill.implementation:
            try:
                output = skill.implementation(**kwargs)
                result["output"] = output
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)

        # If skill has knowledge, include it
        use_full = kwargs.pop("full_knowledge", False)
        if use_full and skill.knowledge:
            result["knowledge"] = skill.knowledge
        elif skill.knowledge_summary:
            result["knowledge"] = skill.knowledge_summary
            result["hint"] = (
                "Call use_skill(name, full_knowledge=True) for the complete guide."
            )
        elif skill.knowledge:
            result["knowledge"] = skill.knowledge

        # Log usage telemetry (fire-and-forget)
        self._log_usage(
            name,
            agent_id,
            success=result.get("success", False),
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )

        return result

    def _log_usage(
        self, skill_name: str, agent_id: AgentID | None, success: bool, duration_ms: int
    ) -> None:
        """Fire-and-forget skill usage logging for analytics."""
        try:
            import logging

            from app.services.request_context import get_current_user_id

            user_id = get_current_user_id() or "unknown"
            logging.getLogger(__name__).info(
                "skill_usage | skill=%s agent=%s user=%s success=%s duration_ms=%d",
                skill_name,
                agent_id.value if agent_id else "any",
                user_id[:8] if user_id != "unknown" else user_id,
                success,
                duration_ms,
            )
        except Exception:
            pass  # Never break the skill call for telemetry


# Global registry instance
skills_registry = SkillsRegistry()


def get_skill_tool(skill_name: str) -> Callable:
    """Create a tool function for a specific skill.

    This allows skills to be exposed as ADK tools.
    """

    def skill_tool(**kwargs: Any) -> dict:
        """Execute the skill with provided arguments."""
        return skills_registry.use_skill(skill_name, **kwargs)

    skill_tool.__name__ = f"use_{skill_name}"
    skill_tool.__doc__ = f"Use the {skill_name} skill."

    return skill_tool
