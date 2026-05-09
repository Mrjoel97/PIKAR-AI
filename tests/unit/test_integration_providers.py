# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the integration provider registry (Phase 102, WORKSPACE-02)."""

from __future__ import annotations


def test_google_workspace_registered() -> None:
    """google_workspace must be a first-class entry in PROVIDER_REGISTRY.

    Pins the canonical OAuth/token URLs, env var names, and the 8 required
    scopes so accidental edits cannot silently break the bridge added in
    WORKSPACE-03.
    """
    from app.config.integration_providers import PROVIDER_REGISTRY

    assert "google_workspace" in PROVIDER_REGISTRY
    entry = PROVIDER_REGISTRY["google_workspace"]

    assert entry.auth_type == "oauth2"
    assert entry.auth_url == "https://accounts.google.com/o/oauth2/v2/auth"
    assert entry.token_url == "https://oauth2.googleapis.com/token"
    assert entry.client_id_env == "GOOGLE_WORKSPACE_CLIENT_ID"
    assert entry.client_secret_env == "GOOGLE_WORKSPACE_CLIENT_SECRET"

    expected_scopes = {
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/userinfo.email",
    }
    assert set(entry.scopes) == expected_scopes
