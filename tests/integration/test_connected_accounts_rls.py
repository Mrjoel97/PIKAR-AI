"""Integration test: cross-user RLS denial on public.connected_accounts (AUTH-01).

Boots against a local Supabase stack (`supabase start`). Verifies that a user
authenticated with their JWT against the anon-key client cannot SELECT another
user's connected_accounts rows under the policy from
``20260415113000_harden_connected_accounts_rls.sql`` (re-asserted by
``20260509000000_phase101_verify_connected_accounts_rls.sql``).

Run with:
    supabase start
    uv run pytest tests/integration/test_connected_accounts_rls.py -x -v

Skips cleanly if no local Supabase stack is running (no Docker, CI without
Supabase). Skips never escalate to FAIL — this is a regression gate, not a
hard CI requirement.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import uuid4

import pytest

try:
    from supabase import create_client
except ImportError:  # pragma: no cover - supabase is in pyproject deps
    create_client = None  # type: ignore[assignment]


def _supabase_status_keys(status: dict[str, Any]) -> dict[str, str] | None:
    """Map keys returned by `supabase status --output json` to our triple.

    The Supabase CLI returns display-friendly keys like ``"API URL"`` or
    ``"ANON_KEY"`` depending on version. Try the well-known shapes and return
    ``None`` if we cannot find what we need.
    """
    api_url = (
        status.get("API URL")
        or status.get("api_url")
        or status.get("API_URL")
        or status.get("api")
    )
    anon_key = (
        status.get("anon key")
        or status.get("anon_key")
        or status.get("ANON_KEY")
        or status.get("anonKey")
    )
    service_role_key = (
        status.get("service_role key")
        or status.get("service_role_key")
        or status.get("SERVICE_ROLE_KEY")
        or status.get("serviceRoleKey")
    )
    if not (api_url and anon_key and service_role_key):
        return None
    return {
        "api_url": api_url,
        "anon_key": anon_key,
        "service_role_key": service_role_key,
    }


@pytest.fixture(scope="session")
def supabase_local() -> dict[str, str]:
    """Probe the local Supabase stack and return its connection details.

    Skips the test if:
    - The supabase CLI is not on PATH.
    - `supabase status` times out or returns non-zero (stack not running).
    - The ``supabase`` Python client is not installed.
    - The JSON output cannot be parsed into the expected triple.
    """
    if create_client is None:
        pytest.skip("supabase python client not installed")

    try:
        proc = subprocess.run(
            ["supabase", "status", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("supabase CLI not available or hung; run `supabase start`")

    if proc.returncode != 0:
        pytest.skip(
            f"supabase local stack not running (exit={proc.returncode}); "
            "run `supabase start`"
        )

    try:
        status = json.loads(proc.stdout)
    except json.JSONDecodeError:
        pytest.skip("could not parse `supabase status --output json` output")

    triple = _supabase_status_keys(status)
    if triple is None:
        pytest.skip(
            "supabase status JSON missing API URL / anon key / service_role key"
        )
    return triple


def test_user_a_cannot_read_user_b_connected_accounts(
    supabase_local: dict[str, str],
) -> None:
    """User A authenticated via anon-key + JWT must only see A's own rows."""
    api_url = supabase_local["api_url"]
    anon_key = supabase_local["anon_key"]
    service_role_key = supabase_local["service_role_key"]

    service = create_client(api_url, service_role_key)

    suffix = uuid4().hex[:8]
    email_a = f"phase101-rls-a-{suffix}@test.local"
    email_b = f"phase101-rls-b-{suffix}@test.local"
    password = "test-rls-pass-1234"

    user_a_id: str | None = None
    user_b_id: str | None = None

    try:
        a_create = service.auth.admin.create_user(
            {
                "email": email_a,
                "password": password,
                "email_confirm": True,
            }
        )
        user_a_id = a_create.user.id

        b_create = service.auth.admin.create_user(
            {
                "email": email_b,
                "password": password,
                "email_confirm": True,
            }
        )
        user_b_id = b_create.user.id

        service.table("connected_accounts").insert(
            {
                "user_id": user_a_id,
                "platform": "linkedin",
                "access_token": "tok-a",
                "status": "active",
            }
        ).execute()
        service.table("connected_accounts").insert(
            {
                "user_id": user_b_id,
                "platform": "linkedin",
                "access_token": "tok-b",
                "status": "active",
            }
        ).execute()

        client_a = create_client(api_url, anon_key)
        client_a.auth.sign_in_with_password({"email": email_a, "password": password})

        result = (
            client_a.table("connected_accounts")
            .select("user_id, platform, access_token")
            .execute()
        )

        assert len(result.data) == 1, (
            f"RLS leak: user A saw {len(result.data)} rows, expected 1"
        )
        assert result.data[0]["user_id"] == user_a_id
        assert result.data[0]["access_token"] == "tok-a"
    finally:
        # CASCADE on auth.users -> connected_accounts.user_id removes the rows.
        if user_a_id:
            try:
                service.auth.admin.delete_user(user_a_id)
            except Exception:
                pass
        if user_b_id:
            try:
                service.auth.admin.delete_user(user_b_id)
            except Exception:
                pass
