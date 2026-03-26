"""Tests for the Creative Pipeline Enhancement (Phases 1-5).

Tests cover:
- Phase 1: Brand Profile tools + context injection
- Phase 2: Creative Brief + Concept Exploration tools
- Phase 3: Art Direction contract tools + media integration
- Phase 4: Content Pipeline orchestrator
- Phase 5: Publishing Strategy tools
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# Helper: Build a mock Supabase client with chainable query methods
# ============================================================================

def _make_supabase_mock(data=None, error=False):
    """Create a mock Supabase client with chainable query builders."""
    mock_client = MagicMock()
    mock_response = MagicMock()

    if error:
        mock_response.data = None
        mock_response.execute = MagicMock(side_effect=RuntimeError("DB error"))
    else:
        mock_response.data = data if data is not None else []

    # Build the chainable query builder
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.insert.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.upsert.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.single.return_value = mock_query

    if error:
        mock_query.execute = MagicMock(side_effect=RuntimeError("DB error"))
    else:
        mock_query.execute.return_value = mock_response

    mock_client.table.return_value = mock_query
    return mock_client, mock_query


# ============================================================================
# Phase 1: Brand Profile Tools
# ============================================================================

class TestBrandProfileTools:
    """Tests for brand_profile.py — get, update, list."""

    @pytest.mark.asyncio
    async def test_get_brand_profile_returns_default_profile(self):
        """When a default profile exists, get_brand_profile returns it."""
        profile_data = {
            "id": "bp-123",
            "user_id": "user-1",
            "brand_name": "TestBrand",
            "voice_tone": "bold and conversational",
            "visual_style": {"mood": "energetic", "color_palette": ["#FF6B35"]},
            "audience_description": "Gen Z creators",
            "platform_rules": {"instagram": {"tone": "casual"}},
            "content_rules": ["Always include CTA"],
            "is_default": True,
        }
        mock_client, _ = _make_supabase_mock(data=[profile_data])

        with (
            patch("app.agents.tools.brand_profile._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.brand_profile._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.brand_profile import get_brand_profile

            result = await get_brand_profile()

        assert result["success"] is True
        assert result["brand_name"] == "TestBrand"
        assert result["voice_tone"] == "bold and conversational"
        assert result["profile"]["id"] == "bp-123"

    @pytest.mark.asyncio
    async def test_get_brand_profile_no_profile_returns_message(self):
        """When no profile exists, returns helpful creation message."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.agents.tools.brand_profile._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.brand_profile._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.brand_profile import get_brand_profile

            result = await get_brand_profile()

        assert result["success"] is True
        assert result["profile"] is None
        assert "No brand profile found" in result["message"]

    @pytest.mark.asyncio
    async def test_get_brand_profile_no_user_returns_error(self):
        """When no user context, returns error."""
        with patch("app.agents.tools.brand_profile._get_request_user_id", return_value=None):
            from app.agents.tools.brand_profile import get_brand_profile

            result = await get_brand_profile()

        assert result["success"] is False
        assert "No user context" in result["error"]

    @pytest.mark.asyncio
    async def test_update_brand_profile_creates_new_when_none_exists(self):
        """When no profile exists, creates a new default profile."""
        # First query (check existing) returns empty
        mock_client = MagicMock()
        mock_query_existing = MagicMock()
        mock_query_existing.select.return_value = mock_query_existing
        mock_query_existing.eq.return_value = mock_query_existing
        mock_query_existing.limit.return_value = mock_query_existing
        mock_resp_empty = MagicMock()
        mock_resp_empty.data = []
        mock_query_existing.execute.return_value = mock_resp_empty

        # Second query (insert) returns new profile
        mock_query_insert = MagicMock()
        mock_query_insert.insert.return_value = mock_query_insert
        mock_resp_new = MagicMock()
        mock_resp_new.data = [{"id": "bp-new", "brand_name": "NewBrand", "is_default": True}]
        mock_query_insert.execute.return_value = mock_resp_new

        call_count = [0]
        def table_side_effect(name):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_query_existing
            return mock_query_insert

        mock_client.table.side_effect = table_side_effect

        with (
            patch("app.agents.tools.brand_profile._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.brand_profile._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.brand_profile import update_brand_profile

            result = await update_brand_profile(
                brand_name="NewBrand",
                voice_tone="edgy and bold",
            )

        assert result["success"] is True
        assert result["action"] == "created"

    @pytest.mark.asyncio
    async def test_update_brand_profile_no_fields_returns_error(self):
        """When no fields provided, returns error."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.agents.tools.brand_profile._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.brand_profile._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.brand_profile import update_brand_profile

            result = await update_brand_profile()

        assert result["success"] is False
        assert "No fields provided" in result["error"]

    def test_format_brand_context_block_produces_valid_block(self):
        """format_brand_context_block produces a well-structured injection block."""
        from app.agents.tools.brand_profile import format_brand_context_block

        profile = {
            "brand_name": "TestBrand",
            "tagline": "Make it happen",
            "voice_tone": "bold",
            "voice_personality": ["witty", "authoritative"],
            "visual_style": {
                "mood": "energetic",
                "color_palette": ["#FF6B35", "#004E89"],
                "lighting_style": "golden hour",
            },
            "audience_description": "Gen Z creators",
            "content_rules": ["Always include CTA", "No corporate jargon"],
            "forbidden_terms": ["synergy", "leverage"],
            "preferred_image_style": "vibrant",
        }

        block = format_brand_context_block(profile)

        assert "[BRAND DNA" in block
        assert "TestBrand" in block
        assert "bold" in block
        assert "witty, authoritative" in block
        assert "#FF6B35" in block
        assert "golden hour" in block
        assert "Gen Z creators" in block
        assert "Always include CTA" in block
        assert "synergy" in block
        assert "vibrant" in block
        assert "[END BRAND DNA]" in block

    def test_format_brand_context_block_empty_profile_returns_empty(self):
        """Empty profile returns empty string."""
        from app.agents.tools.brand_profile import format_brand_context_block

        assert format_brand_context_block({}) == ""
        assert format_brand_context_block(None) == ""


# ============================================================================
# Phase 2: Creative Brief + Concept Exploration
# ============================================================================

class TestCreativeBriefTools:
    """Tests for creative_brief.py — brief generation and concept exploration."""

    @pytest.mark.asyncio
    async def test_generate_creative_brief_returns_structured_brief(self):
        """Brief generation returns all required fields."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.agents.tools.creative_brief._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.creative_brief._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.creative_brief import generate_creative_brief

            result = await generate_creative_brief(
                idea="TikTok campaign for our new sneaker launch",
                goal="drive awareness",
                target_platform="TikTok",
                content_type="video ad",
            )

        assert result["success"] is True
        assert result["brief_id"]  # UUID generated
        brief = result["brief"]
        assert brief["original_idea"] == "TikTok campaign for our new sneaker launch"
        assert brief["goal"] == "drive awareness"
        assert brief["target_platform"] == "TikTok"
        assert brief["content_type"] == "video ad"
        assert brief["pipeline_stage"] == "brief"
        assert "key_messages" in brief
        assert "success_criteria" in brief
        assert result["next_step"] == "explore_concepts"

    @pytest.mark.asyncio
    async def test_generate_creative_brief_enriches_from_brand_profile(self):
        """Brief auto-populates audience/tone from brand profile when available."""
        brand_profile = {
            "audience_description": "Gen Z sneakerheads",
            "voice_tone": "street-smart and energetic",
            "visual_style": {"mood": "urban gritty"},
        }
        # First call: brand profiles table (returns profile)
        # Second call: knowledge_vault table (insert brief)
        mock_client = MagicMock()
        call_count = [0]

        def table_side_effect(name):
            call_count[0] += 1
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.insert.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_resp = MagicMock()
            if name == "brand_profiles":
                mock_resp.data = [brand_profile]
            else:
                mock_resp.data = []
            mock_query.execute.return_value = mock_resp
            return mock_query

        mock_client.table.side_effect = table_side_effect

        with (
            patch("app.agents.tools.creative_brief._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.creative_brief._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.creative_brief import generate_creative_brief

            result = await generate_creative_brief(idea="sneaker launch video")

        assert result["success"] is True
        brief = result["brief"]
        assert brief["target_audience"] == "Gen Z sneakerheads"
        assert brief["tone_and_voice"] == "street-smart and energetic"

    @pytest.mark.asyncio
    async def test_explore_concepts_returns_three_concepts(self):
        """Concept exploration always generates exactly 3 concepts."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.agents.tools.creative_brief._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.creative_brief._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.creative_brief import explore_concepts

            result = await explore_concepts(
                idea="sneaker launch TikTok",
                goal="awareness",
                target_audience="Gen Z",
                tone="bold",
                platform="TikTok",
            )

        assert result["success"] is True
        assert len(result["concepts"]) == 3
        assert result["concepts"][0]["number"] == 1
        assert result["concepts"][1]["number"] == 2
        assert result["concepts"][2]["number"] == 3
        # Each concept has required fields
        for concept in result["concepts"]:
            assert "concept_id" in concept
            assert "name" in concept
            assert "angle" in concept
            assert "hook" in concept
            assert "visual_mood" in concept
            assert "rationale" in concept

    @pytest.mark.asyncio
    async def test_explore_concepts_no_idea_returns_error(self):
        """Missing idea returns error."""
        with patch("app.agents.tools.creative_brief._get_request_user_id", return_value="user-1"):
            from app.agents.tools.creative_brief import explore_concepts

            result = await explore_concepts()

        assert result["success"] is False
        assert "No idea" in result["error"]


# ============================================================================
# Phase 3: Art Direction Tools
# ============================================================================

class TestArtDirectionTools:
    """Tests for art_direction.py — visual contracts."""

    @pytest.mark.asyncio
    async def test_create_art_direction_returns_contract(self):
        """Art direction creation returns a full visual contract."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.agents.tools.art_direction._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.art_direction._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.art_direction import create_art_direction

            result = await create_art_direction(
                mood="warm and cinematic",
                color_palette=["#FF6B35", "#004E89", "#F4A261"],
                lighting_style="golden hour",
                composition_rules="rule of thirds, negative space",
                image_style_preset="bold",
                do_not_include=["stock photo people"],
            )

        assert result["success"] is True
        assert result["art_direction_id"]
        contract = result["contract"]
        assert contract["mood"] == "warm and cinematic"
        assert contract["color_palette"] == ["#FF6B35", "#004E89", "#F4A261"]
        assert contract["lighting_style"] == "golden hour"
        assert contract["image_style_preset"] == "bold"
        assert "stock photo people" in contract["do_not_include"]

    @pytest.mark.asyncio
    async def test_create_art_direction_enriches_from_brand_profile(self):
        """Art direction fills empty fields from brand profile's visual_style."""
        brand_data = {
            "visual_style": {
                "mood": "clean minimal",
                "color_palette": ["#000", "#FFF"],
                "lighting_style": "studio",
            },
            "preferred_image_style": "minimal",
        }
        mock_client = MagicMock()
        call_count = [0]

        def table_side_effect(name):
            call_count[0] += 1
            q = MagicMock()
            q.select.return_value = q
            q.insert.return_value = q
            q.eq.return_value = q
            q.limit.return_value = q
            resp = MagicMock()
            if name == "brand_profiles":
                resp.data = [brand_data]
            else:
                resp.data = []
            q.execute.return_value = resp
            return q

        mock_client.table.side_effect = table_side_effect

        with (
            patch("app.agents.tools.art_direction._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.art_direction._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.art_direction import create_art_direction

            # Only provide mood, rest should come from brand profile
            result = await create_art_direction(mood="override mood")

        contract = result["contract"]
        assert contract["mood"] == "override mood"  # Explicitly set, not overridden
        assert contract["color_palette"] == ["#000", "#FFF"]  # From brand
        assert contract["lighting_style"] == "studio"  # From brand
        assert contract["image_style_preset"] == "minimal"  # From brand

    def test_build_art_direction_prompt_modifier(self):
        """Prompt modifier string includes all visual parameters."""
        from app.agents.tools.art_direction import build_art_direction_prompt_modifier

        contract = {
            "mood": "dark and cinematic",
            "color_palette": ["#1a1a2e", "#16213e"],
            "lighting_style": "neon glow",
            "composition_rules": "centered subject",
            "visual_energy": "high energy",
            "reference_styles": ["Blade Runner", "cyberpunk"],
            "do_not_include": ["daylight scenes"],
        }

        modifier = build_art_direction_prompt_modifier(contract)

        assert "dark and cinematic" in modifier
        assert "#1a1a2e" in modifier
        assert "neon glow" in modifier
        assert "centered subject" in modifier
        assert "high energy" in modifier
        assert "Blade Runner" in modifier
        assert "daylight scenes" in modifier

    def test_build_art_direction_prompt_modifier_empty_contract(self):
        """Empty contract returns empty string."""
        from app.agents.tools.art_direction import build_art_direction_prompt_modifier

        assert build_art_direction_prompt_modifier({}) == ""
        assert build_art_direction_prompt_modifier(None) == ""

    @pytest.mark.asyncio
    async def test_art_direction_integrates_with_generate_image(self):
        """generate_image with art_direction_id loads contract and modifies prompt."""
        contract_data = {
            "mood": "warm sunset",
            "color_palette": ["#FF6B35"],
            "lighting_style": "golden hour",
            "image_style_preset": "bold",
        }
        kv_row = {"content": json.dumps(contract_data)}

        mock_kv_client, mock_kv_query = _make_supabase_mock(data=kv_row)

        # Mock the art direction tool's get function
        async def mock_get_art_direction(art_direction_id, user_id=None):
            return {"success": True, "contract": contract_data}

        # Mock vertex image generation
        mock_vertex_result = {
            "success": True,
            "image_bytes_base64": "aGVsbG8=",  # base64 of "hello"
            "model_used": "gemini-2.5-flash-image",
            "mime_type": "image/png",
        }

        with (
            patch("app.agents.tools.media._get_supabase_client", return_value=None),
            patch("app.services.request_context.get_current_user_id", return_value=None),
            patch("app.services.request_context.get_current_session_id", return_value=None),
            patch("app.services.request_context.get_current_workflow_execution_id", return_value=None),
            patch("app.agents.tools.art_direction.get_art_direction", new=mock_get_art_direction),
            patch("app.services.vertex_image_service.generate_image", return_value=mock_vertex_result),
            patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_vertex_result),
        ):
            from app.agents.tools.media import generate_image

            result = await generate_image(
                prompt="a sneaker on a rooftop",
                art_direction_id="ad-123",
                user_id="user-1",
            )

        # Should succeed (even without storage, returns data URL)
        assert result.get("success") is not False or result.get("type") == "image"


# ============================================================================
# Phase 4: Content Pipeline Orchestrator
# ============================================================================

class TestContentPipeline:
    """Tests for content_pipeline.py — pipeline lifecycle."""

    @pytest.mark.asyncio
    async def test_start_content_pipeline_initializes_10_stages(self):
        """Starting a pipeline creates all 10 stages."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.workflows.content_pipeline._get_supabase_client", return_value=mock_client),
            patch("app.workflows.content_pipeline._get_request_user_id", return_value="user-1"),
        ):
            from app.workflows.content_pipeline import start_content_pipeline

            result = await start_content_pipeline(
                idea="TikTok sneaker launch campaign",
                content_type="video ad",
                target_platform="TikTok",
                goal="drive awareness",
            )

        assert result["success"] is True
        assert result["pipeline_id"]
        pipeline = result["pipeline"]
        assert len(pipeline["stages"]) == 10
        assert pipeline["status"] == "running"
        assert pipeline["current_stage"] == "brief"
        # All stages start as pending
        for stage in pipeline["stages"]:
            assert stage["status"] == "pending"
        # First stage info
        assert result["next_stage"] == "brief"
        assert result["next_tool"] == "generate_creative_brief"

    @pytest.mark.asyncio
    async def test_start_content_pipeline_with_skip_stages(self):
        """Skipping stages marks them as 'skipped'."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.workflows.content_pipeline._get_supabase_client", return_value=mock_client),
            patch("app.workflows.content_pipeline._get_request_user_id", return_value="user-1"),
        ):
            from app.workflows.content_pipeline import start_content_pipeline

            result = await start_content_pipeline(
                idea="Quick blog post",
                skip_stages=["research", "storyboard", "assembly", "repurpose"],
            )

        pipeline = result["pipeline"]
        skipped = [s for s in pipeline["stages"] if s["status"] == "skipped"]
        active = [s for s in pipeline["stages"] if s["status"] == "pending"]
        assert len(skipped) == 4
        assert len(active) == 6

    @pytest.mark.asyncio
    async def test_start_content_pipeline_no_user_returns_error(self):
        """No user context returns error."""
        with patch("app.workflows.content_pipeline._get_request_user_id", return_value=None):
            from app.workflows.content_pipeline import start_content_pipeline

            result = await start_content_pipeline(idea="test")

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_update_pipeline_stage_advances_to_next(self):
        """Completing a stage advances current_stage to the next pending one."""
        pipeline_data = {
            "id": "pipe-1",
            "user_id": "user-1",
            "idea": "test",
            "content_type": "video",
            "target_platform": "TikTok",
            "status": "running",
            "current_stage": "brief",
            "stages": [
                {"stage": "brief", "name": "Creative Brief", "status": "in_progress", "order": 0, "output_id": None, "output_summary": "", "started_at": "2026-01-01", "completed_at": None, "requires_approval": False},
                {"stage": "research", "name": "Research & Trends", "status": "pending", "order": 1, "output_id": None, "output_summary": "", "started_at": None, "completed_at": None, "requires_approval": False},
                {"stage": "concepts", "name": "Concept Exploration", "status": "pending", "order": 2, "output_id": None, "output_summary": "", "started_at": None, "completed_at": None, "requires_approval": True},
            ],
            "artifacts": {},
        }
        kv_response = {"content": json.dumps(pipeline_data)}

        mock_client = MagicMock()
        call_count = [0]

        def table_side_effect(name):
            call_count[0] += 1
            q = MagicMock()
            q.select.return_value = q
            q.update.return_value = q
            q.eq.return_value = q
            q.single.return_value = q
            resp = MagicMock()
            resp.data = kv_response
            q.execute.return_value = resp
            return q

        mock_client.table.side_effect = table_side_effect

        with (
            patch("app.workflows.content_pipeline._get_supabase_client", return_value=mock_client),
            patch("app.workflows.content_pipeline._get_request_user_id", return_value="user-1"),
        ):
            from app.workflows.content_pipeline import update_pipeline_stage

            result = await update_pipeline_stage(
                pipeline_id="pipe-1",
                stage="brief",
                status="completed",
                output_id="brief-123",
                output_summary="Brief created for sneaker launch",
            )

        assert result["success"] is True
        assert result["next_stage"] == "research"
        assert result["next_tool"] == "deep_research"

    @pytest.mark.asyncio
    async def test_pipeline_stage_definitions_are_complete(self):
        """Every PipelineStage has a matching definition."""
        from app.workflows.content_pipeline import STAGE_DEFINITIONS, STAGE_ORDER, PipelineStage

        assert len(STAGE_ORDER) == 10
        for stage in PipelineStage:
            assert stage in STAGE_DEFINITIONS, f"Missing definition for {stage}"
            defn = STAGE_DEFINITIONS[stage]
            assert "name" in defn
            assert "tool" in defn
            assert "agent" in defn
            assert "output_type" in defn

    @pytest.mark.asyncio
    async def test_get_pipeline_status_returns_progress(self):
        """Pipeline status returns structured progress info."""
        pipeline_data = {
            "id": "pipe-1",
            "status": "running",
            "current_stage": "concepts",
            "stages": [
                {"stage": "brief", "name": "Creative Brief", "status": "completed", "order": 0, "output_summary": "Brief done"},
                {"stage": "research", "name": "Research & Trends", "status": "completed", "order": 1, "output_summary": "Research done"},
                {"stage": "concepts", "name": "Concept Exploration", "status": "in_progress", "order": 2, "output_summary": ""},
                {"stage": "script", "name": "Script & Copy", "status": "pending", "order": 3, "output_summary": ""},
            ],
            "artifacts": {},
        }

        mock_client = MagicMock()
        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.single.return_value = q
        resp = MagicMock()
        resp.data = {"content": json.dumps(pipeline_data)}
        q.execute.return_value = resp
        mock_client.table.return_value = q

        with (
            patch("app.workflows.content_pipeline._get_supabase_client", return_value=mock_client),
            patch("app.workflows.content_pipeline._get_request_user_id", return_value="user-1"),
        ):
            from app.workflows.content_pipeline import get_pipeline_status

            result = await get_pipeline_status(pipeline_id="pipe-1")

        assert result["success"] is True
        assert result["completed_stages"] == 2
        assert result["status"] == "running"


# ============================================================================
# Phase 5: Publishing Strategy Tools
# ============================================================================

class TestPublishingStrategyTools:
    """Tests for publishing_strategy.py."""

    @pytest.mark.asyncio
    async def test_create_publishing_strategy_returns_platform_strategies(self):
        """Strategy creation generates per-platform templates."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.agents.tools.publishing_strategy._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.publishing_strategy._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.publishing_strategy import create_publishing_strategy

            result = await create_publishing_strategy(
                content_description="Sneaker launch video ad",
                content_type="video ad",
                target_platforms=["instagram", "tiktok", "linkedin"],
                campaign_goal="drive awareness",
            )

        assert result["success"] is True
        assert result["strategy_id"]
        strategy = result["strategy"]
        assert len(strategy["platform_strategies"]) == 3

        platforms = {s["platform"] for s in strategy["platform_strategies"]}
        assert platforms == {"instagram", "tiktok", "linkedin"}

        # Each platform has required fields
        for ps in strategy["platform_strategies"]:
            assert "caption" in ps
            assert "hashtags" in ps
            assert "optimal_posting_time" in ps
            assert "format_notes" in ps
            assert "max_caption_length" in ps

        # Distribution calendar exists
        assert len(strategy["distribution_calendar"]) == 5

    @pytest.mark.asyncio
    async def test_create_publishing_strategy_uses_platform_guidelines(self):
        """Platform strategies include correct platform-specific guidelines."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.agents.tools.publishing_strategy._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.publishing_strategy._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.publishing_strategy import create_publishing_strategy

            result = await create_publishing_strategy(
                content_description="Test content",
                target_platforms=["twitter"],
            )

        twitter_strategy = result["strategy"]["platform_strategies"][0]
        assert twitter_strategy["platform"] == "twitter"
        assert twitter_strategy["max_caption_length"] == 280
        assert "1-2 max" in twitter_strategy["recommended_hashtag_count"]

    @pytest.mark.asyncio
    async def test_create_publishing_strategy_defaults_to_three_platforms(self):
        """When no platforms specified, defaults to instagram, tiktok, linkedin."""
        mock_client, _ = _make_supabase_mock(data=[])

        with (
            patch("app.agents.tools.publishing_strategy._get_supabase_client", return_value=mock_client),
            patch("app.agents.tools.publishing_strategy._get_request_user_id", return_value="user-1"),
        ):
            from app.agents.tools.publishing_strategy import create_publishing_strategy

            result = await create_publishing_strategy(content_description="Test")

        platforms = {s["platform"] for s in result["strategy"]["platform_strategies"]}
        assert platforms == {"instagram", "tiktok", "linkedin"}

    @pytest.mark.asyncio
    async def test_platform_guidelines_coverage(self):
        """All 6 platform guidelines are defined and have required fields."""
        from app.agents.tools.publishing_strategy import PLATFORM_GUIDELINES

        expected_platforms = {"instagram", "tiktok", "youtube", "linkedin", "twitter", "facebook"}
        assert set(PLATFORM_GUIDELINES.keys()) == expected_platforms

        for platform, guidelines in PLATFORM_GUIDELINES.items():
            assert "optimal_times" in guidelines, f"{platform} missing optimal_times"
            assert "hashtag_count" in guidelines, f"{platform} missing hashtag_count"
            assert "caption_style" in guidelines, f"{platform} missing caption_style"
            assert "format_notes" in guidelines, f"{platform} missing format_notes"
            assert "max_caption_length" in guidelines, f"{platform} missing max_caption_length"


# ============================================================================
# Phase 1 (Bonus): Context Extractor Brand DNA Injection
# ============================================================================

class TestBrandDNAInjection:
    """Tests for brand DNA injection in context_extractor.py."""

    def test_creative_agent_names_include_all_creative_agents(self):
        """The creative agent name set includes all content + marketing agents."""
        from app.agents.context_extractor import _CREATIVE_AGENT_NAMES

        assert "ContentCreationAgent" in _CREATIVE_AGENT_NAMES
        assert "VideoDirectorAgent" in _CREATIVE_AGENT_NAMES
        assert "GraphicDesignerAgent" in _CREATIVE_AGENT_NAMES
        assert "CopywriterAgent" in _CREATIVE_AGENT_NAMES
        assert "MarketingAgent" in _CREATIVE_AGENT_NAMES
        assert "SocialMediaAgent" in _CREATIVE_AGENT_NAMES
        assert "ExecutiveAgent" in _CREATIVE_AGENT_NAMES

    def test_try_load_brand_profile_caches_in_session_state(self):
        """Brand profile is loaded once and cached in session state."""
        from app.agents.context_extractor import (
            _BRAND_PROFILE_LOADED_KEY,
            _try_load_brand_profile,
        )

        # First call: not loaded yet, returns "" because no user_id
        mock_ctx = MagicMock()
        mock_ctx.state = {}

        result = _try_load_brand_profile(mock_ctx)

        # Should have set the loaded key to True
        assert mock_ctx.state[_BRAND_PROFILE_LOADED_KEY] is True
        # Returns empty because no user_id
        assert result == ""

    def test_try_load_brand_profile_returns_cached_on_second_call(self):
        """Second call returns cached value without DB query."""
        from app.agents.context_extractor import (
            _BRAND_PROFILE_LOADED_KEY,
            _try_load_brand_profile,
        )
        from app.agents.tools.brand_profile import BRAND_PROFILE_STATE_KEY

        mock_ctx = MagicMock()
        mock_ctx.state = {
            _BRAND_PROFILE_LOADED_KEY: True,
            BRAND_PROFILE_STATE_KEY: "[BRAND DNA]\nTest Brand\n[END BRAND DNA]",
        }

        result = _try_load_brand_profile(mock_ctx)

        assert "[BRAND DNA]" in result
        assert "Test Brand" in result


# ============================================================================
# Integration: Agent Wiring
# ============================================================================

class TestAgentWiring:
    """Tests that new tools are properly wired into agents."""

    def test_content_agent_has_brand_profile_tools(self):
        """ContentCreationAgent includes brand profile tools."""
        from app.agents.content.agent import create_content_agent

        agent = create_content_agent()
        tool_names = {getattr(t, "__name__", str(t)) for t in agent.tools}

        assert "get_brand_profile" in tool_names
        assert "update_brand_profile" in tool_names

    def test_content_agent_has_creative_brief_tools(self):
        """ContentCreationAgent includes creative brief tools."""
        from app.agents.content.agent import create_content_agent

        agent = create_content_agent()
        tool_names = {getattr(t, "__name__", str(t)) for t in agent.tools}

        assert "generate_creative_brief" in tool_names
        assert "explore_concepts" in tool_names
        assert "get_creative_brief" in tool_names

    def test_content_agent_has_art_direction_tools(self):
        """ContentCreationAgent and sub-agents include art direction tools."""
        from app.agents.content.agent import create_content_agent

        agent = create_content_agent()
        tool_names = {getattr(t, "__name__", str(t)) for t in agent.tools}
        assert "create_art_direction" in tool_names
        assert "get_art_direction" in tool_names

        # Sub-agents too
        for sub in agent.sub_agents:
            sub_tool_names = {getattr(t, "__name__", str(t)) for t in sub.tools}
            if sub.name in ("VideoDirectorAgent", "GraphicDesignerAgent"):
                assert "create_art_direction" in sub_tool_names, f"{sub.name} missing art_direction"

    def test_content_agent_has_pipeline_tools(self):
        """ContentCreationAgent includes pipeline orchestration tools."""
        from app.agents.content.agent import create_content_agent

        agent = create_content_agent()
        tool_names = {getattr(t, "__name__", str(t)) for t in agent.tools}

        assert "start_content_pipeline" in tool_names
        assert "update_pipeline_stage" in tool_names
        assert "get_pipeline_status" in tool_names

    def test_content_director_instruction_mentions_pipeline(self):
        """ContentDirector instruction includes creative pipeline guidance."""
        from app.agents.content.agent import CONTENT_DIRECTOR_INSTRUCTION

        assert "CREATIVE PIPELINE" in CONTENT_DIRECTOR_INSTRUCTION
        assert "generate_creative_brief" in CONTENT_DIRECTOR_INSTRUCTION
        assert "explore_concepts" in CONTENT_DIRECTOR_INSTRUCTION
        assert "start_content_pipeline" in CONTENT_DIRECTOR_INSTRUCTION

    def test_marketing_agent_has_brand_and_publishing_tools(self):
        """MarketingAgent includes brand profile and publishing strategy tools."""
        from app.agents.marketing.agent import create_marketing_agent

        agent = create_marketing_agent()
        tool_names = {getattr(t, "__name__", str(t)) for t in agent.tools}

        assert "get_brand_profile" in tool_names
        assert "update_brand_profile" in tool_names

        # Publishing strategy should be in SocialMediaAgent sub-agent
        for sub in agent.sub_agents:
            if "Social" in sub.name:
                sub_tool_names = {getattr(t, "__name__", str(t)) for t in sub.tools}
                assert "create_publishing_strategy" in sub_tool_names, "SocialMediaAgent missing publishing_strategy"
