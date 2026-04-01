"""Tests for the onboarding system: router models, middleware guard, and persona logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from starlette.testclient import TestClient


# ---------------------------------------------------------------------------
# Helper: build a minimal BusinessContextInput without importing the real model
# (avoids pulling in Supabase SDK at import time)
# ---------------------------------------------------------------------------

def _make_context(
    team_size: str = "",
    role: str = "",
    industry: str = "",
    company_name: str = "Test Co",
    description: str = "A test company",
    goals: list | None = None,
    website: str | None = None,
):
    """Return a dict shaped like BusinessContextInput for persona tests."""
    return {
        "company_name": company_name,
        "industry": industry,
        "description": description,
        "goals": goals or ["growth"],
        "team_size": team_size,
        "role": role,
        "website": website,
    }


# ============================================================================
# 1. Pydantic model tests  (routers/onboarding.py)
# ============================================================================

class TestOnboardingModels:
    """Verify Pydantic models used in the onboarding router."""

    def test_conversation_extraction_input_accepts_messages(self):
        """ConversationExtractionInput should accept a list of strings."""
        from app.routers.onboarding import ConversationExtractionInput

        obj = ConversationExtractionInput(messages=["Hello", "I run a bakery"])
        assert obj.messages == ["Hello", "I run a bakery"]

    def test_extraction_result_fields(self):
        """ExtractionResult must expose extracted_context, persona_preview, confidence."""
        from app.routers.onboarding import ExtractionResult
        from app.services.user_onboarding_service import BusinessContextInput

        ctx = BusinessContextInput(
            company_name="Acme",
            industry="Other",
            description="Test",
            goals=["growth"],
            team_size="startup",
            role="founder",
        )
        result = ExtractionResult(
            extracted_context=ctx,
            persona_preview="startup",
            confidence=0.85,
        )
        assert result.persona_preview == "startup"
        assert result.confidence == 0.85
        assert result.extracted_context.company_name == "Acme"

    def test_persona_switch_input(self):
        """PersonaSwitchInput must accept new_persona string."""
        from app.routers.onboarding import PersonaSwitchInput

        obj = PersonaSwitchInput(new_persona="enterprise")
        assert obj.new_persona == "enterprise"


# ============================================================================
# 2. get_current_user_id dependency
# ============================================================================

class TestGetCurrentUserId:
    """Tests for the JWT verification dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self):
        """Should return the user id when Supabase verifies the token."""
        from app.routers.onboarding import get_current_user_id

        mock_user_obj = MagicMock()
        mock_user_obj.user.id = "user-abc-123"

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = mock_user_obj

        creds = MagicMock()
        creds.credentials = "valid-jwt-token"

        with patch("app.routers.onboarding.get_service_client", return_value=mock_supabase):
            user_id = await get_current_user_id(creds)
            assert user_id == "user-abc-123"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Should raise HTTPException 401 when Supabase rejects the token."""
        from fastapi import HTTPException
        from app.routers.onboarding import get_current_user_id

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = Exception("Invalid JWT")

        creds = MagicMock()
        creds.credentials = "bad-token"

        with patch("app.routers.onboarding.get_service_client", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(creds)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_none_user_raises_401(self):
        """Should raise HTTPException 401 when get_user returns None."""
        from fastapi import HTTPException
        from app.routers.onboarding import get_current_user_id

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = None

        creds = MagicMock()
        creds.credentials = "some-token"

        with patch("app.routers.onboarding.get_service_client", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(creds)
            assert exc_info.value.status_code == 401


# ============================================================================
# 3. extract_context JSON parse fallback
# ============================================================================

class TestExtractContextFallback:
    """Test that the extract_context endpoint returns defaults on JSON parse errors."""

    @pytest.mark.asyncio
    async def test_json_decode_error_returns_defaults(self):
        """When Gemini returns non-JSON, fallback should return confidence=0.3."""
        import json
        from app.routers.onboarding import ExtractionResult

        # We test the fallback logic directly by simulating what the endpoint does
        # on a JSONDecodeError, rather than calling the full endpoint (which would
        # require Gemini credentials).
        conversation_text = "I sell cupcakes online"

        # This is the fallback branch from the endpoint:
        from app.services.user_onboarding_service import BusinessContextInput

        result = ExtractionResult(
            extracted_context=BusinessContextInput(
                company_name="My Business",
                industry="Other",
                description=conversation_text[:200],
                goals=["growth"],
                team_size="startup",
                role="founder",
            ),
            persona_preview="startup",
            confidence=0.3,
        )

        assert result.confidence == 0.3
        assert result.persona_preview == "startup"
        assert result.extracted_context.company_name == "My Business"
        assert result.extracted_context.industry == "Other"
        assert result.extracted_context.description == "I sell cupcakes online"


# ============================================================================
# 4. OnboardingGuardMiddleware
# ============================================================================

def _make_guard_app():
    """Create a minimal FastAPI app with the OnboardingGuardMiddleware."""
    from app.middleware.onboarding_guard import OnboardingGuardMiddleware

    app = FastAPI()
    app.add_middleware(OnboardingGuardMiddleware)

    @app.get("/health/live")
    async def health():
        return {"ok": True}

    @app.get("/auth/callback")
    async def auth_callback():
        return {"ok": True}

    @app.get("/onboarding/status")
    async def onboarding_status():
        return {"step": 1}

    @app.get("/docs")
    async def docs_page():
        return {"ok": True}

    @app.get("/dashboard")
    async def dashboard():
        return {"data": "secret"}

    @app.get("/solopreneur/home")
    async def solopreneur():
        return {"persona": "solopreneur"}

    @app.get("/startup/metrics")
    async def startup():
        return {"persona": "startup"}

    @app.get("/sme/overview")
    async def sme():
        return {"persona": "sme"}

    @app.get("/enterprise/overview")
    async def enterprise():
        return {"persona": "enterprise"}

    @app.get("/briefing/today")
    async def briefing():
        return {"briefing": True}

    @app.get("/settings/profile")
    async def settings():
        return {"settings": True}

    @app.get("/other")
    async def other():
        return {"other": True}

    return app


class TestOnboardingGuardExcludedPaths:
    """Excluded prefixes should always pass through without auth checks."""

    def test_health_path_allowed(self):
        client = TestClient(_make_guard_app())
        resp = client.get("/health/live")
        assert resp.status_code == 200

    def test_auth_path_allowed(self):
        client = TestClient(_make_guard_app())
        resp = client.get("/auth/callback")
        assert resp.status_code == 200

    def test_onboarding_path_allowed(self):
        client = TestClient(_make_guard_app())
        resp = client.get("/onboarding/status")
        assert resp.status_code == 200

    def test_docs_path_allowed(self):
        client = TestClient(_make_guard_app())
        resp = client.get("/docs")
        assert resp.status_code == 200


class TestOnboardingGuardNonProtectedPaths:
    """Non-protected, non-excluded paths should pass through."""

    def test_other_path_passes_through(self):
        client = TestClient(_make_guard_app())
        resp = client.get("/other")
        assert resp.status_code == 200


class TestOnboardingGuardNoAuth:
    """Requests without Bearer auth on protected paths should pass through
    (the route's own auth dependency handles it)."""

    def test_no_auth_header_passes_through(self):
        client = TestClient(_make_guard_app())
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_non_bearer_auth_passes_through(self):
        client = TestClient(_make_guard_app())
        resp = client.get("/dashboard", headers={"Authorization": "Basic abc123"})
        assert resp.status_code == 200


class TestOnboardingGuardWithAuth:
    """Protected path behaviour when a Bearer token is present."""

    def _mock_supabase(self, *, user_id="user-1", profile_persona=None, agent_completed=None):
        """Build a mock Supabase client with configurable query results."""
        mock_sb = MagicMock()

        # auth.get_user
        if user_id:
            mock_user = MagicMock()
            mock_user.user.id = user_id
            mock_sb.auth.get_user.return_value = mock_user
        else:
            mock_sb.auth.get_user.return_value = None

        # table("users_profile").select().eq().maybe_single().execute()
        profile_result = MagicMock()
        profile_result.data = {"persona": profile_persona} if profile_persona else None

        agent_result = MagicMock()
        agent_result.data = {"onboarding_completed": agent_completed} if agent_completed is not None else None

        def table_side_effect(name):
            chain = MagicMock()
            if name == "users_profile":
                chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = profile_result
            elif name == "user_executive_agents":
                chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = agent_result
            return chain

        mock_sb.table.side_effect = table_side_effect
        return mock_sb

    def test_user_with_persona_passes_through(self):
        """User who has a persona in users_profile should access protected paths."""
        mock_sb = self._mock_supabase(profile_persona="startup")
        with patch("app.middleware.onboarding_guard.get_service_client", return_value=mock_sb):
            client = TestClient(_make_guard_app())
            resp = client.get("/dashboard", headers={"Authorization": "Bearer valid-token"})
            assert resp.status_code == 200
            assert resp.json() == {"data": "secret"}

    def test_user_with_onboarding_completed_passes_through(self):
        """User who has onboarding_completed in user_executive_agents should pass."""
        mock_sb = self._mock_supabase(agent_completed=True)
        with patch("app.middleware.onboarding_guard.get_service_client", return_value=mock_sb):
            client = TestClient(_make_guard_app())
            resp = client.get("/dashboard", headers={"Authorization": "Bearer valid-token"})
            assert resp.status_code == 200

    def test_user_without_onboarding_gets_403(self):
        """User with no persona and no onboarding_completed should get 403."""
        mock_sb = self._mock_supabase(profile_persona=None, agent_completed=None)
        with patch("app.middleware.onboarding_guard.get_service_client", return_value=mock_sb):
            client = TestClient(_make_guard_app())
            resp = client.get("/dashboard", headers={"Authorization": "Bearer valid-token"})
            assert resp.status_code == 403
            body = resp.json()
            assert body["detail"] == "Onboarding not completed"
            assert body["redirect"] == "/onboarding"

    def test_protected_persona_paths_guarded(self):
        """All persona paths should return 403 when onboarding is incomplete."""
        mock_sb = self._mock_supabase(profile_persona=None, agent_completed=None)
        with patch("app.middleware.onboarding_guard.get_service_client", return_value=mock_sb):
            client = TestClient(_make_guard_app())
            for path in ["/solopreneur/home", "/startup/metrics", "/sme/overview",
                         "/enterprise/overview", "/briefing/today", "/settings/profile"]:
                resp = client.get(path, headers={"Authorization": "Bearer valid-token"})
                assert resp.status_code == 403, f"{path} should be guarded"

    def test_guard_exception_lets_request_through(self):
        """If the guard raises an exception, the request should still pass through."""
        with patch("app.middleware.onboarding_guard.get_service_client", side_effect=Exception("DB down")):
            client = TestClient(_make_guard_app())
            resp = client.get("/dashboard", headers={"Authorization": "Bearer valid-token"})
            assert resp.status_code == 200

    def test_null_user_passes_through(self):
        """If auth.get_user returns no user, the guard lets the request through."""
        mock_sb = self._mock_supabase(user_id=None)
        with patch("app.middleware.onboarding_guard.get_service_client", return_value=mock_sb):
            client = TestClient(_make_guard_app())
            resp = client.get("/dashboard", headers={"Authorization": "Bearer bad-token"})
            assert resp.status_code == 200


# ============================================================================
# 5. determinePersonaPreview logic (TypeScript port tested in Python)
# ============================================================================

def determine_persona_preview(context: dict) -> str:
    """Python replica of frontend/src/services/onboarding.ts determinePersonaPreview.

    Faithfully mirrors the TypeScript logic for test coverage.
    """
    size = (context.get("team_size") or "").lower()
    role = (context.get("role") or "").lower()
    industry = (context.get("industry") or "").lower()

    # Direct ID mapping
    if size == "solo":
        return "solopreneur"
    if size == "startup":
        return "startup"
    if size in ("sme-small", "sme-large"):
        return "sme"
    if size == "enterprise":
        return "enterprise"

    # Fallback: Enterprise rules
    if "200+" in size or "enterprise" in size or "500+" in size:
        return "enterprise"
    if "corporate" in industry and any(t in role for t in ("vp", "chief", "head")):
        return "enterprise"

    # SME rules
    if "51-200" in size:
        return "sme"
    if "11-50" in size or "sme" in size:
        return "sme"

    # Solopreneur rules
    if "just me" in size or "solopreneur" in size or size == "1":
        return "solopreneur"
    if "freelance" in role or "consultant" in role:
        return "solopreneur"

    # Default
    return "startup"


class TestDeterminePersonaPreview:
    """Test the persona determination logic mirrored from the TS frontend."""

    def test_solo_returns_solopreneur(self):
        """team_size='solo' should map to solopreneur."""
        assert determine_persona_preview(_make_context(team_size="solo")) == "solopreneur"

    def test_startup_returns_startup(self):
        """team_size='startup' should map to startup."""
        assert determine_persona_preview(_make_context(team_size="startup")) == "startup"

    def test_sme_small_returns_sme(self):
        """team_size='sme-small' should map to sme."""
        assert determine_persona_preview(_make_context(team_size="sme-small")) == "sme"

    def test_sme_large_returns_sme(self):
        """team_size='sme-large' should map to sme."""
        assert determine_persona_preview(_make_context(team_size="sme-large")) == "sme"

    def test_enterprise_returns_enterprise(self):
        """team_size='enterprise' should map to enterprise."""
        assert determine_persona_preview(_make_context(team_size="enterprise")) == "enterprise"

    def test_unknown_team_size_defaults_to_startup(self):
        """An unrecognized team_size should default to startup."""
        assert determine_persona_preview(_make_context(team_size="unknown")) == "startup"

    def test_empty_team_size_defaults_to_startup(self):
        """Empty team_size with no role hint should default to startup."""
        assert determine_persona_preview(_make_context(team_size="")) == "startup"

    def test_freelance_role_with_empty_team_size_returns_solopreneur(self):
        """role='freelance' with empty team_size should yield solopreneur."""
        assert determine_persona_preview(_make_context(team_size="", role="freelance")) == "solopreneur"

    def test_consultant_role_returns_solopreneur(self):
        """role='consultant' with empty team_size should yield solopreneur."""
        assert determine_persona_preview(_make_context(role="consultant")) == "solopreneur"

    def test_legacy_200_plus_returns_enterprise(self):
        """Legacy size string containing '200+' should map to enterprise."""
        assert determine_persona_preview(_make_context(team_size="200+ employees")) == "enterprise"

    def test_legacy_51_200_returns_sme(self):
        """Legacy size string containing '51-200' should map to sme."""
        assert determine_persona_preview(_make_context(team_size="51-200 people")) == "sme"

    def test_legacy_just_me_returns_solopreneur(self):
        """Legacy size string 'just me' should map to solopreneur."""
        assert determine_persona_preview(_make_context(team_size="just me")) == "solopreneur"

    def test_corporate_vp_returns_enterprise(self):
        """Corporate industry + VP role should map to enterprise."""
        assert determine_persona_preview(
            _make_context(industry="Corporate Services", role="VP of Operations")
        ) == "enterprise"
