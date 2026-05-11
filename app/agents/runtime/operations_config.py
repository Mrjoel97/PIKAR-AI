# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Per-agent declarative tunables (`operations.yaml`).

Loaded once when an agent factory builds the agent. Malformed config
fails fast — the agent does not load. Defaults mirror the example
in the design spec (§ 15) so an `operations.yaml` may be as small as
``agent_id: <name>``.

Strictness: every nested model sets ``extra="forbid"`` so a typo in
the YAML surfaces as a ``pydantic.ValidationError`` instead of being
silently dropped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

_StrictModel = ConfigDict(extra="forbid")


class ModelConfig(BaseModel):
    """Primary + fallback model identifiers used by the agent."""

    model_config = _StrictModel

    primary: str = "gemini-2.5-pro"
    fallback: str = "gemini-2.5-flash"


class RetryConfig(BaseModel):
    """Exponential backoff retry policy applied to model + tool calls."""

    model_config = _StrictModel

    max_attempts: int = 5
    backoff_initial_s: float = 2.0
    backoff_multiplier: float = 2.0
    backoff_max_s: float = 60.0


class ApprovalConfig(BaseModel):
    """When an agent must escalate before acting."""

    model_config = _StrictModel

    required_above_usd: float | None = None
    required_for_external_send: bool = False


class ResearchConfig(BaseModel):
    """Research-mode iteration + sourcing floor."""

    model_config = _StrictModel

    max_iterations: int = 3
    required_source_min: int = 3


class AuditConfig(BaseModel):
    """How strict the audit gate is when verifying initiative outputs."""

    model_config = _StrictModel

    fail_on_any_unmet_criterion: bool = True
    escalate_on_partial: bool = False


class SkillsInjectionConfig(BaseModel):
    """Top-K skill retrieval parameters."""

    model_config = _StrictModel

    top_k: int = 5
    similarity_floor: float = 0.65


class SkillsConfig(BaseModel):
    """Which skill IDs the agent may use + injection tuning."""

    model_config = _StrictModel

    # "*" means "any skill"; concrete entries support glob-style prefixes
    # like "finance:*" — matching logic lives in the skills registry, not
    # here.
    allowed_ids: list[str] = Field(default_factory=lambda: ["*"])
    injection: SkillsInjectionConfig = Field(default_factory=SkillsInjectionConfig)


class InitiativeConfig(BaseModel):
    """What this agent can do inside the initiative lifecycle."""

    model_config = _StrictModel

    phases_owned: list[str] = Field(default_factory=list)
    can_advance_phase: bool = False
    can_close: bool = False


class MemoryConfig(BaseModel):
    """Agent memory retention + retrieval tuning."""

    model_config = _StrictModel

    history_retention_months: int = 18
    retrieval_top_k: int = 4


class CompactionConfig(BaseModel):
    """When and how to compact the conversation history."""

    model_config = _StrictModel

    trigger_token_count: int = 80_000
    keep_last_n_turns: int = 12


class RoutingConfig(BaseModel):
    """Last-resort routing when the task-router classifier is ambiguous."""

    model_config = _StrictModel

    last_resort_default: Literal["direct", "initiative"] = "direct"


class OperationsConfig(BaseModel):
    """Top-level ``operations.yaml`` schema.

    ``extra='forbid'`` on every layer so a typo in the YAML fails fast
    instead of silently defaulting. Defaults come from the spec § 15
    example and are designed so a minimal agent only needs ``agent_id``.
    """

    model_config = _StrictModel

    agent_id: str
    model: ModelConfig = Field(default_factory=ModelConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    initiative: InitiativeConfig = Field(default_factory=InitiativeConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    compaction: CompactionConfig = Field(default_factory=CompactionConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)

    @classmethod
    def load(cls, path: Path | str) -> OperationsConfig:
        """Load + validate ``operations.yaml`` at ``path``.

        Raises:
            FileNotFoundError: if ``path`` does not exist.
            ValueError: if the file is not valid YAML (wraps
                ``yaml.YAMLError`` with a clear, agent-actionable message).
            pydantic.ValidationError: if the YAML parses but does not
                match the schema (missing ``agent_id``, unknown keys,
                wrong types, etc.).
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"operations.yaml not found at {path}")
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ValueError(
                f"operations.yaml at {path} is not valid YAML: {exc}"
            ) from exc
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(
                f"operations.yaml at {path} must be a YAML mapping at the top level, "
                f"got {type(data).__name__}"
            )
        return cls.model_validate(data)


__all__ = [
    "ApprovalConfig",
    "AuditConfig",
    "CompactionConfig",
    "InitiativeConfig",
    "MemoryConfig",
    "ModelConfig",
    "OperationsConfig",
    "ResearchConfig",
    "RetryConfig",
    "RoutingConfig",
    "SkillsConfig",
    "SkillsInjectionConfig",
    "ValidationError",
]
