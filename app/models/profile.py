from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

from app.models.user import BusinessContext, UserPreferences

class UserProfile(BaseModel):
    user_id: UUID
    full_name: Optional[str] = None
    persona: Optional[Literal["solopreneur", "startup", "sme", "enterprise"]] = None
    
    # We embed the models defined in user.py for consistency
    business_context: BusinessContext = Field(default_factory=BusinessContext)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    storage_bucket_id: Optional[str] = "user-content"
    storage_path_prefix: Optional[str] = None # Expects '{user_id}/' typically
    rag_knowledge_vault_id: Optional[UUID] = None
    
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
