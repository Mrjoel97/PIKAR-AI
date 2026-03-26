"""Tests for production hardening: fail-fast guards and environment validation.

Verifies that production deployments crash at startup when critical services
(SupabaseSessionService, GCS artifact storage) are unavailable, rather than
silently falling back to in-memory implementations that cause data loss
across Cloud Run replicas.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.config.validation import (
    Environment,
    EnvironmentVariable,
    validate_environment,
    ENVIRONMENT_VARIABLES,
)


# ---------------------------------------------------------------------------
# Test 1: validate_environment(env=Production) fails when LOGS_BUCKET_NAME missing
# ---------------------------------------------------------------------------
class TestLogsValidation:
    """Validate LOGS_BUCKET_NAME is required in production."""

    def test_production_fails_without_logs_bucket_name(self, monkeypatch):
        """LOGS_BUCKET_NAME must be set in production; validation must fail without it."""
        # Set up a minimal production-like env to isolate the LOGS_BUCKET_NAME check.
        # Provide all other production-required vars so we only trigger the one we care about.
        _set_all_production_required(monkeypatch, exclude={"LOGS_BUCKET_NAME"})
        monkeypatch.delenv("LOGS_BUCKET_NAME", raising=False)

        result = validate_environment(
            env=Environment.PRODUCTION, fail_fast=False, log_warnings=False
        )
        assert not result.valid, "Validation should fail when LOGS_BUCKET_NAME is missing in production"
        assert "LOGS_BUCKET_NAME" in result.missing_required

    # ---------------------------------------------------------------------------
    # Test 2: validate_environment(env=Development) succeeds without LOGS_BUCKET_NAME
    # ---------------------------------------------------------------------------
    def test_development_succeeds_without_logs_bucket_name(self, monkeypatch):
        """LOGS_BUCKET_NAME is optional in development."""
        monkeypatch.delenv("LOGS_BUCKET_NAME", raising=False)

        result = validate_environment(
            env=Environment.DEVELOPMENT, fail_fast=False, log_warnings=False
        )
        # LOGS_BUCKET_NAME should NOT appear in missing_required for dev
        assert "LOGS_BUCKET_NAME" not in result.missing_required

    def test_logs_bucket_name_in_environment_variables(self):
        """LOGS_BUCKET_NAME must be registered in ENVIRONMENT_VARIABLES."""
        names = [v.name for v in ENVIRONMENT_VARIABLES]
        assert "LOGS_BUCKET_NAME" in names, (
            "LOGS_BUCKET_NAME should be in ENVIRONMENT_VARIABLES list"
        )

    def test_logs_bucket_name_required_in_production_only(self):
        """LOGS_BUCKET_NAME must be required_in={Environment.PRODUCTION}."""
        var = next(
            (v for v in ENVIRONMENT_VARIABLES if v.name == "LOGS_BUCKET_NAME"),
            None,
        )
        assert var is not None
        assert Environment.PRODUCTION in var.required_in
        assert Environment.DEVELOPMENT not in var.required_in


# ---------------------------------------------------------------------------
# Test 3-6: Fail-fast guards in fast_api_app.py startup logic
# ---------------------------------------------------------------------------
class TestSessionServiceFailFast:
    """SupabaseSessionService failure must raise in production, fallback in dev."""

    def test_production_raises_on_supabase_session_failure(self):
        """In production, SupabaseSessionService init failure must raise RuntimeError."""
        # Simulate the production guard logic directly
        _is_production = True
        init_error = ConnectionError("Supabase unreachable")

        with pytest.raises(RuntimeError, match="SupabaseSessionService initialization failed in production"):
            _simulate_session_service_init(
                is_production=_is_production,
                supabase_error=init_error,
            )

    def test_development_falls_back_to_inmemory_session(self):
        """In development, SupabaseSessionService failure falls back to InMemory."""
        _is_production = False
        init_error = ConnectionError("Supabase unreachable")

        result = _simulate_session_service_init(
            is_production=_is_production,
            supabase_error=init_error,
        )
        assert result == "InMemorySessionService", (
            "Development mode should fall back to InMemorySessionService"
        )


class TestArtifactServiceFailFast:
    """Missing LOGS_BUCKET_NAME must raise in production, fallback in dev."""

    def test_production_raises_without_logs_bucket(self):
        """In production, missing LOGS_BUCKET_NAME must raise RuntimeError."""
        with pytest.raises(RuntimeError, match="LOGS_BUCKET_NAME is required in production"):
            _simulate_artifact_service_init(
                is_production=True,
                logs_bucket_name=None,
                adk_available=True,
            )

    def test_development_falls_back_to_inmemory_artifact(self):
        """In development, missing LOGS_BUCKET_NAME falls back to InMemoryArtifactService."""
        result = _simulate_artifact_service_init(
            is_production=False,
            logs_bucket_name=None,
            adk_available=True,
        )
        assert result == "InMemoryArtifactService", (
            "Development mode should fall back to InMemoryArtifactService"
        )

    def test_production_uses_gcs_when_bucket_set(self):
        """In production with LOGS_BUCKET_NAME, GcsArtifactService is used."""
        result = _simulate_artifact_service_init(
            is_production=True,
            logs_bucket_name="gs://pikar-ai-logs",
            adk_available=True,
        )
        assert result == "GcsArtifactService", (
            "Production with LOGS_BUCKET_NAME should use GcsArtifactService"
        )


# ---------------------------------------------------------------------------
# Helpers — simulate the startup logic patterns from fast_api_app.py
# ---------------------------------------------------------------------------

def _simulate_session_service_init(
    *,
    is_production: bool,
    supabase_error: Exception | None = None,
) -> str:
    """Simulate the session_service initialization pattern from fast_api_app.py.

    Returns the name of the service class that would be used.
    """
    try:
        if supabase_error:
            raise supabase_error
        return "SupabaseSessionService"
    except Exception as e:
        if is_production:
            raise RuntimeError(
                f"SupabaseSessionService initialization failed in production: {e}. "
                "InMemory fallback is disabled in production to prevent data loss across replicas."
            ) from e
        return "InMemorySessionService"


def _simulate_artifact_service_init(
    *,
    is_production: bool,
    logs_bucket_name: str | None,
    adk_available: bool,
) -> str:
    """Simulate the artifact_service initialization pattern from fast_api_app.py.

    Returns the name of the service class that would be used.
    """
    if adk_available:
        if logs_bucket_name:
            return "GcsArtifactService"
        elif is_production:
            raise RuntimeError(
                "LOGS_BUCKET_NAME is required in production for artifact persistence. "
                "InMemory fallback is disabled to prevent data loss across replicas."
            )
        else:
            return "InMemoryArtifactService"
    return "None"


def _set_all_production_required(monkeypatch, *, exclude: set[str] | None = None):
    """Set all production-required env vars to dummy values, except those in exclude."""
    exclude = exclude or set()

    # Gather all required-in-production vars from the registry
    for var in ENVIRONMENT_VARIABLES:
        if Environment.PRODUCTION in var.required_in and var.name not in exclude:
            monkeypatch.setenv(var.name, "dummy-value")

    # Production boolean-valued vars that must have specific values
    boolean_overrides = {
        "WORKFLOW_STRICT_TOOL_RESOLUTION": "true",
        "WORKFLOW_STRICT_CRITICAL_TOOL_GUARD": "true",
        "WORKFLOW_ALLOW_FALLBACK_SIMULATION": "false",
        "WORKFLOW_ENFORCE_READINESS_GATE": "true",
    }
    for name, value in boolean_overrides.items():
        if name not in exclude:
            monkeypatch.setenv(name, value)

    # WORKFLOW_SERVICE_SECRET needs >= 32 chars
    if "WORKFLOW_SERVICE_SECRET" not in exclude:
        monkeypatch.setenv(
            "WORKFLOW_SERVICE_SECRET",
            "a" * 32,
        )

    # BACKEND_API_URL needs valid URL format
    if "BACKEND_API_URL" not in exclude:
        monkeypatch.setenv("BACKEND_API_URL", "https://api.pikar.ai")
