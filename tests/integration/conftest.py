"""Integration-test bootstrap configuration.

This file is loaded by pytest before integration test modules are imported.
It forces local test-safe import behavior for app.fast_api_app so tests do
not depend on native A2A/grpc bindings being available in CI/dev shells.
"""

from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock


# Skip heavy optional runtime imports that are not required for API endpoint
# integration tests, and avoid startup env validation noise in test runs.
os.environ.setdefault("LOCAL_DEV_BYPASS", "1")
os.environ.setdefault("SKIP_ENV_VALIDATION", "1")
os.environ.setdefault("ENVIRONMENT", "test")

# ---------------------------------------------------------------------------
# Remove unit-test stubs from sys.modules so that integration tests import
# the real application modules.  When the unit test suite runs first in the
# same pytest session, module-level _stub() calls in unit test files insert
# lightweight fakes into sys.modules.  Those stubs are intentionally thin
# (they only export the names needed by the tested router) and will cause
# ImportError when the integration tests try to import the full fast_api_app
# module chain.  Purging them here lets Python re-import the real modules.
# ---------------------------------------------------------------------------
_UNIT_TEST_STUBS = [
    "app.app_utils.auth",
    "app.autonomy.agent_kernel",
    "app.config.feature_gating",
    "app.middleware.feature_gate",
    "app.middleware.rate_limiter",
    "app.personas.runtime",
    "app.routers.onboarding",
    "app.services.feature_flags",
    "app.services.governance_service",
    "app.services.sse_connection_limits",
    "app.services.supabase_async",
    "app.workflows.contract_defaults",
    "app.workflows.engine",
    "app.workflows.user_workflow_service",
]

for _mod in _UNIT_TEST_STUBS:
    sys.modules.pop(_mod, None)

# ---------------------------------------------------------------------------
# Ensure app.services.supabase_client is in sys.modules with a minimal
# working stub.  This module is needed at import-time by several routers
# (e.g. departments, account) and by services like DepartmentRunner that
# instantiate a client in their module-level singleton.  Without a pre-seeded
# stub the combined unit+integration run fails with ValueError("SUPABASE_URL
# and SUPABASE_SERVICE_ROLE_KEY must be set") when no real credentials are
# present in the test environment.
#
# The individual integration tests monkeypatch get_service_client via
# monkeypatch.setattr() so this stub is never used by test logic directly.
# ---------------------------------------------------------------------------
if "app.services.supabase_client" not in sys.modules:
    _fake_client = MagicMock()

    class _FakeSupabaseService:
        """Minimal SupabaseService stub that satisfies the module-level
        DepartmentRunner() call without requiring real DB credentials."""

        _instance = None
        _client = _fake_client  # non-None so __init__ returns early

        def __new__(cls):
            if cls._instance is None:
                cls._instance = object.__new__(cls)
            return cls._instance

        def __init__(self) -> None:
            pass  # _client is already set; real init is skipped

        @property
        def client(self):  # noqa: ANN201
            return _fake_client

    _sc_mod = types.ModuleType("app.services.supabase_client")
    _sc_mod.SupabaseService = _FakeSupabaseService  # type: ignore[attr-defined]
    _sc_mod.AsyncSupabaseService = MagicMock  # type: ignore[attr-defined]
    _sc_mod.get_service_client = MagicMock(return_value=_fake_client)  # type: ignore[attr-defined]
    _sc_mod.get_supabase_service = MagicMock(return_value=_FakeSupabaseService())  # type: ignore[attr-defined]
    _sc_mod.get_client = MagicMock(return_value=_fake_client)  # type: ignore[attr-defined]
    _sc_mod.get_anon_client = MagicMock(return_value=_fake_client)  # type: ignore[attr-defined]
    _sc_mod.get_async_service = MagicMock()  # type: ignore[attr-defined]
    _sc_mod.get_async_client = MagicMock()  # type: ignore[attr-defined]
    _sc_mod.get_async_anon_client = MagicMock()  # type: ignore[attr-defined]
    _sc_mod.get_supabase_client = MagicMock(return_value=_fake_client)  # type: ignore[attr-defined]
    _sc_mod.get_client_stats = MagicMock(return_value={})  # type: ignore[attr-defined]
    _sc_mod.invalidate_client = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.supabase_client"] = _sc_mod

    # Also seed the backward-compat wrapper so existing routers that do
    # `from app.services.supabase import get_service_client` get the stub.
    _sb_mod = types.ModuleType("app.services.supabase")
    _sb_mod.SupabaseService = _FakeSupabaseService  # type: ignore[attr-defined]
    _sb_mod.AsyncSupabaseService = MagicMock  # type: ignore[attr-defined]
    _sb_mod.get_service_client = MagicMock(return_value=_fake_client)  # type: ignore[attr-defined]
    _sb_mod.get_supabase_service = MagicMock(return_value=_FakeSupabaseService())  # type: ignore[attr-defined]
    _sb_mod.get_client = MagicMock(return_value=_fake_client)  # type: ignore[attr-defined]
    _sb_mod.get_anon_client = MagicMock(return_value=_fake_client)  # type: ignore[attr-defined]
    _sb_mod.get_async_service = MagicMock()  # type: ignore[attr-defined]
    _sb_mod.get_async_client = MagicMock()  # type: ignore[attr-defined]
    _sb_mod.get_async_anon_client = MagicMock()  # type: ignore[attr-defined]
    _sb_mod.get_supabase_client = MagicMock(return_value=_fake_client)  # type: ignore[attr-defined]
    _sb_mod.get_client_stats = MagicMock(return_value={})  # type: ignore[attr-defined]
    _sb_mod.invalidate_client = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.supabase"] = _sb_mod
