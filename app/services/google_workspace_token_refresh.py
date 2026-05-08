# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Synchronous Google Workspace OAuth token refresh.

Companion to ``GoogleWorkspaceAuthService`` for the in-flight tool helper
path, which is sync. Mirrors the logic of
``IntegrationManager._refresh_token`` (async) but uses ``httpx.Client`` (sync)
so it can be called from the sync ADK ``before_model_callback`` and tool
functions without crossing the async/sync boundary.

Phase 102, requirement WORKSPACE-04 (auto-refresh within 5 minutes of expiry).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

from app.services.google_workspace_auth_service import (
    get_google_workspace_auth_service,
)

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _is_expiring_soon(expires_at_iso: str | None, *, minutes: int) -> bool:
    """Return True when the ISO-8601 expiry is within ``minutes`` of now (UTC).

    Returns False (no-op) when the input is missing, unparseable, or far in
    the future. Naive datetimes are interpreted as UTC.
    """
    if not expires_at_iso:
        return False
    try:
        expires_at = datetime.fromisoformat(expires_at_iso)
    except (ValueError, TypeError):
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at - datetime.now(tz=timezone.utc) < timedelta(minutes=minutes)


def refresh_if_expiring(tool_context, *, threshold_minutes: int = 5) -> None:
    """Refresh ``google_provider_token`` in ``tool_context`` if expiring soon.

    Best-effort: silently no-ops on missing user_id, missing refresh token,
    unconfigured env, ``expires_at=None`` (legacy fallback paths), or any
    network failure. On success, mutates ``tool_context.state`` in place
    with the new access/refresh token plus the new expiry, then writes
    through to ``integration_credentials`` via ``sync_credentials`` so
    future sessions benefit.

    Args:
        tool_context: ADK tool context (must expose a mutable ``.state`` dict).
        threshold_minutes: Refresh when expiry is within this many minutes
            (default 5).
    """
    state = tool_context.state
    if not _is_expiring_soon(
        state.get("google_token_expires_at"), minutes=threshold_minutes
    ):
        return

    user_id = state.get("user_id")
    refresh_token = state.get("google_refresh_token")
    if not user_id or not refresh_token:
        return

    client_id = os.environ.get("GOOGLE_WORKSPACE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_WORKSPACE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return

    try:
        with httpx.Client(timeout=30.0) as http:
            resp = http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("refresh_if_expiring: token refresh failed: %s", exc)
        return

    new_access = data.get("access_token", "")
    new_refresh = data.get("refresh_token", refresh_token)
    expires_in = data.get("expires_in")
    new_expires_at = (
        (datetime.now(tz=timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
        if expires_in
        else None
    )

    if new_access:
        state["google_provider_token"] = new_access
    if new_refresh:
        state["google_refresh_token"] = new_refresh
    if new_expires_at:
        state["google_token_expires_at"] = new_expires_at

    try:
        get_google_workspace_auth_service().sync_credentials(
            user_id=user_id,
            access_token=new_access,
            refresh_token=new_refresh,
            expires_at=new_expires_at,
        )
    except Exception as exc:
        logger.debug("refresh_if_expiring: sync_credentials failed: %s", exc)


__all__ = ["GOOGLE_TOKEN_URL", "refresh_if_expiring"]
