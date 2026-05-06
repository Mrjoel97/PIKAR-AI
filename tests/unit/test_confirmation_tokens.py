# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the confirmation token TTL helper.

The TTL governs how long an admin has to confirm a CONFIRM-tier action
(refund, role change, knowledge delete) after the AdminAgent surfaces a
confirmation card. The previous hardcoded 5-minute window was too short
to read a refund summary and confirm without re-triggering the flow.
"""

from __future__ import annotations

import pytest


def test_default_ttl_is_15_minutes(monkeypatch):
    """No env var → 15-minute (900s) default — long enough to read & confirm."""
    monkeypatch.delenv("ADMIN_CONFIRMATION_TTL_SECONDS", raising=False)
    from app.services.confirmation_tokens import _get_token_ttl

    assert _get_token_ttl() == 900


def test_env_var_overrides_default(monkeypatch):
    """Operator can tune ADMIN_CONFIRMATION_TTL_SECONDS at runtime."""
    monkeypatch.setenv("ADMIN_CONFIRMATION_TTL_SECONDS", "1200")
    from app.services.confirmation_tokens import _get_token_ttl

    assert _get_token_ttl() == 1200


def test_invalid_env_value_falls_back_to_default(monkeypatch):
    """Garbage value falls back to 900s rather than raising at runtime."""
    monkeypatch.setenv("ADMIN_CONFIRMATION_TTL_SECONDS", "not-a-number")
    from app.services.confirmation_tokens import _get_token_ttl

    assert _get_token_ttl() == 900


@pytest.mark.parametrize(
    ("raw_value", "expected_clamped"),
    [
        ("0", 60),  # zero → minimum
        ("30", 60),  # below minimum → minimum
        ("60", 60),  # at minimum → unchanged
        ("3600", 3600),  # at maximum → unchanged
        ("7200", 3600),  # above maximum → maximum
    ],
)
def test_ttl_is_clamped_to_safe_bounds(monkeypatch, raw_value, expected_clamped):
    """TTL is clamped to [60, 3600] to prevent operator footguns."""
    monkeypatch.setenv("ADMIN_CONFIRMATION_TTL_SECONDS", raw_value)
    from app.services.confirmation_tokens import _get_token_ttl

    assert _get_token_ttl() == expected_clamped
