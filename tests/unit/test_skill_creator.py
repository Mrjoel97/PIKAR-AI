import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.skills.skill_creator import (
    SkillCreator,
    SkillCreationRequest,
    SkillCreationResult,
    SkillSuggestion,
    AgentID,
)
from app.skills.custom_skills_service import CustomSkillsService
from app.skills.registry import Skill, AgentID


# ---------------------------------------------------------------------------
# Helpers for semantic-similarity tests
# ---------------------------------------------------------------------------

def _make_skill(name: str, description: str, category: str = "finance") -> Skill:
    """Create a minimal Skill for test purposes."""
    return Skill(
        name=name,
        description=description,
        category=category,
        agent_ids=[AgentID.FIN],
    )

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


# =========================================================================
# Semantic similarity tests  (FIX-03)
# =========================================================================


class TestFindSimilarSkillsSemantic:
    """Tests for the embedding-backed similarity path in find_similar_skills."""

    @patch("app.skills.skill_creator.skills_registry")
    @patch("app.skills.skill_creator.skill_embeddings")
    def test_find_similar_skills_semantic_path_when_warmed(
        self, mock_embeddings, mock_registry, skill_creator,
    ):
        """When embeddings are warmed, search_similar is used (not keyword overlap)."""
        mock_embeddings.is_warmed.return_value = True
        mock_embeddings.search_similar.return_value = [
            ("financial_projection", 0.92),
            ("budget_planning", 0.85),
        ]

        fin_proj = _make_skill("financial_projection", "Financial projection and planning")
        budget = _make_skill("budget_planning", "Budget planning and allocation")
        mock_registry.get.side_effect = lambda name: {
            "financial_projection": fin_proj,
            "budget_planning": budget,
        }.get(name)

        results = skill_creator.find_similar_skills("revenue forecasting", "finance", limit=5)

        mock_embeddings.search_similar.assert_called_once()
        assert len(results) == 2
        # financial_projection should be first (higher cosine + category boost)
        assert results[0].name == "financial_projection"
        assert results[1].name == "budget_planning"

    @patch("app.skills.skill_creator.skills_registry")
    @patch("app.skills.skill_creator.skill_embeddings")
    def test_find_similar_skills_keyword_fallback_when_cold(
        self, mock_embeddings, mock_registry, skill_creator,
    ):
        """When embeddings are NOT warmed, falls back to keyword overlap."""
        mock_embeddings.is_warmed.return_value = False

        # Set up registry with skills that have keyword overlap
        skill_a = _make_skill("budget_analysis", "Analyze budget and financial cost data")
        mock_registry.list_all.return_value = [skill_a]

        results = skill_creator.find_similar_skills("budget analysis tool", "finance", limit=5)

        # search_similar should NOT be called
        mock_embeddings.search_similar.assert_not_called()
        # keyword overlap should still find the skill
        assert len(results) >= 1
        assert results[0].name == "budget_analysis"

    @patch("app.skills.skill_creator.skills_registry")
    @patch("app.skills.skill_creator.skill_embeddings")
    def test_synonym_query_finds_semantically_related_skill(
        self, mock_embeddings, mock_registry, skill_creator,
    ):
        """Synonym query ('revenue forecasting') matches 'financial projection' via embeddings.

        Keyword overlap alone would miss this because no keywords match.
        """
        mock_embeddings.is_warmed.return_value = True
        mock_embeddings.search_similar.return_value = [
            ("financial_projection", 0.88),
        ]

        fin_proj = _make_skill("financial_projection", "financial projection and planning")
        mock_registry.get.side_effect = lambda name: {
            "financial_projection": fin_proj,
        }.get(name)

        results = skill_creator.find_similar_skills(
            "revenue forecasting", "finance", limit=5,
        )

        assert len(results) == 1
        assert results[0].name == "financial_projection"

    @patch("app.skills.skill_creator.skills_registry")
    @patch("app.skills.skill_creator.skill_embeddings")
    def test_category_boost_in_semantic_mode(
        self, mock_embeddings, mock_registry, skill_creator,
    ):
        """Same-category skills get a +0.15 boost to their cosine score."""
        mock_embeddings.is_warmed.return_value = True
        # marketing_skill has higher cosine but wrong category
        # finance_skill has lower cosine but right category -- boost flips order
        mock_embeddings.search_similar.return_value = [
            ("marketing_skill", 0.80),
            ("finance_skill", 0.70),
        ]

        mkt_skill = _make_skill("marketing_skill", "Marketing analytics", category="marketing")
        fin_skill = _make_skill("finance_skill", "Finance analytics", category="finance")
        mock_registry.get.side_effect = lambda name: {
            "marketing_skill": mkt_skill,
            "finance_skill": fin_skill,
        }.get(name)

        results = skill_creator.find_similar_skills(
            "analyze data", "finance", limit=5,
        )

        # finance_skill: 0.70 + 0.15 = 0.85
        # marketing_skill: 0.80 + 0.00 = 0.80
        assert results[0].name == "finance_skill"
        assert results[1].name == "marketing_skill"

    @patch("app.skills.skill_creator.skills_registry")
    @patch("app.skills.skill_creator.skill_embeddings")
    def test_search_similar_returns_empty(
        self, mock_embeddings, mock_registry, skill_creator,
    ):
        """When search_similar returns empty list, find_similar_skills returns []."""
        mock_embeddings.is_warmed.return_value = True
        mock_embeddings.search_similar.return_value = []

        results = skill_creator.find_similar_skills(
            "something totally unique", "finance", limit=5,
        )

        assert results == []
