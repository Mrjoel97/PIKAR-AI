from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import BusinessContext, UserPreferences


class UserProfile(BaseModel):
    user_id: UUID
    full_name: str | None = None
    persona: Literal["solopreneur", "startup", "sme", "enterprise"] | None = None

    # We embed the models defined in user.py for consistency
    business_context: BusinessContext = Field(default_factory=BusinessContext)
    preferences: UserPreferences = Field(default_factory=UserPreferences)

    storage_bucket_id: str | None = "user-content"
    storage_path_prefix: str | None = None  # Expects '{user_id}/' typically
    rag_knowledge_vault_id: UUID | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
