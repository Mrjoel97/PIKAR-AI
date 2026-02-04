from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from uuid import UUID

class BusinessContext(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    goals: Optional[List[str]] = None
    team_size: Optional[str] = None
    role: Optional[str] = None
    website: Optional[str] = None

class UserPreferences(BaseModel):
    tone: Optional[str] = None
    verbosity: Optional[str] = None
    communication_style: Optional[str] = None
    notification_frequency: Optional[str] = None

class AgentSetup(BaseModel):
    agent_name: Optional[str] = None
    focus_areas: Optional[List[str]] = None

class Configuration(BaseModel):
    business_context: Optional[BusinessContext] = None
    preferences: Optional[UserPreferences] = None
    agent_setup: Optional[AgentSetup] = None

class UserExecutiveAgent(BaseModel):
    user_id: UUID
    agent_name: Optional[str] = None
    configuration: Configuration = Field(default_factory=Configuration)
    persona: Optional[Literal["solopreneur", "startup", "sme", "enterprise"]] = None
    onboarding_completed: bool = False
    system_prompt_override: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Legacy fields for backward compatibility if they exist in DB access
    business_context: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    
    model_config = {"from_attributes": True, "populate_by_name": True}
    
    @field_validator("configuration", mode="before")
    @classmethod
    def validate_configuration(cls, v: Any) -> Configuration:
        if isinstance(v, Configuration):
            return v
        if isinstance(v, dict):
            return Configuration.model_validate(v)
        return v
