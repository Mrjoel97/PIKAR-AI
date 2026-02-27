"""Integration-test bootstrap configuration.

This file is loaded by pytest before integration test modules are imported.
It forces local test-safe import behavior for app.fast_api_app so tests do
not depend on native A2A/grpc bindings being available in CI/dev shells.
"""

from __future__ import annotations

import os


# Skip heavy optional runtime imports that are not required for API endpoint
# integration tests, and avoid startup env validation noise in test runs.
os.environ.setdefault("LOCAL_DEV_BYPASS", "1")
os.environ.setdefault("SKIP_ENV_VALIDATION", "1")
os.environ.setdefault("ENVIRONMENT", "test")
