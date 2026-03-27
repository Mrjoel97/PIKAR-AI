# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""API authentication handler for generated tools.

Provides runtime credential resolution, SSRF protection, and
optional Fernet-based encryption for stored credentials.
Credentials are stored per-user in the api_credentials table.
"""

from __future__ import annotations

import ipaddress
import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Credential encryption helpers
# ---------------------------------------------------------------------------


def _get_encryption_key() -> bytes | None:
    """Get encryption key from environment. Returns None if not configured."""
    key = os.environ.get("API_ENCRYPTION_KEY")
    if key:
        return key.encode() if isinstance(key, str) else key
    return None


def encrypt_credential(value: str) -> str:
    """Encrypt a credential value. Falls back to plaintext if encryption key not configured."""
    key = _get_encryption_key()
    if not key:
        logger.warning("API_ENCRYPTION_KEY not set, storing credential as plaintext")
        return value
    try:
        from cryptography.fernet import Fernet

        f = Fernet(key)
        return f.encrypt(value.encode()).decode()
    except ImportError:
        logger.warning("cryptography package not available, storing as plaintext")
        return value
    except Exception as exc:
        logger.warning("Encryption failed, storing as plaintext: %s", exc)
        return value


def decrypt_credential(encrypted: str) -> str:
    """Decrypt a credential value. Handles plaintext fallback gracefully."""
    key = _get_encryption_key()
    if not key:
        return encrypted  # Assume plaintext
    try:
        from cryptography.fernet import Fernet

        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return encrypted  # Assume plaintext (pre-encryption data)


# ---------------------------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------------------------

# Schemes allowed in generated tool URLs.
_ALLOWED_SCHEMES = frozenset({"http", "https"})

# Private/reserved IP ranges that must never be contacted by generated tools.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6 private ranges
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_url(url: str) -> str:
    """Validate a URL is safe to call (no SSRF to internal networks).

    Args:
        url: The full URL to validate.

    Returns:
        The validated URL string.

    Raises:
        ValueError: If the URL targets a private/reserved address or uses
            a disallowed scheme.
    """
    parsed = urlparse(url)

    # Scheme check
    if parsed.scheme not in _ALLOWED_SCHEMES:
        msg = f"URL scheme '{parsed.scheme}' is not allowed. Use http or https."
        raise ValueError(msg)

    hostname = parsed.hostname
    if not hostname:
        msg = "URL must include a hostname."
        raise ValueError(msg)

    # Resolve hostname to check for private IPs
    try:
        addr = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if addr in network:
                msg = f"URL targets a private/reserved address ({hostname})."
                raise ValueError(msg)
    except ValueError as exc:
        # If it's not a valid IP literal it's a regular hostname — that's fine.
        # Re-raise only if this was our own "private address" error.
        if "private/reserved" in str(exc) or "not allowed" in str(exc):
            raise
        # Regular hostname (e.g. api.stripe.com) — allow it.

    return url


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------


def get_api_credential(secret_name: str) -> str:
    """Resolve an API credential at runtime.

    Resolution order:
        1. Environment variable ``API_SECRET_{NAME_UPPER}``
        2. User credential store (via request-context ``user_id``)

    This function is called by generated tool code at runtime.  It is
    intentionally **synchronous** because ADK tool functions are sync.

    Args:
        secret_name: Name of the credential (e.g. ``"stripe_api_key"``).

    Returns:
        The credential value as a plain string.

    Raises:
        ValueError: If the credential cannot be found in any source.
    """
    # 1. Check environment variable
    env_key = f"API_SECRET_{secret_name.upper()}"
    env_val = os.environ.get(env_key)
    if env_val:
        return env_val

    # 2. Check user credential store
    try:
        from app.services.request_context import get_current_user_id

        user_id = get_current_user_id()
        if user_id and user_id != "anonymous":
            from app.services.supabase_client import get_service_client

            supabase = get_service_client()
            result = (
                supabase.table("api_credentials")
                .select("encrypted_value")
                .eq("user_id", user_id)
                .eq("name", secret_name)
                .single()
                .execute()
            )
            if result.data:
                return decrypt_credential(result.data["encrypted_value"])
    except Exception as exc:
        logger.warning(
            "Failed to resolve credential '%s' from store: %s",
            secret_name,
            exc,
        )

    msg = (
        f"API credential '{secret_name}' not found. "
        f"Set env var {env_key} or store it via the Configuration tools."
    )
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Credential CRUD service (async, for use from FastAPI routes / services)
# ---------------------------------------------------------------------------


class APICredentialService:
    """Manage API credentials for users.

    All mutating methods are async because they are called from FastAPI
    async routes/services and must not block the event loop.
    """

    def __init__(self) -> None:
        from app.services.supabase_client import get_service_client

        self._supabase = get_service_client()

    # -- write ---------------------------------------------------------------

    async def store_credential(
        self,
        user_id: str,
        name: str,
        value: str,
        auth_scheme: str = "api_key",
        metadata: dict | None = None,
    ) -> dict:
        """Store (or update) a credential for *user_id*.

        Uses an upsert keyed on ``(user_id, name)`` so calling this twice
        for the same credential simply overwrites the value.

        Args:
            user_id: Owner of the credential.
            name: Credential identifier (e.g. ``"stripe_api_key"``).
            value: The raw credential value.
            auth_scheme: One of ``"api_key"``, ``"bearer"``, ``"basic"``,
                ``"oauth2"``, ``"custom"``.
            metadata: Optional JSON-serialisable metadata dict.

        Returns:
            ``{"status": "success", "name": name}``
        """
        from app.services.supabase_async import execute_async

        data = {
            "user_id": user_id,
            "name": name,
            "encrypted_value": encrypt_credential(value),
            "auth_scheme": auth_scheme,
            "metadata": metadata or {},
        }
        await execute_async(
            self._supabase.table("api_credentials").upsert(
                data, on_conflict="user_id,name"
            ),
            op_name="api_credentials.store",
        )
        return {"status": "success", "name": name}

    # -- read ----------------------------------------------------------------

    async def get_credential(self, user_id: str, name: str) -> str | None:
        """Return the decrypted value of a single credential, or ``None``."""
        from app.services.supabase_async import execute_async

        result = await execute_async(
            self._supabase.table("api_credentials")
            .select("encrypted_value")
            .eq("user_id", user_id)
            .eq("name", name)
            .single(),
            op_name="api_credentials.get",
        )
        if result.data:
            return decrypt_credential(result.data["encrypted_value"])
        return None

    async def list_credentials(self, user_id: str) -> list[dict]:
        """List credential metadata (never values) for *user_id*."""
        from app.services.supabase_async import execute_async

        result = await execute_async(
            self._supabase.table("api_credentials")
            .select("name, auth_scheme, created_at, updated_at")
            .eq("user_id", user_id),
            op_name="api_credentials.list",
        )
        return result.data or []

    # -- delete --------------------------------------------------------------

    async def delete_credential(self, user_id: str, name: str) -> dict:
        """Delete a stored credential.

        Returns:
            ``{"status": "success", "deleted": name}``
        """
        from app.services.supabase_async import execute_async

        await execute_async(
            self._supabase.table("api_credentials")
            .delete()
            .eq("user_id", user_id)
            .eq("name", name),
            op_name="api_credentials.delete",
        )
        return {"status": "success", "deleted": name}
