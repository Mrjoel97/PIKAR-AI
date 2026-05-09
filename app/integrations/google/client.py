# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Google API client utilities.

Provides authenticated clients for Google Sheets and Drive APIs
using OAuth tokens from Supabase authentication.
"""

import logging
import os
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

logger = logging.getLogger(__name__)


def get_google_credentials(
    provider_token: str,
    provider_refresh_token: str | None = None,
) -> Credentials:
    """Create Google credentials from Supabase provider tokens.

    When a user logs in with Google via Supabase Auth, the session
    contains provider_token (access token) and provider_refresh_token.

    Args:
        provider_token: Google OAuth access token from Supabase session.
        provider_refresh_token: Optional refresh token for token renewal.

    Returns:
        Google Credentials object for API authentication.
    """
    return Credentials(
        token=provider_token,
        refresh_token=provider_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        # Client ID/secret not needed when we already have valid tokens
    )


def get_sheets_service(credentials: Credentials) -> Resource:
    """Get authenticated Google Sheets API service.

    Args:
        credentials: Google OAuth credentials.

    Returns:
        Google Sheets API v4 service resource.
    """
    return build("sheets", "v4", credentials=credentials)


def get_drive_service(credentials: Credentials) -> Resource:
    """Get authenticated Google Drive API service.

    Args:
        credentials: Google OAuth credentials.

    Returns:
        Google Drive API v3 service resource.
    """
    return build("drive", "v3", credentials=credentials)


def get_user_gmail_credentials(
    provider_refresh_token: str,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> Credentials:
    """Create Google credentials for background Gmail access using refresh token.

    Args:
        provider_refresh_token: Google OAuth refresh token stored in the user profile.
        client_id: Optional OAuth client ID; falls back to GOOGLE_CLIENT_ID env var.
        client_secret: Optional OAuth client secret; falls back to GOOGLE_CLIENT_SECRET env var.

    Returns:
        Google Credentials object suitable for background Gmail access.

    Raises:
        ValueError: If refresh token is missing or client credentials are unresolvable.
    """
    resolved_client_id = client_id or os.environ.get("GOOGLE_CLIENT_ID", "")
    resolved_client_secret = client_secret or os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if not provider_refresh_token:
        raise ValueError("Refresh token required for background Gmail access.")
    if not resolved_client_id or not resolved_client_secret:
        raise ValueError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET required for background Gmail access."
        )
    return Credentials(
        token=None,
        refresh_token=provider_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=resolved_client_id,
        client_secret=resolved_client_secret,
    )


def get_credentials_from_supabase_session(session: dict[str, Any]) -> Credentials:
    """Extract Google credentials from a Supabase session object.

    Args:
        session: Supabase session dict containing provider tokens.

    Returns:
        Google Credentials object.

    Raises:
        ValueError: If session doesn't contain Google provider tokens.
    """
    provider_token = session.get("provider_token")
    if not provider_token:
        raise ValueError(
            "Session does not contain provider_token. "
            "User must authenticate with Google OAuth."
        )

    return get_google_credentials(
        provider_token=provider_token,
        provider_refresh_token=session.get("provider_refresh_token"),
    )


def _warn_missing_google_workspace_env() -> None:
    """Emit WARN for missing Google Workspace OAuth env vars in non-test environments.

    Skipped automatically when ``PYTEST_CURRENT_TEST`` is set so pytest runs are
    quiet. Mirrors the pattern used by ``get_user_gmail_credentials`` for
    unresolvable client_id/secret. Phase 102 (WORKSPACE-06).
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    missing = [
        v
        for v in (
            "GOOGLE_WORKSPACE_CLIENT_ID",
            "GOOGLE_WORKSPACE_CLIENT_SECRET",
            "GOOGLE_WORKSPACE_REDIRECT_URI",
        )
        if not os.environ.get(v)
    ]
    if missing:
        logger.warning(
            "Google Workspace OAuth not configured: missing env vars %s. "
            "Per-user Google Workspace integration will be unavailable until set.",
            ", ".join(missing),
        )


# Run at module import so missing config surfaces at app boot.
_warn_missing_google_workspace_env()
