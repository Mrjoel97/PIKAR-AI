# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the Google Workspace startup-WARN guard (Phase 102, WORKSPACE-06)."""

from __future__ import annotations

import logging

import pytest

_WORKSPACE_VARS = (
    "GOOGLE_WORKSPACE_CLIENT_ID",
    "GOOGLE_WORKSPACE_CLIENT_SECRET",
    "GOOGLE_WORKSPACE_REDIRECT_URI",
)


def test_workspace_env_warn_all_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: logging.LogCaptureFixture,
) -> None:
    """All three vars unset (and PYTEST_CURRENT_TEST cleared) emits exactly one WARN."""
    from app.integrations.google.client import _warn_missing_google_workspace_env

    for var in _WORKSPACE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    caplog.set_level(logging.WARNING, logger="app.integrations.google.client")
    _warn_missing_google_workspace_env()

    warn_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warn_records) == 1
    msg = warn_records[0].getMessage()
    for var in _WORKSPACE_VARS:
        assert var in msg


def test_workspace_env_warn_partial_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: logging.LogCaptureFixture,
) -> None:
    """Only the missing var(s) appear in the warning; set vars are not mentioned."""
    from app.integrations.google.client import _warn_missing_google_workspace_env

    monkeypatch.setenv("GOOGLE_WORKSPACE_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("GOOGLE_WORKSPACE_CLIENT_SECRET", "fake-secret")
    monkeypatch.delenv("GOOGLE_WORKSPACE_REDIRECT_URI", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    caplog.set_level(logging.WARNING, logger="app.integrations.google.client")
    _warn_missing_google_workspace_env()

    warn_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warn_records) == 1
    msg = warn_records[0].getMessage()
    assert "GOOGLE_WORKSPACE_REDIRECT_URI" in msg
    assert "GOOGLE_WORKSPACE_CLIENT_ID" not in msg
    assert "GOOGLE_WORKSPACE_CLIENT_SECRET" not in msg


def test_workspace_env_warn_all_set_no_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: logging.LogCaptureFixture,
) -> None:
    """When all three vars are set, no WARN is emitted."""
    from app.integrations.google.client import _warn_missing_google_workspace_env

    for var in _WORKSPACE_VARS:
        monkeypatch.setenv(var, f"fake-{var.lower()}")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    caplog.set_level(logging.WARNING, logger="app.integrations.google.client")
    _warn_missing_google_workspace_env()

    warn_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warn_records == []


def test_workspace_env_warn_suppressed_in_pytest(
    monkeypatch: pytest.MonkeyPatch,
    caplog: logging.LogCaptureFixture,
) -> None:
    """PYTEST_CURRENT_TEST presence suppresses the WARN even when vars are missing."""
    from app.integrations.google.client import _warn_missing_google_workspace_env

    for var in _WORKSPACE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_workspace_env_warn_suppressed_in_pytest")

    caplog.set_level(logging.WARNING, logger="app.integrations.google.client")
    _warn_missing_google_workspace_env()

    warn_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warn_records == []
