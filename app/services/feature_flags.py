# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Feature-flag helpers for controlled rollouts."""

import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_workflow_kill_switch_enabled() -> bool:
    """Hard stop for workflow starts."""
    return _as_bool(os.getenv("WORKFLOW_KILL_SWITCH"), default=False)


def is_workflow_canary_enabled() -> bool:
    """Whether workflow execution should be limited to canary users."""
    return _as_bool(os.getenv("WORKFLOW_CANARY_ENABLED"), default=False)


def is_user_allowed_for_workflow_canary(user_id: str) -> bool:
    """Check if user is in canary allowlist."""
    raw = os.getenv("WORKFLOW_CANARY_USER_IDS", "")
    allow = {item.strip() for item in raw.split(",") if item.strip()}
    if not allow:
        return False
    return user_id in allow
