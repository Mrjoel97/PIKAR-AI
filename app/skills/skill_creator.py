"""SkillCreator - System for creating user-specific custom skills.

This module provides the core logic for generating new skills based on:
1. User requirements and descriptions
2. Existing skill templates
3. Domain expertise from specialized agents

The skill creation process follows a structured flow:
1. User describes what skill they need
2. System identifies appropriate base template
3. AI generates skill content (name, description, knowledge)
4. Skill is validated and stored for the user
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.skills.registry import AgentID, Skill, skills_registry
from app.skills.custom_skills_service import (
    CustomSkillsService, 
    get_custom_skills_service
)


# =============================================================================
# Skill Creation Request/Response Models
# =============================================================================

class SkillCreationRequest(BaseModel):
    """Request to create a new custom skill."""
    
    user_id: str = Field(..., description="User's UUID")
    skill_name: str = Field(..., description="Desired name for the skill")
    skill_description: str = Field(..., description="User's description of what the skill should do")
    category: str = Field(..., description="Category (e.g., 'marketing', 'content', 'finance')")
    target_agents: List[str] = Field(
        default_factory=list,
        description="Agent IDs that should have access (e.g., ['MKT', 'CONT'])"
    )
    base_skill_name: Optional[str] = Field(
        None, 
        description="Name of existing skill to use as template"
    )
    additional_knowledge: Optional[str] = Field(
        None,
        description="Additional knowledge/instructions to include"
    )


class SkillCreationResult(BaseModel):
    """Result of skill creation operation."""
    
    success: bool
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    error_message: Optional[str] = None
    validation_errors: List[str] = Field(default_factory=list)


class SkillSuggestion(BaseModel):
    """A suggested skill based on user request analysis."""
    
    suggested_name: str
    suggested_description: str
    suggested_category: str
    suggested_agents: List[str]
    similar_existing_skills: List[str]
    confidence_score: float = Field(ge=0.0, le=1.0)


# =============================================================================
# Skill Creator Class
# =============================================================================

class SkillCreator:
    """Creates custom skills for users based on their requirements.
    
    This class handles:
    - Validating skill creation requests
    - Finding suitable template skills
    - Generating skill content
    - Storing created skills via CustomSkillsService
    """
    
    # Valid categories for skills
    VALID_CATEGORIES = [
        "finance", "hr", "marketing", "sales", "compliance",
        "content", "data", "support", "operations", "planning",
        "design", "development", "meta", "marketing_cro", "copywriting"
    ]
    
    def __init__(self, custom_skills_service: Optional[CustomSkillsService] = None):
        """Initialize SkillCreator with optional custom service instance."""
        self._service = custom_skills_service or get_custom_skills_service()
    
    def validate_request(self, request: SkillCreationRequest) -> List[str]:
        """Validate a skill creation request.
        
        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []
        
        # Validate skill name
        if not request.skill_name:
            errors.append("Skill name is required")
        elif len(request.skill_name) < 3:
            errors.append("Skill name must be at least 3 characters")
        elif len(request.skill_name) > 50:
            errors.append("Skill name must be 50 characters or less")
        elif not request.skill_name.replace("_", "").replace("-", "").isalnum():
            errors.append("Skill name can only contain letters, numbers, underscores, and hyphens")
        
        # Validate description
        if not request.skill_description:
            errors.append("Skill description is required")
        elif len(request.skill_description) < 10:
            errors.append("Skill description must be at least 10 characters")
        
        # Validate category
        if request.category not in self.VALID_CATEGORIES:
            errors.append(f"Invalid category. Must be one of: {', '.join(self.VALID_CATEGORIES)}")
        
        # Validate agent IDs
        valid_agent_ids = {aid.value for aid in AgentID}
        for agent_id in request.target_agents:
            if agent_id not in valid_agent_ids:
                errors.append(f"Invalid agent ID: {agent_id}")
        
        # Check if skill name already exists for user
        # This will be done async in the create method
        
        return errors
    
    def find_similar_skills(
        self, 
        description: str, 
        category: str,
        limit: int = 5
    ) -> List[Skill]:
        """Find existing skills similar to the requested description.
        
        Uses simple keyword matching. Could be enhanced with embeddings.
        """
        keywords = set(description.lower().split())
        scored_skills = []
        
        for skill in skills_registry.list_all():
            # Score based on category match and keyword overlap
            score = 0.0
            if skill.category == category:
                score += 0.3
            
            skill_keywords = set(skill.description.lower().split())
            if skill.knowledge:
                skill_keywords.update(skill.knowledge.lower().split())
            
            overlap = len(keywords & skill_keywords)
            if overlap > 0:
                score += min(0.7, overlap * 0.1)
            
            if score > 0:
                scored_skills.append((score, skill))
        
        # Sort by score descending and return top matches
        scored_skills.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored_skills[:limit]]

    def get_base_skill_template(
        self,
        base_skill_name: Optional[str],
        category: str,
        description: str
    ) -> Optional[Skill]:
        """Get an existing skill to use as a template.

        If base_skill_name is provided, uses that. Otherwise finds
        the most similar skill in the category.
        """
        if base_skill_name:
            return skills_registry.get(base_skill_name)

        # Find most similar skill
        similar = self.find_similar_skills(description, category, limit=1)
        return similar[0] if similar else None

    def generate_skill_knowledge(
        self,
        description: str,
        base_skill: Optional[Skill],
        additional_knowledge: Optional[str]
    ) -> str:
        """Generate knowledge content for the new skill.

        Combines:
        - User's description and requirements
        - Knowledge from base skill template (if any)
        - Additional knowledge provided
        """
        sections = []

        # Header from description
        sections.append(f"## Overview\n{description}\n")

        # Add knowledge from base skill if available
        if base_skill and base_skill.knowledge:
            sections.append(f"## Foundation (from {base_skill.name})\n{base_skill.knowledge}\n")

        # Add user-provided additional knowledge
        if additional_knowledge:
            sections.append(f"## Additional Guidelines\n{additional_knowledge}\n")

        return "\n".join(sections)

    async def create_skill(
        self,
        request: SkillCreationRequest
    ) -> SkillCreationResult:
        """Create a new custom skill from the request.

        This is the main entry point for skill creation.

        Args:
            request: The skill creation request.

        Returns:
            SkillCreationResult with success status and details.
        """
        # Validate request
        validation_errors = self.validate_request(request)
        if validation_errors:
            return SkillCreationResult(
                success=False,
                validation_errors=validation_errors
            )

        # Check if skill name already exists for this user
        existing = await self._service.get_custom_skill_by_name(
            user_id=request.user_id,
            name=request.skill_name
        )
        if existing:
            return SkillCreationResult(
                success=False,
                error_message=f"Skill '{request.skill_name}' already exists"
            )

        # Get base skill template if specified
        base_skill = self.get_base_skill_template(
            base_skill_name=request.base_skill_name,
            category=request.category,
            description=request.skill_description
        )

        # Generate skill knowledge
        knowledge = self.generate_skill_knowledge(
            description=request.skill_description,
            base_skill=base_skill,
            additional_knowledge=request.additional_knowledge
        )

        # Determine agent IDs
        agent_ids = request.target_agents
        if not agent_ids and base_skill:
            # Inherit from base skill if not specified
            agent_ids = [aid.value for aid in base_skill.agent_ids]
        if not agent_ids:
            # Default to EXEC if nothing specified
            agent_ids = [AgentID.EXEC.value]

        # Create the skill in database
        try:
            record = await self._service.create_custom_skill(
                user_id=request.user_id,
                name=request.skill_name,
                description=request.skill_description,
                category=request.category,
                agent_ids=agent_ids,
                knowledge=knowledge,
                based_on_skill=base_skill.name if base_skill else None,
                metadata={
                    "created_via": "skill_creator",
                    "base_skill": base_skill.name if base_skill else None,
                }
            )

            return SkillCreationResult(
                success=True,
                skill_id=record["id"],
                skill_name=record["name"]
            )

        except Exception as e:
            return SkillCreationResult(
                success=False,
                error_message=str(e)
            )

    async def suggest_skill(
        self,
        user_description: str,
        category_hint: Optional[str] = None
    ) -> SkillSuggestion:
        """Analyze user description and suggest a skill structure.

        This helps users by suggesting:
        - A standardized name
        - A refined description
        - Appropriate category
        - Which agents should have access
        - Similar existing skills they might use instead
        """
        # Simple heuristics for category detection
        description_lower = user_description.lower()

        # Category detection based on keywords
        category_keywords = {
            "finance": ["financial", "budget", "revenue", "cost", "profit", "money"],
            "marketing": ["marketing", "campaign", "brand", "advertising", "promotion"],
            "content": ["content", "writing", "blog", "article", "copy", "creative"],
            "sales": ["sales", "lead", "prospect", "deal", "pipeline", "customer"],
            "hr": ["hiring", "recruit", "employee", "performance", "team"],
            "compliance": ["compliance", "legal", "regulation", "risk", "audit"],
            "data": ["data", "analytics", "metrics", "dashboard", "report"],
            "operations": ["process", "workflow", "efficiency", "automation"],
        }

        detected_category = category_hint or "meta"
        max_matches = 0

        for cat, keywords in category_keywords.items():
            matches = sum(1 for kw in keywords if kw in description_lower)
            if matches > max_matches:
                max_matches = matches
                detected_category = cat

        # Agent suggestion based on category
        category_to_agents = {
            "finance": [AgentID.FIN.value, AgentID.DATA.value],
            "marketing": [AgentID.MKT.value, AgentID.CONT.value],
            "content": [AgentID.CONT.value, AgentID.MKT.value],
            "sales": [AgentID.SALES.value, AgentID.MKT.value],
            "hr": [AgentID.HR.value],
            "compliance": [AgentID.LEGAL.value],
            "data": [AgentID.DATA.value, AgentID.FIN.value],
            "operations": [AgentID.OPS.value],
        }

        suggested_agents = category_to_agents.get(
            detected_category,
            [AgentID.EXEC.value]
        )

        # Generate name from description (simple approach)
        words = user_description.lower().split()[:5]
        suggested_name = "_".join(w for w in words if w.isalnum())[:30]

        # Find similar skills
        similar = self.find_similar_skills(user_description, detected_category, limit=3)

        # Calculate confidence based on how well we matched
        confidence = min(1.0, 0.5 + (max_matches * 0.1) + (0.2 if similar else 0))

        return SkillSuggestion(
            suggested_name=suggested_name,
            suggested_description=user_description,
            suggested_category=detected_category,
            suggested_agents=suggested_agents,
            similar_existing_skills=[s.name for s in similar],
            confidence_score=confidence
        )


# =============================================================================
# Module-level helpers
# =============================================================================

_skill_creator: Optional[SkillCreator] = None


def get_skill_creator() -> SkillCreator:
    """Get the singleton SkillCreator instance."""
    global _skill_creator
    if _skill_creator is None:
        _skill_creator = SkillCreator()
    return _skill_creator


async def create_custom_skill(
    user_id: str,
    skill_name: str,
    description: str,
    category: str,
    target_agents: Optional[List[str]] = None,
    base_skill_name: Optional[str] = None,
    additional_knowledge: Optional[str] = None
) -> SkillCreationResult:
    """Convenience function to create a custom skill.

    This is the primary API for skill creation from agents.
    """
    creator = get_skill_creator()
    request = SkillCreationRequest(
        user_id=user_id,
        skill_name=skill_name,
        skill_description=description,
        category=category,
        target_agents=target_agents or [],
        base_skill_name=base_skill_name,
        additional_knowledge=additional_knowledge
    )
    return await creator.create_skill(request)

