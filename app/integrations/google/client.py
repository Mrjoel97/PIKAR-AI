# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google API client utilities.

Provides authenticated clients for Google Sheets and Drive APIs
using OAuth tokens from Supabase authentication.
"""

from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource


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
