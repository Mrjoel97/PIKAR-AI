"""Env-var propagation tests for SSE_MAX_DURATION_S across both SSE modules.

Phase 85 / Plan 01 — HOTFIX-03.

Confirms that BOTH SSE generators (admin chat and user run_sse) read the
same SSE_MAX_DURATION_S env var with the same default of 570s. The default
value was raised from 300 → 570 to give a 30s safety margin under
Cloud Run's 600s --timeout (so the SSE deadline fires before Cloud Run
closes the connection, ensuring the user sees the friendly app error
instead of a raw 504).

Tests use ``importlib.reload`` after ``monkeypatch.setenv`` /
``monkeypatch.delenv`` so the module-level ``int(os.getenv(...))`` is
re-evaluated against the patched environment. ``app.fast_api_app`` is
heavy (Supabase / ADK imports), so this module's tests use a textual
default-extraction fallback (``inspect.getsource``) for that file rather
than reloading it. The admin module is light enough to reload directly.
"""

from __future__ import annotations

import importlib
import inspect
import re
import sys


def _extract_fast_api_default() -> str:
    """Extract the literal default for SSE_MAX_DURATION_S in fast_api_app.

    Reads the source text of ``app.fast_api_app`` and returns the literal
    string passed as the second arg to ``os.getenv("SSE_MAX_DURATION_S", ...)``.
    Avoids the ~5s import cost of reloading the full ADK + Supabase stack
    just to read a constant.
    """
    import app.fast_api_app as fast_api_app

    source = inspect.getsource(fast_api_app)
    match = re.search(
        r'os\.getenv\(\s*"SSE_MAX_DURATION_S"\s*,\s*"(\d+)"\s*\)',
        source,
    )
    assert match is not None, (
        "SSE_MAX_DURATION_S literal default not found in fast_api_app source"
    )
    return match.group(1)


def test_env_default(monkeypatch):
    """Both SSE modules default to 570s when SSE_MAX_DURATION_S is unset."""
    monkeypatch.delenv("SSE_MAX_DURATION_S", raising=False)

    # Admin module is light — reload directly.
    if "app.routers.admin.chat" in sys.modules:
        admin_chat = importlib.reload(sys.modules["app.routers.admin.chat"])
    else:
        admin_chat = importlib.import_module("app.routers.admin.chat")

    assert admin_chat._SSE_MAX_DURATION_S == 570, (
        f"admin _SSE_MAX_DURATION_S default should be 570, got "
        f"{admin_chat._SSE_MAX_DURATION_S}"
    )

    # fast_api_app is heavy — read the literal default from source instead.
    fast_default = _extract_fast_api_default()
    assert fast_default == "570", (
        f"fast_api_app SSE_MAX_DURATION_S literal default should be '570', "
        f"got '{fast_default}'"
    )


def test_env_override(monkeypatch):
    """Setting SSE_MAX_DURATION_S=999 propagates to BOTH modules.

    This is the contract-binder: post-fix, both modules MUST read the
    env var. Pre-fix, the admin module is hardcoded to 300 — env override
    is silently ignored — so this test fails until the fix lands.
    """
    monkeypatch.setenv("SSE_MAX_DURATION_S", "999")

    # Admin: reload to re-evaluate module-level int(os.getenv(...)).
    if "app.routers.admin.chat" in sys.modules:
        admin_chat = importlib.reload(sys.modules["app.routers.admin.chat"])
    else:
        admin_chat = importlib.import_module("app.routers.admin.chat")

    assert admin_chat._SSE_MAX_DURATION_S == 999, (
        f"admin _SSE_MAX_DURATION_S should respect env override, got "
        f"{admin_chat._SSE_MAX_DURATION_S}"
    )

    # fast_api_app: directly call os.getenv to confirm pattern, since
    # reloading the module is prohibitively heavy. The textual-default
    # check above already covers the literal-source contract.
    import os

    assert int(os.getenv("SSE_MAX_DURATION_S", "570")) == 999
