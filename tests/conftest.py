"""Root test-suite conftest.

This file is loaded by pytest before any test directory conftest is processed.
Its sole responsibility is to provide the ``pytest_collect_file`` hook that
purges unit-test module stubs from sys.modules immediately before any
integration test file is imported for collection.

Background
----------
Module-level ``_stub()`` calls in unit test files (e.g. ``test_workflow_execution_stream.py``)
insert thin fakes into ``sys.modules`` so the router under test can be imported
without real DB / ADK / Redis dependencies.  Because these calls run at
*collection* time (when pytest imports the test module), they persist in
``sys.modules`` for the remainder of the pytest session.  When the integration
test files are subsequently imported they transitively pull in the full
``app.fast_api_app`` module graph, which expects the *real* symbols from those
modules — triggering ImportError.

The ``tests/integration/conftest.py`` cannot solve this alone because that
conftest is loaded *before* any test module is imported, so the stubs have not
yet been inserted when it runs.

The fix: this hook fires for every file collected.  When it detects an
integration test path it purges the known unit-test stubs so Python
re-imports the real modules on the next ``from app import ...`` statement.
"""

from __future__ import annotations

import sys
from pathlib import Path


# These module names are stubbed by module-level _stub() calls in unit test
# files.  They are purged from sys.modules each time an integration test
# file is about to be collected so the integration test gets the real
# implementations.
_UNIT_TEST_STUB_PREFIXES: tuple[str, ...] = (
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
    "app.agents.tools.registry",
)


def pytest_collect_file(parent, file_path: Path):  # noqa: ANN001
    """Purge unit-test stubs before importing any integration test module."""
    # We only act on Python test files inside tests/integration/
    try:
        rel = file_path.relative_to(parent.config.rootpath / "tests" / "integration")
    except ValueError:
        return None  # not under tests/integration/ — do nothing

    if not file_path.name.startswith("test_") or file_path.suffix != ".py":
        return None

    # Purge the stubs so the integration test import gets real modules.
    for mod_name in list(sys.modules):
        for stub in _UNIT_TEST_STUB_PREFIXES:
            if mod_name == stub or mod_name.startswith(stub + "."):
                sys.modules.pop(mod_name, None)
                break

    # Also purge any router/app modules that may have been cached with stub
    # dependencies baked in, so they get reimported with real deps.
    for mod_name in list(sys.modules):
        if mod_name.startswith("app.") and mod_name not in (
            "app.services.supabase_client",
            "app.services.supabase",
        ):
            # Only evict app.* modules that were imported AFTER the stubs were
            # inserted (indicated by having no __file__ or a stub __file__).
            mod = sys.modules[mod_name]
            file_attr = getattr(mod, "__file__", None)
            if file_attr is None:
                # Module has no __file__ — it's a stub or a types.ModuleType
                sys.modules.pop(mod_name, None)

    return None
