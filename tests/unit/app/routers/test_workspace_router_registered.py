# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""The workspace router must be mounted under the main FastAPI app."""

from __future__ import annotations


def test_workspace_router_registered():
    """GET /workspace/events must be a known route on the production app."""
    from app.fast_api_app import app

    paths = {route.path for route in app.routes}
    assert "/workspace/events" in paths
