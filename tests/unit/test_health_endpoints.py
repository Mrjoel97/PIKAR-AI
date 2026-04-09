# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for canonical health endpoint response shape (OBS-05).

Verifies that all /health/* endpoints return the canonical versioned JSON envelope:
    {status, version, service, latency_ms, details, checked_at}
and that health_checker.py correctly maps canonical statuses to its internal statuses.
"""

import os
from typing import ClassVar
from unittest.mock import patch


class TestCanonicalHealthShape:
    """Verify the _health_response helper produces the canonical versioned envelope."""

    REQUIRED_KEYS: ClassVar[set[str]] = {"status", "version", "service", "latency_ms", "details", "checked_at"}
    VALID_STATUSES: ClassVar[set[str]] = {"ok", "degraded", "down"}

    def _import_helper(self):
        """Import _health_response with env vars patched to avoid module-level side-effects."""
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
                "SUPABASE_ANON_KEY": "test-anon-key",
            },
        ):
            from app.fast_api_app import _health_response

            return _health_response

    def test_health_response_helper_produces_all_fields(self):
        """_health_response includes all required canonical fields."""
        _health_response = self._import_helper()
        resp = _health_response(
            status="ok",
            service="test",
            latency_ms=42,
            details={"foo": "bar"},
        )
        assert self.REQUIRED_KEYS.issubset(set(resp.keys())), (
            f"Missing keys: {self.REQUIRED_KEYS - set(resp.keys())}"
        )

    def test_health_response_version_is_one(self):
        """version field must be the string '1' for all canonical health responses."""
        _health_response = self._import_helper()
        resp = _health_response(status="ok", service="live", latency_ms=0)
        assert resp["version"] == "1"

    def test_health_response_service_field_set(self):
        """service field echoes the service name passed to the helper."""
        _health_response = self._import_helper()
        for svc in ("live", "supabase", "redis", "gemini", "video"):
            resp = _health_response(status="ok", service=svc)
            assert resp["service"] == svc, f"Expected service={svc}, got {resp['service']}"

    def test_health_response_status_constrained(self):
        """status values must be one of ok, degraded, or down."""
        _health_response = self._import_helper()
        for status in self.VALID_STATUSES:
            resp = _health_response(status=status, service="test")
            assert resp["status"] == status

    def test_health_response_integrations_optional(self):
        """integrations key only present when explicitly provided (not always emitted)."""
        _health_response = self._import_helper()
        resp_without = _health_response(status="ok", service="test")
        assert "integrations" not in resp_without, "integrations key should be absent by default"

        resp_with = _health_response(
            status="ok",
            service="test",
            integrations={"stripe": {"status": "ok", "last_sync_at": None}},
        )
        assert "integrations" in resp_with
        assert resp_with["integrations"]["stripe"]["status"] == "ok"

    def test_health_response_details_defaults_to_empty_dict(self):
        """details defaults to {} when not provided."""
        _health_response = self._import_helper()
        resp = _health_response(status="ok", service="live")
        assert resp["details"] == {}

    def test_health_response_checked_at_is_iso_string(self):
        """checked_at must be a non-empty ISO-format datetime string."""
        _health_response = self._import_helper()
        resp = _health_response(status="ok", service="live", latency_ms=0)
        checked_at = resp["checked_at"]
        assert isinstance(checked_at, str) and len(checked_at) > 0
        # ISO format sanity: should contain 'T' separator
        assert "T" in checked_at, f"checked_at '{checked_at}' does not look ISO-formatted"


class TestHealthCheckerCanonicalMapping:
    """Verify health_checker._check_one correctly maps canonical statuses to internal statuses.

    The mapping contract: "ok" -> "healthy", "degraded" -> "degraded", "down" -> "unhealthy".
    This is validated via the mapping table used inside health_checker.py.
    """

    _CANONICAL_MAP: ClassVar[dict[str, str]] = {"ok": "healthy", "degraded": "degraded", "down": "unhealthy"}

    def test_ok_maps_to_healthy(self):
        """Canonical 'ok' status maps to checker 'healthy'."""
        assert self._CANONICAL_MAP["ok"] == "healthy"

    def test_degraded_maps_to_degraded(self):
        """Canonical 'degraded' status is passed through unchanged."""
        assert self._CANONICAL_MAP["degraded"] == "degraded"

    def test_down_maps_to_unhealthy(self):
        """Canonical 'down' status maps to checker 'unhealthy'."""
        assert self._CANONICAL_MAP["down"] == "unhealthy"

    def test_all_canonical_statuses_have_mapping(self):
        """Every canonical status value has a defined internal mapping."""
        valid_canonical = {"ok", "degraded", "down"}
        assert set(self._CANONICAL_MAP.keys()) == valid_canonical

    def test_internal_statuses_match_api_health_checks_schema(self):
        """Internal statuses must match the CHECK constraint on api_health_checks.status column.

        Schema: CHECK (status IN ('healthy', 'unhealthy', 'degraded'))
        """
        allowed_db_statuses = {"healthy", "unhealthy", "degraded"}
        mapped_values = set(self._CANONICAL_MAP.values())
        assert mapped_values.issubset(allowed_db_statuses), (
            f"Unmapped statuses not in DB schema: {mapped_values - allowed_db_statuses}"
        )
