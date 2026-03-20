from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BusinessContext(BaseModel):
    company_name: str | None = None
    industry: str | None = None
    description: str | None = None
    goals: list[str] | None = None
    team_size: str | None = None
    role: str | None = None
    website: str | None = None


class UserPreferences(BaseModel):
    tone: str | None = None
    verbosity: str | None = None
    communication_style: str | None = None
    notification_frequency: str | None = None


class AgentSetup(BaseModel):
    agent_name: str | None = None
    focus_areas: list[str] | None = None


class Configuration(BaseModel):
    business_context: BusinessContext | None = None
    preferences: UserPreferences | None = None
    agent_setup: AgentSetup | None = None


class UserExecutiveAgent(BaseModel):
    user_id: UUID
    agent_name: str | None = None
    configuration: Configuration = Field(default_factory=Configuration)
    persona: Literal["solopreneur", "startup", "sme", "enterprise"] | None = None
    onboarding_completed: bool = False
    system_prompt_override: str | None = None
    created_at: datetime
    updated_at: datetime

    # Legacy fields for backward compatibility if they exist in DB access
    business_context: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}

    @field_validator("configuration", mode="before")
    @classmethod
    def validate_configuration(cls, v: Any) -> Configuration:
        if isinstance(v, Configuration):
            return v
        if isinstance(v, dict):
            return Configuration.model_validate(v)
        return v
