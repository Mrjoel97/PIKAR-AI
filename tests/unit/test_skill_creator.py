import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.skills.skill_creator import (
    SkillCreator,
    SkillCreationRequest,
    SkillCreationResult,
    SkillSuggestion,
    AgentID
)
from app.skills.custom_skills_service import CustomSkillsService
from app.skills.registry import Skill, AgentID

@pytest.fixture
def mock_custom_skills_service():
    service = Mock(spec=CustomSkillsService)
    service.get_custom_skill_by_name = AsyncMock(return_value=None)
    service.create_custom_skill = AsyncMock(return_value={"id": "skill-123", "name": "test_skill"})
    return service

@pytest.fixture
def skill_creator(mock_custom_skills_service):
    return SkillCreator(custom_skills_service=mock_custom_skills_service)

class TestSkillCreatorValidation:
    def test_validate_request_valid(self, skill_creator):
        request = SkillCreationRequest(
            user_id="user-123",
            skill_name="valid_skill",
            skill_description="A valid skill description with enough length",
            category="finance",
            target_agents=[AgentID.FIN.value]
        )
        errors = skill_creator.validate_request(request)
        assert len(errors) == 0

    def test_validate_request_invalid_name_short(self, skill_creator):
        request = SkillCreationRequest(
            user_id="user-123",
            skill_name="no",
            skill_description="Valid description",
            category="finance"
        )
        errors = skill_creator.validate_request(request)
        assert any("at least 3 characters" in e for e in errors)

    def test_validate_request_invalid_name_chars(self, skill_creator):
        request = SkillCreationRequest(
            user_id="user-123",
            skill_name="bad name!",
            skill_description="Valid description",
            category="finance"
        )
        errors = skill_creator.validate_request(request)
        assert any("only contain letters" in e for e in errors)

    def test_validate_request_invalid_category(self, skill_creator):
        request = SkillCreationRequest(
            user_id="user-123",
            skill_name="valid_name",
            skill_description="Valid description",
            category="invalid_category"
        )
        errors = skill_creator.validate_request(request)
        assert any("Invalid category" in e for e in errors)

class TestSkillCreatorSuggestion:
    @pytest.mark.asyncio
    async def test_suggest_skill_category_detection(self, skill_creator):
        # Finance keywords
        desc = "I need to analyze financial budgets and revenue"
        suggestion = await skill_creator.suggest_skill(desc)
        assert suggestion.suggested_category == "finance"
        assert AgentID.FIN.value in suggestion.suggested_agents

        # Marketing keywords
        desc = "Create a marketing campaign for brand awareness"
        suggestion = await skill_creator.suggest_skill(desc)
        assert suggestion.suggested_category == "marketing"
        assert AgentID.MKT.value in suggestion.suggested_agents

    @pytest.mark.asyncio
    async def test_suggest_skill_default(self, skill_creator):
        desc = "Do something generic"
        suggestion = await skill_creator.suggest_skill(desc)
        assert suggestion.suggested_category == "meta"  # Default fallback logic
        assert AgentID.EXEC.value in suggestion.suggested_agents

class TestSkillCreatorKnowledge:
    def test_generate_skill_knowledge_basic(self, skill_creator):
        desc = "My skill description"
        knowledge = skill_creator.generate_skill_knowledge(desc, None, None)
        assert "## Overview" in knowledge
        assert desc in knowledge

    def test_generate_skill_knowledge_with_base(self, skill_creator):
        desc = "My skill"
        base_skill = Skill(
            name="base", 
            description="base desc", 
            category="finance", 
            agent_ids=[AgentID.FIN],
            knowledge="Base knowledge content"
        )
        knowledge = skill_creator.generate_skill_knowledge(desc, base_skill, None)
        assert "## Foundation (from base)" in knowledge
        assert "Base knowledge content" in knowledge

    def test_generate_skill_knowledge_with_additional(self, skill_creator):
        desc = "My skill"
        additional = "Extra instructions"
        knowledge = skill_creator.generate_skill_knowledge(desc, None, additional)
        assert "## Additional Guidelines" in knowledge
        assert additional in knowledge

class TestSkillCreatorCreate:
    @pytest.mark.asyncio
    async def test_create_skill_success(self, skill_creator, mock_custom_skills_service):
        request = SkillCreationRequest(
            user_id="user-123",
            skill_name="new_skill",
            skill_description="Description of new skill",
            category="finance"
        )
        
        result = await skill_creator.create_skill(request)
        
        assert result.success is True
        assert result.skill_id == "skill-123"
        mock_custom_skills_service.create_custom_skill.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_create_skill_already_exists(self, skill_creator, mock_custom_skills_service):
        # Mock that skill exists
        mock_custom_skills_service.get_custom_skill_by_name.return_value = {"id": "existing"}
        
        request = SkillCreationRequest(
            user_id="user-123",
            skill_name="existing_skill",
            skill_description="Description",
            category="finance"
        )
        
        result = await skill_creator.create_skill(request)
        
        assert result.success is False
        assert "already exists" in result.error_message

    @pytest.mark.asyncio
    async def test_create_skill_validation_failure(self, skill_creator):
        request = SkillCreationRequest(
            user_id="user-123",
            skill_name="a", # Too short
            skill_description="Description",
            category="finance"
        )
        
        result = await skill_creator.create_skill(request)
        
        assert result.success is False
        assert len(result.validation_errors) > 0
