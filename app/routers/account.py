# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Account Management API Router.

Handles account deletion (self-service and Facebook data deletion callback)
and deletion status tracking for GDPR/Meta platform compliance.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["Account"])

# token_urlsafe(16) produces 22-char strings from the base64url alphabet
_CONFIRMATION_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{20,30}$")


# ============================================================================
# Pydantic Models
# ============================================================================


class FacebookDeletionResponse(BaseModel):
    """Response returned to Facebook after processing a data deletion callback."""

    url: str
    confirmation_code: str


class DeleteAccountResponse(BaseModel):
    """Response after a user-initiated account deletion."""

    success: bool
    message: str


class DeletionStatusResponse(BaseModel):
    """Status of a data deletion request."""

    id: str
    status: str
    platform: str
    requested_at: str
    completed_at: str | None = None


# ============================================================================
# Facebook Signed Request Verification
# ============================================================================


def _b64url_decode(data: str) -> bytes:
    """Decode Facebook's unpadded base64url encoding."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def _verify_facebook_signed_request(signed_request: str, app_secret: str) -> dict:
    """Parse and verify Facebook's signed_request parameter.

    Facebook sends a dot-separated string: <base64url_signature>.<base64url_payload>.
    The signature is HMAC-SHA256(app_secret, payload_raw).

    Args:
        signed_request: The raw signed_request form field from Facebook.
        app_secret: The Facebook App Secret for HMAC verification.

    Returns:
        Decoded JSON payload from the signed request.

    Raises:
        HTTPException: If the request is malformed or signature is invalid.
    """
    try:
        encoded_sig, payload_raw = signed_request.split(".", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Malformed signed_request")

    sig = _b64url_decode(encoded_sig)
    expected_sig = hmac.new(
        app_secret.encode("utf-8"),
        payload_raw.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        data = json.loads(_b64url_decode(payload_raw))
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid payload encoding")

    return data


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/facebook-deletion-callback",
    response_model=FacebookDeletionResponse,
)
@limiter.limit("5/minute")
async def facebook_deletion_callback(
    request: Request,
    signed_request: str = Form(...),
) -> FacebookDeletionResponse:
    """Handle Facebook's data deletion callback.

    Facebook sends this when a user requests deletion of their data
    from the Facebook app settings. The signed_request is verified
    using HMAC-SHA256 with the app secret.

    This endpoint is unauthenticated — Facebook signs the payload instead.
    """
    app_secret = os.environ.get("FACEBOOK_APP_SECRET")
    if not app_secret:
        logger.error(
            "FACEBOOK_APP_SECRET not configured — cannot process deletion callback"
        )
        raise HTTPException(status_code=500, detail="Server configuration error")

    # Verify and decode the signed request
    payload = _verify_facebook_signed_request(signed_request, app_secret)
    fb_user_id = str(payload.get("user_id", ""))

    if not fb_user_id:
        raise HTTPException(status_code=400, detail="Missing user_id in signed request")

    supabase = get_service_client()
    confirmation_code = secrets.token_urlsafe(16)

    # Check for idempotency — Meta may resend the same callback
    existing = (
        supabase.table("data_deletion_requests")
        .select("confirmation_code")
        .eq("facebook_user_id", fb_user_id)
        .eq("platform", "facebook")
        .in_("status", ["pending", "completed"])
        .limit(1)
        .execute()
    )
    if existing.data:
        existing_code = existing.data[0]["confirmation_code"]
        app_url = os.environ.get("NEXT_PUBLIC_APP_URL", "https://app.pikar.ai")
        return FacebookDeletionResponse(
            url=f"{app_url}/data-deletion/status?id={existing_code}",
            confirmation_code=existing_code,
        )

    # Look up the Supabase user linked to this Facebook account
    account_result = (
        supabase.table("connected_accounts")
        .select("user_id")
        .eq("platform", "facebook")
        .eq("platform_user_id", fb_user_id)
        .limit(1)
        .execute()
    )

    supabase_user_id = None
    if account_result.data:
        supabase_user_id = account_result.data[0]["user_id"]

    # Create the deletion request record
    supabase.table("data_deletion_requests").insert(
        {
            "user_id": supabase_user_id,
            "platform": "facebook",
            "facebook_user_id": fb_user_id,
            "status": "pending",
            "confirmation_code": confirmation_code,
        }
    ).execute()

    # Execute deletion if we found a linked user
    if supabase_user_id:
        try:
            supabase.rpc(
                "delete_user_account", {"p_user_id": supabase_user_id}
            ).execute()
            # Mark as completed after successful deletion
            supabase.table("data_deletion_requests").update(
                {"status": "completed", "completed_at": "now()"}
            ).eq("confirmation_code", confirmation_code).execute()
        except Exception:
            logger.exception(
                "Failed to delete user account for Facebook user %s (Supabase UID: %s)",
                fb_user_id,
                supabase_user_id,
            )
            # Mark request as failed but still return 200 (Meta requires it)
            supabase.table("data_deletion_requests").update(
                {"status": "failed", "error_detail": "Database deletion failed"}
            ).eq("confirmation_code", confirmation_code).execute()
    else:
        # No linked account — mark as completed (nothing to delete)
        supabase.table("data_deletion_requests").update(
            {"status": "completed", "completed_at": "now()"}
        ).eq("confirmation_code", confirmation_code).execute()

    app_url = os.environ.get("NEXT_PUBLIC_APP_URL", "https://app.pikar.ai")
    return FacebookDeletionResponse(
        url=f"{app_url}/data-deletion/status?id={confirmation_code}",
        confirmation_code=confirmation_code,
    )


@router.delete("/delete", response_model=DeleteAccountResponse)
@limiter.limit("3/minute")
async def delete_account(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> DeleteAccountResponse:
    """Permanently delete the authenticated user's account and all associated data.

    This action is irreversible. All user data across every table is removed
    via the delete_user_account() database function.
    """
    supabase = get_service_client()
    confirmation_code = secrets.token_urlsafe(16)

    # Create audit trail record before deletion
    supabase.table("data_deletion_requests").insert(
        {
            "user_id": current_user_id,
            "platform": "self",
            "status": "pending",
            "confirmation_code": confirmation_code,
        }
    ).execute()

    try:
        supabase.rpc("delete_user_account", {"p_user_id": current_user_id}).execute()
        # Mark as completed after successful deletion
        supabase.table("data_deletion_requests").update(
            {"status": "completed", "completed_at": "now()"}
        ).eq("confirmation_code", confirmation_code).execute()
    except Exception:
        logger.exception("Failed to delete account for user %s", current_user_id)
        supabase.table("data_deletion_requests").update(
            {"status": "failed", "error_detail": "Database deletion failed"}
        ).eq("confirmation_code", confirmation_code).execute()
        raise HTTPException(
            status_code=500,
            detail="Account deletion failed. Please contact privacy@pikar.ai for assistance.",
        )

    return DeleteAccountResponse(
        success=True,
        message="Your account and all associated data have been permanently deleted.",
    )


@router.get(
    "/deletion-status/{confirmation_code}",
    response_model=DeletionStatusResponse,
)
@limiter.limit("20/minute")
async def get_deletion_status(
    request: Request,
    confirmation_code: str,
) -> DeletionStatusResponse:
    """Check the status of a data deletion request.

    This endpoint is unauthenticated — access is gated by the
    unguessable confirmation code (16-byte token_urlsafe).
    """
    if not _CONFIRMATION_CODE_RE.match(confirmation_code):
        raise HTTPException(status_code=404, detail="Deletion request not found")

    supabase = get_service_client()

    result = (
        supabase.table("data_deletion_requests")
        .select("id, status, platform, requested_at, completed_at")
        .eq("confirmation_code", confirmation_code)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Deletion request not found")

    row = result.data[0]
    return DeletionStatusResponse(
        id=str(row["id"]),
        status=row["status"],
        platform=row["platform"],
        requested_at=str(row["requested_at"]),
        completed_at=str(row["completed_at"]) if row.get("completed_at") else None,
    )
