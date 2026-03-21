import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async


async def request_human_approval(
    action_type: str, action_description: str, payload: dict[str, Any]
) -> str:
    """
    Pauses execution and requests human approval via a generated Magic Link.

    Args:
        action_type: Short identifier like 'POST_TWEET' or 'SEND_EMAIL'.
        action_description: Human readable text for the user,
            e.g. "Post a tweet about the launch".
        payload: The exact data to be acted upon.

    Returns:
        A message containing the Magic Link to show to the user.
    """
    try:
        supabase = get_service_client()
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        payload = dict(payload or {})

        data = {
            "token": token_hash,
            "action_type": action_type,
            "payload": payload,
            "expires_at": expires_at.isoformat(),
            "status": "PENDING",
        }

        await execute_async(
            supabase.table("approval_requests").insert(data),
            op_name="approvals.create",
        )

        base_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
        link = f"{base_url}/approval/{token}"
        return (
            f"I have generated an approval request for "
            f"'{action_description}'.\n"
            f"Please approve it here: {link}"
        )

    except Exception as e:
        return f"Failed to generate approval link: {e!s}"
