# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Social Media Publisher.

Handles posting content (text, images, video, carousels) to connected
social media accounts with platform-specific media upload flows.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from app.social.connector import get_social_connector

if TYPE_CHECKING:
    import httpx

logger = logging.getLogger(__name__)

# Facebook Graph API version. The previous default was deprecated 2026-01-26;
# v23.0 is the current GA per Meta's API versioning schedule. Plan 107-02
# already bumped connector.py to the same constant -- do not regress.
FB_GRAPH_API_VERSION = "v23.0"


class FacebookUploadError(Exception):
    """Raised when a Facebook three-phase video upload fails irrecoverably.

    Attributes:
        phase: Which upload phase failed: 'start', 'transfer', or 'finish'.
        session_id: The ``upload_session_id`` (None if failure was in
            ``upload_phase=start`` and we never received an ID).
        status_code: HTTP status code from Meta (None if the failure was a
            network exception with no response).
    """

    def __init__(
        self,
        message: str,
        *,
        phase: str,
        session_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.session_id = session_id
        self.status_code = status_code


async def _post_chunk_with_retry(
    http: "httpx.AsyncClient",
    url: str,
    data: dict,
    files: dict | None = None,
    timeout: float = 60.0,
):
    """POST a Facebook upload phase request; retry exactly once on 5xx or network error.

    4xx responses are NOT retried -- they surface immediately so the caller
    can raise a structured ``FacebookUploadError``. The caller handles
    status-code interpretation; this helper only handles the retry loop.

    Returns the last ``httpx.Response`` (caller decides whether to raise based
    on status_code) OR re-raises the captured ``httpx.RequestError`` after the
    second network failure.
    """
    import httpx as _httpx

    last_exc: Exception | None = None
    last_resp = None
    for attempt in (1, 2):
        try:
            resp = await http.post(url, data=data, files=files, timeout=timeout)
            if resp.status_code < 500:
                return resp  # 2xx or 4xx -- return; caller decides
            # 5xx -- retry once
            last_resp = resp
            if attempt == 1:
                logger.warning(
                    "Facebook chunk POST returned %s; retrying once",
                    resp.status_code,
                )
                await asyncio.sleep(0.5)
                continue
            return resp  # second 5xx -- return so caller raises structured error
        except _httpx.RequestError as exc:
            last_exc = exc
            if attempt == 1:
                logger.warning(
                    "Facebook chunk POST raised %s; retrying once",
                    type(exc).__name__,
                )
                await asyncio.sleep(0.5)
                continue
            raise
    # Defensive: both branches above return or raise. Fall-through is unreachable.
    if last_resp is not None:
        return last_resp
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("_post_chunk_with_retry: unexpected fall-through")


async def _upload_facebook_video(
    http: "httpx.AsyncClient",
    page_id: str,
    page_access_token: str,
    video_bytes: bytes,
    description: str,
    title: str | None = None,
    api_version: str = FB_GRAPH_API_VERSION,
) -> dict[str, Any]:
    """Three-phase resumable upload of a video to a Facebook Page.

    See https://developers.facebook.com/docs/graph-api/reference/page/videos/

    Args:
        http: An open ``httpx.AsyncClient``.
        page_id: Facebook Page ID (target of the upload).
        page_access_token: A Page access token with ``pages_manage_posts`` scope.
        video_bytes: Full video file bytes (in-memory; SC-1 scope is 30s 1080p
            MP4 ~5-15 MB). Streaming-from-URL is deferred (D-7).
        description: Caption / post body.
        title: Optional video title.
        api_version: Graph API version (default ``v23.0``).

    Returns:
        ``{"video_id": str, "success": bool}``.

    Raises:
        FacebookUploadError: with ``.phase``, ``.session_id``, ``.status_code``
        on any non-recoverable failure (after the single retry, if applicable).
    """
    url = f"https://graph.facebook.com/{api_version}/{page_id}/videos"
    file_size = len(video_bytes)

    # Phase 1: start
    start_resp = await http.post(
        url,
        data={
            "upload_phase": "start",
            "access_token": page_access_token,
            "file_size": str(file_size),
        },
        timeout=60.0,
    )
    if start_resp.status_code != 200:
        raise FacebookUploadError(
            f"phase=start failed: {start_resp.text}",
            phase="start",
            status_code=start_resp.status_code,
        )
    start_body = start_resp.json()
    upload_session_id = start_body["upload_session_id"]
    video_id = start_body["video_id"]
    start_offset = int(start_body["start_offset"])
    end_offset = int(start_body["end_offset"])
    logger.info(
        "Facebook upload start: session=%s video_id=%s file_size=%d "
        "first_chunk=[%d, %d)",
        upload_session_id,
        video_id,
        file_size,
        start_offset,
        end_offset,
    )

    # Phase 2: transfer (loop until offsets converge)
    while start_offset < end_offset:
        chunk = video_bytes[start_offset:end_offset]
        transfer_resp = await _post_chunk_with_retry(
            http,
            url,
            data={
                "upload_phase": "transfer",
                "access_token": page_access_token,
                "upload_session_id": upload_session_id,
                "start_offset": str(start_offset),
            },
            files={"video_file_chunk": ("chunk", chunk, "application/octet-stream")},
            timeout=120.0,
        )
        if transfer_resp.status_code != 200:
            raise FacebookUploadError(
                f"phase=transfer failed at offset {start_offset}: {transfer_resp.text}",
                phase="transfer",
                session_id=upload_session_id,
                status_code=transfer_resp.status_code,
            )
        transfer_body = transfer_resp.json()
        start_offset = int(transfer_body["start_offset"])
        end_offset = int(transfer_body["end_offset"])
        logger.info(
            "Facebook upload chunk done: session=%s next=[%d, %d)",
            upload_session_id,
            start_offset,
            end_offset,
        )

    # Phase 3: finish
    finish_data: dict[str, Any] = {
        "upload_phase": "finish",
        "access_token": page_access_token,
        "upload_session_id": upload_session_id,
        "description": description,
    }
    if title:
        finish_data["title"] = title
    finish_resp = await http.post(url, data=finish_data, timeout=60.0)
    if finish_resp.status_code != 200:
        raise FacebookUploadError(
            f"phase=finish failed: {finish_resp.text}",
            phase="finish",
            session_id=upload_session_id,
            status_code=finish_resp.status_code,
        )
    finish_body = finish_resp.json()
    success = bool(finish_body.get("success", False))
    logger.info(
        "Facebook upload finish: session=%s video_id=%s success=%s",
        upload_session_id,
        video_id,
        success,
    )
    return {"video_id": video_id, "success": success}


# ----------------------------------------------------------------------
# YouTube resumable upload constants -- see Phase 105 RESEARCH.md
# ----------------------------------------------------------------------

YOUTUBE_RESUMABLE_INIT_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable&part=snippet,status"
)
YOUTUBE_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB, multiple of 256KB
YOUTUBE_SINGLE_PUT_THRESHOLD = 25 * 1024 * 1024  # <=25MB -> single PUT
YOUTUBE_DEFAULT_CATEGORY_ID = "22"  # People & Blogs
DEFAULT_VIDEO_MIME = "video/mp4"


def _default_remedy(code: int) -> tuple[str, bool]:
    """Fallback (remedy, retriable) for unrecognised YouTube error codes."""
    if code == 401:
        return ("re-authenticate the YouTube account", False)
    if code == 404:
        return ("upload session expired; re-initiate from step 1", True)
    if code == 429:
        return ("rate-limited; retry with backoff", True)
    if 500 <= code < 600:
        return ("transient YouTube server error; retry with backoff", True)
    if 400 <= code < 500:
        return ("non-retriable client error; fix request and retry", False)
    return ("unexpected response; retry once then escalate", True)


# Reason -> (remedy, retriable) mapping from RESEARCH.md "Error Mapping"
_YOUTUBE_REASON_MAP: dict[str, tuple[str, bool]] = {
    # 400 -- invalid metadata; non-retriable, fix-then-retry
    "invalidVideoMetadata": (
        "re-check title and categoryId before retrying",
        False,
    ),
    "invalidTitle": ("provide a non-empty video title", False),
    "invalidDescription": ("clean up the description and retry", False),
    "invalidCategoryId": (
        "use a valid YouTube category id (e.g. 22)",
        False,
    ),
    "invalidTags": ("remove problematic tags and retry", False),
    "mediaBodyRequired": (
        "internal: video bytes were not sent -- file a bug",
        False,
    ),
    # 401 -- token issue
    "authorizationRequired": (
        "re-authenticate the YouTube account",
        False,
    ),
    "youtubeSignupRequired": (
        "the connected Google account has no YouTube channel -- "
        "create one at youtube.com and reconnect",
        False,
    ),
    # 403 -- permission/quota
    "quotaExceeded": (
        "wait ~24h for daily quota reset, or request a quota "
        "increase in Google Cloud Console",
        True,
    ),
    "uploadLimitExceeded": (
        "YouTube upload limit hit; wait before retrying",
        True,
    ),
    "rateLimitExceeded": ("retry with exponential backoff", True),
    "forbiddenPrivacySetting": (
        "use 'public', 'unlisted', or 'private'",
        False,
    ),
    "forbiddenLicenseSetting": ("use a supported license value", False),
    "insufficientPermissions": (
        "re-authenticate and grant youtube.upload scope",
        False,
    ),
    "forbidden": ("re-authenticate the account", False),
    # 404 -- expired session URL
    "404": ("upload session expired; re-initiate from step 1", True),
    "notFound": ("upload session expired; re-initiate from step 1", True),
    # 5xx + 429 -- transient
    "backendError": ("retry with exponential backoff", True),
    "processingFailure": ("retry with exponential backoff", True),
}


def _map_youtube_error(
    resp: "httpx.Response",
    *,
    stage: str,
    session_url: str | None = None,
) -> dict[str, Any]:
    """Map a non-2xx YouTube response to a structured error dict.

    Extracts ``error.errors[0].reason`` and ``error.message`` from the JSON
    body when available; falls back to ``_default_remedy(status_code)`` for
    unknown reasons. Wraps JSON parsing in ``try/except Exception`` so non-
    JSON 5xx responses still yield a structured result.
    """
    code = resp.status_code
    try:
        body = resp.json()
        err = body.get("error", {}) if isinstance(body, dict) else {}
        errors_list = err.get("errors") or [{}]
        first = errors_list[0] if errors_list else {}
        reason = first.get("reason") if isinstance(first, dict) else None
        reason = reason or err.get("status") or str(code)
        message = err.get("message") or resp.text[:300]
    except Exception:
        reason = str(code)
        try:
            message = resp.text[:300]
        except Exception:
            message = f"HTTP {code}"

    remedy, retriable = _YOUTUBE_REASON_MAP.get(reason, _default_remedy(code))
    return {
        "success": False,
        "error": f"YouTube {stage} failed ({code} {reason}): {message}",
        "reason": reason,
        "retriable": retriable,
        "remedy": remedy,
        "stage": stage,
        "session_url": session_url,
    }


class SocialPublisher:
    """Publishes content to connected social media accounts."""

    def __init__(self):
        self.connector = get_social_connector()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_token_or_error(
        self, user_id: str, platform: str
    ) -> tuple[str | None, dict | None]:
        """Return (token, None) or (None, error_dict)."""
        token = await self.connector.get_access_token(user_id, platform)
        if not token:
            return None, {
                "error": f"No active connection for {platform}. "
                "Use 'get_oauth_url' to connect the account first."
            }
        return token, None

    def _get_facebook_page_context(
        self, user_id: str
    ) -> tuple[tuple[str, str] | None, dict | None]:
        """Resolve ``(page_id, page_access_token)`` for a Facebook connection.

        The Page ID is stored in ``connected_accounts.platform_user_id`` (set
        by Plan 107-02's OAuth callback augmentation). The Page access token
        is stored Fernet-encrypted in ``connected_accounts.access_token`` and
        is decrypted in-memory before being returned.

        Returns:
            ``((page_id, page_token), None)`` on success, or
            ``(None, {"error": ...})`` when the row is missing, the Page ID
            was never captured (pre-107-02 connection), or the token cannot
            be decrypted.
        """
        result = (
            self.connector.client.table("connected_accounts")
            .select("platform_user_id, access_token, status")
            .eq("user_id", user_id)
            .eq("platform", "facebook")
            .eq("status", "active")
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None, {
                "error": (
                    "No active Facebook Page connection. "
                    "Reconnect Facebook to grant Page access."
                )
            }
        row = rows[0]
        page_id = row.get("platform_user_id")
        if not page_id:
            return None, {
                "error": (
                    "Facebook connection is missing the Page ID. "
                    "Reconnect to capture Page access "
                    "(Plan 107-02 OAuth update required)."
                )
            }
        encrypted_token = row.get("access_token")
        try:
            page_token = self.connector._decrypt_token(encrypted_token)
        except Exception as exc:
            logger.warning("Facebook page token decryption failed: %s", exc)
            return None, {"error": "Failed to decrypt Facebook Page token."}
        if not page_token:
            return None, {"error": "Facebook Page token is empty after decryption."}
        return (page_id, page_token), None

    async def _upload_image_twitter(
        self, http, headers: dict, media_url: str
    ) -> str | None:
        """Simple-shot image upload to X v2 (≤5MB).

        Returns the media_id string on success, ``None`` on any failure
        (logged at WARNING). 403s are treated as a likely missing-scope
        condition and the caller surfaces a reconnect prompt.

        See Phase 104 RESEARCH.md: v1.1 ``upload.twitter.com`` was sunset
        2025-06-09. v2 ``api.x.com/2/media/upload`` (GA 2025-01-13)
        accepts a single multipart POST for files ≤5MB.
        """
        img_resp = await http.get(media_url)
        img_resp.raise_for_status()
        img_bytes = img_resp.content
        mime = (
            img_resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            or "image/jpeg"
        )

        if len(img_bytes) > 5 * 1024 * 1024:
            logger.warning(
                "Twitter image %s is %d bytes (>5MB); v2 simple upload will reject. "
                "Resize the image or use the video chunked path.",
                media_url,
                len(img_bytes),
            )
            return None

        upload_resp = await http.post(
            "https://api.x.com/2/media/upload",
            headers=headers,
            files={"media": ("upload", img_bytes, mime)},
            data={"media_category": "tweet_image"},
        )
        if upload_resp.status_code == 403:
            logger.warning(
                "Twitter media upload returned 403 -- token likely lacks "
                "media.write scope. User must reconnect. Body: %s",
                upload_resp.text,
            )
            return None
        if upload_resp.status_code not in (200, 201):
            logger.warning(
                "Twitter image upload failed (%d): %s",
                upload_resp.status_code,
                upload_resp.text,
            )
            return None

        body = upload_resp.json()
        return body.get("data", {}).get("id") or body.get("media_id_string")

    async def _upload_video_twitter(
        self, http, headers: dict, media_url: str
    ) -> str | None:
        """Chunked video upload to X v2: GET → INIT → APPEND → FINALIZE → STATUS.

        Returns the media_id string when ``processing_info.state == 'succeeded'``
        (or when FINALIZE returns no processing_info, meaning already done).
        Returns ``None`` on any failure -- structured error details are logged at
        WARNING; the caller surfaces a generic reconnect prompt.

        Honors ``processing_info.check_after_secs`` from each STATUS response;
        falls back to 2 seconds. Total wait capped at 600 seconds (deadline
        computed once before the poll loop). Sleep happens BEFORE each STATUS
        GET because the API explicitly tells us when to come back.

        Videos >100MB log a WARNING but proceed in-memory. Tempfile fallback
        is deferred per Phase 104 CONTEXT open question #2.

        See Phase 104 RESEARCH.md §"processing_info.state lifecycle":
        states transition pending → in_progress → (succeeded | failed).
        """
        # 1. Download bytes
        vid_resp = await http.get(media_url)
        vid_resp.raise_for_status()
        vid_bytes = vid_resp.content
        total_bytes = len(vid_bytes)
        mime = (
            vid_resp.headers.get("content-type", "video/mp4").split(";")[0].strip()
            or "video/mp4"
        )

        if total_bytes > 100 * 1024 * 1024:
            logger.warning(
                "Twitter video %s is %d bytes (>100MB); reading into memory. "
                "Cloud Run memory pressure may surface -- see Phase 104 CONTEXT "
                "open question #2.",
                media_url,
                total_bytes,
            )

        # 2. INIT
        init_resp = await http.post(
            "https://api.x.com/2/media/upload/initialize",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "media_type": mime,
                "total_bytes": total_bytes,
                "media_category": "tweet_video",
            },
        )
        if init_resp.status_code not in (200, 201, 202):
            logger.warning(
                "Twitter video INIT failed (%d): %s",
                init_resp.status_code,
                init_resp.text,
            )
            return None
        init_body = init_resp.json()
        media_id = init_body.get("data", {}).get("id") or init_body.get(
            "media_id_string"
        )
        if not media_id:
            logger.warning("Twitter video INIT returned no media_id: %s", init_body)
            return None

        # 3. APPEND chunks (≤4MB each, segment_index monotonic from 0)
        chunk_size = 4 * 1024 * 1024
        for i in range(0, total_bytes, chunk_size):
            chunk = vid_bytes[i : i + chunk_size]
            seg_idx = i // chunk_size
            append_resp = await http.post(
                "https://api.x.com/2/media/upload",
                headers=headers,
                data={
                    "command": "APPEND",
                    "media_id": media_id,
                    "segment_index": seg_idx,
                },
                files={"media": ("chunk", chunk, "application/octet-stream")},
            )
            if append_resp.status_code not in (200, 204):
                logger.warning(
                    "Twitter APPEND seg=%d failed (%d): %s",
                    seg_idx,
                    append_resp.status_code,
                    append_resp.text,
                )
                return None

        # 4. FINALIZE
        final_resp = await http.post(
            f"https://api.x.com/2/media/upload/{media_id}/finalize",
            headers=headers,
        )
        if final_resp.status_code not in (200, 201):
            logger.warning(
                "Twitter FINALIZE failed (%d): %s",
                final_resp.status_code,
                final_resp.text,
            )
            return None

        # 5. STATUS poll (only if FINALIZE returned processing_info)
        proc = final_resp.json().get("data", {}).get("processing_info")
        if not proc or proc.get("state") == "succeeded":
            return media_id

        deadline = asyncio.get_event_loop().time() + 600  # 10-min cap
        while proc and proc.get("state") in ("pending", "in_progress"):
            if asyncio.get_event_loop().time() > deadline:
                logger.warning(
                    "Twitter STATUS poll timed out for media_id=%s after 600s",
                    media_id,
                )
                return None
            await asyncio.sleep(proc.get("check_after_secs", 2))
            status_resp = await http.get(
                "https://api.x.com/2/media/upload",
                headers=headers,
                params={"command": "STATUS", "media_id": media_id},
            )
            if status_resp.status_code != 200:
                logger.warning(
                    "Twitter STATUS failed (%d): %s",
                    status_resp.status_code,
                    status_resp.text,
                )
                return None
            proc = status_resp.json().get("data", {}).get("processing_info")

        if proc and proc.get("state") == "failed":
            err = proc.get("error", {}) or {}
            logger.warning(
                "Twitter media processing failed for media_id=%s: code=%s message=%s",
                media_id,
                err.get("code"),
                err.get("message"),
            )
            return None
        return media_id

    # ------------------------------------------------------------------
    # TikTok helpers (Content Posting API status polling)
    # ------------------------------------------------------------------

    async def _poll_tiktok_publish_status(
        self,
        http: "httpx.AsyncClient",
        headers: dict,
        publish_id: str,
        *,
        initial_delay: float = 5.0,
        poll_interval: float = 5.0,
        max_total_seconds: float = 300.0,
    ) -> dict[str, Any]:
        """Poll TikTok ``/v2/post/publish/status/fetch/`` until terminal state.

        Cadence: ``initial_delay`` seconds before the first poll, then
        ``poll_interval`` seconds between polls. Hard-caps at
        ``max_total_seconds`` wall-clock measured from the moment the deadline
        is established (after the initial sleep). Uses ``asyncio.sleep`` so
        the event loop stays unblocked.

        Returns:
            On ``PUBLISH_COMPLETE``: ``{"success": True, "platform": "tiktok",
            "post_id": <video_id>, "video_id": <video_id>, "publish_id":
            publish_id, "media_type": "video", "message": ...}``.
            On ``FAILED``: ``{"error": "TikTok publish failed: <reason>",
            "fail_reason": <reason>, "publish_id": publish_id}``.
            On ``SEND_TO_USER_INBOX`` (unexpected on direct-post path):
            ``{"error": "TikTok saved video as draft instead of publishing",
            "fail_reason": "send_to_user_inbox", "publish_id": publish_id}``.
            On status-fetch HTTP error: ``{"error": "TikTok status fetch
            failed (<code>): <body>", "publish_id": publish_id}``.
            On 5-minute cap: ``{"error": "publish_pending -- check TikTok
            manually", "publish_id": publish_id}``.

        See Phase 106 RESEARCH.md for the TikTok status enum and
        ``fail_reason`` whitelist.
        """
        await asyncio.sleep(initial_delay)
        deadline = asyncio.get_event_loop().time() + max_total_seconds

        while asyncio.get_event_loop().time() < deadline:
            resp = await http.post(
                "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
                headers={
                    **headers,
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json={"publish_id": publish_id},
            )
            if resp.status_code != 200:
                return {
                    "error": (
                        f"TikTok status fetch failed ({resp.status_code}): {resp.text}"
                    ),
                    "publish_id": publish_id,
                }

            data = resp.json().get("data", {}) or {}
            status = data.get("status")

            if status == "PUBLISH_COMPLETE":
                # NOTE: TikTok's API field is literally
                # "publicaly_available_post_id" (one 'l' -- sic). DO NOT
                # rename to "publicly_..." -- that breaks the contract with
                # TikTok's response shape.
                ids = data.get("publicaly_available_post_id") or []
                video_id = ids[0] if ids else None
                return {
                    "success": True,
                    "platform": "tiktok",
                    "post_id": video_id or publish_id,
                    "video_id": video_id,
                    "publish_id": publish_id,
                    "media_type": "video",
                    "message": "Posted to tiktok successfully",
                }
            if status == "FAILED":
                fail_reason = data.get("fail_reason", "unknown")
                logger.warning("TikTok publish %s FAILED: %s", publish_id, fail_reason)
                return {
                    "error": f"TikTok publish failed: {fail_reason}",
                    "fail_reason": fail_reason,
                    "publish_id": publish_id,
                }
            if status == "SEND_TO_USER_INBOX":
                # Should not occur on direct-post path, but TikTok could
                # fall back when the app lacks the right scope.
                logger.warning(
                    "TikTok publish %s saved as draft instead of published",
                    publish_id,
                )
                return {
                    "error": ("TikTok saved video as draft instead of publishing"),
                    "fail_reason": "send_to_user_inbox",
                    "publish_id": publish_id,
                }
            # PROCESSING_UPLOAD / PROCESSING_DOWNLOAD / unknown -> keep polling.
            await asyncio.sleep(poll_interval)

        return {
            "error": "publish_pending -- check TikTok manually",
            "publish_id": publish_id,
        }

    # ------------------------------------------------------------------
    # LinkedIn helpers (Posts API + image/video upload flows)
    # ------------------------------------------------------------------

    async def _resolve_linkedin_author_urn(
        self,
        http: "httpx.AsyncClient",
        token: str,
        user_id: str,
    ) -> str | None:
        """Resolve ``urn:li:person:{sub}`` for a LinkedIn-connected user.

        If the connected_accounts row already has ``platform_user_id``
        (captured at OAuth callback time per POST-01), use it. Otherwise
        lazy-backfill: GET ``/v2/userinfo``, persist the ``sub``, and
        return the composed URN. On total failure, return ``None`` --
        the caller surfaces a "reconnect required" error.
        """
        result = (
            self.connector.client.table("connected_accounts")
            .select("platform_user_id")
            .eq("user_id", user_id)
            .eq("platform", "linkedin")
            .eq("status", "active")
            .execute()
        )
        rows = result.data or []
        platform_user_id: str | None = None
        if rows:
            platform_user_id = rows[0].get("platform_user_id")

        if platform_user_id:
            return f"urn:li:person:{platform_user_id}"

        # Lazy backfill -- pre-Phase-103 connections never wrote this column.
        sub, _name = await self.connector._fetch_linkedin_identity(http, token)
        if not sub:
            return None

        try:
            self.connector.client.table("connected_accounts").update(
                {"platform_user_id": sub}
            ).eq("user_id", user_id).eq("platform", "linkedin").execute()
        except Exception:
            logger.exception(
                "Failed to persist backfilled LinkedIn platform_user_id; "
                "publish will continue with the in-memory value"
            )

        return f"urn:li:person:{sub}"

    async def _upload_linkedin_image(
        self,
        http: "httpx.AsyncClient",
        api_headers: dict,
        author_urn: str,
        media_url: str,
    ) -> str | None:
        """Run /rest/images initializeUpload + PUT bytes.

        Returns the resulting ``urn:li:image:...`` URN on success, ``None``
        on any failure.
        """
        init_resp = await http.post(
            "https://api.linkedin.com/rest/images?action=initializeUpload",
            headers=api_headers,
            json={"initializeUploadRequest": {"owner": author_urn}},
        )
        if init_resp.status_code != 200:
            logger.warning(
                "LinkedIn /rest/images initializeUpload failed: %s %s",
                init_resp.status_code,
                (getattr(init_resp, "text", "") or "")[:200],
            )
            return None

        value = (init_resp.json() or {}).get("value") or {}
        upload_url = value.get("uploadUrl")
        image_urn = value.get("image")
        if not upload_url or not image_urn:
            logger.warning(
                "LinkedIn /rest/images initializeUpload returned incomplete value: %s",
                value,
            )
            return None

        # Fetch raw bytes from the public media URL (no auth -- it's the
        # caller's hosted CDN URL, not a LinkedIn-protected resource).
        media_resp = await http.get(media_url)
        if media_resp.status_code != 200:
            logger.warning(
                "Fetching LinkedIn image media bytes failed: %s",
                media_resp.status_code,
            )
            return None

        # PUT to the pre-signed URL -- MUST NOT include Authorization.
        put_resp = await http.put(
            upload_url,
            content=media_resp.content,
            headers={"Content-Type": "application/octet-stream"},
        )
        if put_resp.status_code not in (200, 201):
            logger.warning(
                "LinkedIn image PUT failed: %s %s",
                put_resp.status_code,
                (getattr(put_resp, "text", "") or "")[:200],
            )
            return None

        return image_urn

    async def _upload_linkedin_video(
        self,
        http: "httpx.AsyncClient",
        api_headers: dict,
        author_urn: str,
        media_url: str,
    ) -> str | None:
        """Run /rest/videos initializeUpload + chunked PUTs + finalizeUpload.

        Returns the resulting ``urn:li:video:...`` URN on success, ``None``
        on any failure.
        """
        # Step 1: fetch video bytes so we know the file size.
        media_resp = await http.get(media_url)
        if media_resp.status_code != 200:
            logger.warning(
                "Fetching LinkedIn video media bytes failed: %s",
                media_resp.status_code,
            )
            return None

        body = media_resp.content
        file_size = len(body)

        # Step 2: initializeUpload to get per-part uploadInstructions.
        init_resp = await http.post(
            "https://api.linkedin.com/rest/videos?action=initializeUpload",
            headers=api_headers,
            json={
                "initializeUploadRequest": {
                    "owner": author_urn,
                    "fileSizeBytes": file_size,
                    "uploadCaptions": False,
                    "uploadThumbnail": False,
                }
            },
        )
        if init_resp.status_code != 200:
            logger.warning(
                "LinkedIn /rest/videos initializeUpload failed: %s %s",
                init_resp.status_code,
                (getattr(init_resp, "text", "") or "")[:200],
            )
            return None

        value = (init_resp.json() or {}).get("value") or {}
        video_urn = value.get("video")
        upload_token = value.get("uploadToken")
        instructions = value.get("uploadInstructions") or []
        if not video_urn or not upload_token or not instructions:
            logger.warning(
                "LinkedIn /rest/videos initializeUpload returned incomplete value"
            )
            return None

        # Step 3: PUT each chunk; capture etag (or ETag) per part.
        etags: list[str] = []
        for instruction in instructions:
            url = instruction.get("uploadUrl")
            first = instruction.get("firstByte", 0)
            last = instruction.get("lastByte", file_size - 1)
            chunk = body[first : last + 1]  # LinkedIn's range is inclusive.
            put_resp = await http.put(
                url,
                content=chunk,
                headers={"Content-Type": "application/octet-stream"},
            )
            if put_resp.status_code not in (200, 201):
                logger.warning(
                    "LinkedIn video chunk PUT failed: %s %s",
                    put_resp.status_code,
                    (getattr(put_resp, "text", "") or "")[:200],
                )
                return None
            etag = put_resp.headers.get("etag") or put_resp.headers.get("ETag")
            if not etag:
                logger.warning("LinkedIn video chunk PUT did not return an etag")
                return None
            etags.append(etag)

        # Step 4: finalizeUpload with the collected part IDs.
        finalize_resp = await http.post(
            "https://api.linkedin.com/rest/videos?action=finalizeUpload",
            headers=api_headers,
            json={
                "finalizeUploadRequest": {
                    "video": video_urn,
                    "uploadToken": upload_token,
                    "uploadedPartIds": etags,
                }
            },
        )
        if finalize_resp.status_code not in (200, 201):
            logger.warning(
                "LinkedIn /rest/videos finalizeUpload failed: %s %s",
                finalize_resp.status_code,
                (getattr(finalize_resp, "text", "") or "")[:200],
            )
            return None

        return video_urn

    async def _post_linkedin(
        self,
        http: "httpx.AsyncClient",
        token: str,
        user_id: str,
        content: str,
        media_urls: list[str] | None,
        media_type: str,
    ) -> dict[str, Any]:
        """Post to LinkedIn ``/rest/posts`` (POST-02) with text/image/video.

        Returns the standard publisher envelope:
        ``{"success": True, "platform": "linkedin", "post_id": "<urn>", ...}``
        or ``{"error": "<reason>"}``.
        """
        author_urn = await self._resolve_linkedin_author_urn(http, token, user_id)
        if not author_urn:
            return {
                "error": (
                    "LinkedIn account is missing platform_user_id and the "
                    "/v2/userinfo lookup failed; reconnect the account."
                )
            }

        api_headers = {
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": "202401",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "author": author_urn,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        has_media = bool(media_urls)
        if has_media and media_type == "image":
            image_urn = await self._upload_linkedin_image(
                http, api_headers, author_urn, media_urls[0]
            )
            if not image_urn:
                return {"error": "LinkedIn image upload failed"}
            body["content"] = {
                "media": {"id": image_urn, "altText": (content or "")[:120]}
            }
        elif has_media and media_type == "video":
            video_urn = await self._upload_linkedin_video(
                http, api_headers, author_urn, media_urls[0]
            )
            if not video_urn:
                return {"error": "LinkedIn video upload failed"}
            body["content"] = {
                "media": {"id": video_urn, "title": (content or "")[:100]}
            }
        # TODO: LinkedIn carousel via /rest/documents -- out of scope POST-02.
        # carousel media_type falls through to text-only commentary for now.

        resp = await http.post(
            "https://api.linkedin.com/rest/posts",
            headers=api_headers,
            json=body,
        )
        if resp.status_code in (200, 201):
            post_urn = resp.headers.get("x-restli-id") or resp.headers.get(
                "X-RestLi-Id"
            )
            return {
                "success": True,
                "platform": "linkedin",
                "post_id": post_urn,
                "media_type": media_type,
                "message": "Posted to linkedin successfully",
            }
        return {
            "error": (
                f"LinkedIn /rest/posts failed ({resp.status_code}): "
                f"{(getattr(resp, 'text', '') or '')[:200]}"
            )
        }

    # ------------------------------------------------------------------
    # YouTube resumable upload (POST-07) -- see Phase 105 RESEARCH.md
    # ------------------------------------------------------------------

    async def _upload_video_youtube(
        self,
        http: "httpx.AsyncClient",
        token: str,
        media_url: str,
        title: str,
        description: str,
        privacy_status: str = "public",
        category_id: str = YOUTUBE_DEFAULT_CATEGORY_ID,
        mime_type: str = DEFAULT_VIDEO_MIME,
    ) -> dict[str, Any]:
        """Two-step resumable upload to YouTube Data API v3 ``videos.insert``.

        Step 1 POSTs metadata to ``YOUTUBE_RESUMABLE_INIT_URL`` and reads the
        session URL from the response ``Location`` header. Step 2 PUTs the
        video bytes (single PUT for files <=25MB, 8MB chunked PUT with 308
        Resume Incomplete handling for larger files).

        Args:
            http: An open ``httpx.AsyncClient``.
            token: Bearer access token (caller's responsibility to refresh).
            media_url: Public URL of the source video (e.g., Supabase Storage).
            title: Video title (truncated to 100 chars by YouTube anyway).
            description: Video description (truncated to 5000 chars).
            privacy_status: ``public`` | ``unlisted`` | ``private``.
            category_id: YouTube category id; ``"22"`` (People & Blogs) is
                the safest default.
            mime_type: Video MIME type, default ``video/mp4``.

        Returns:
            Success dict ``{success: True, platform, post_id, privacy_status}``
            on 201, otherwise a structured error dict from
            ``_map_youtube_error`` or one of the local error branches with
            keys ``{success, error, reason, retriable, remedy, stage}``.
        """
        import httpx as _httpx  # local: keeps module import lightweight

        # 1. Download bytes from the public media URL (full read into memory;
        #    streaming-from-disk is a follow-up if files routinely >50MB).
        try:
            async with http.stream("GET", media_url) as src:
                if src.status_code != 200:
                    return {
                        "success": False,
                        "error": (
                            f"Could not fetch media from {media_url}: "
                            f"HTTP {src.status_code}"
                        ),
                        "reason": "media_fetch_failed",
                        "retriable": True,
                        "remedy": ("verify the media URL is accessible and retry"),
                        "stage": "download",
                    }
                video_bytes = await src.aread()
        except _httpx.RequestError as exc:
            return {
                "success": False,
                "error": f"Network error fetching media: {exc}",
                "reason": "media_fetch_network",
                "retriable": True,
                "remedy": "retry now",
                "stage": "download",
            }

        total_size = len(video_bytes)

        # 2. Initiate resumable session.
        init_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime_type,
            "X-Upload-Content-Length": str(total_size),
        }
        metadata = {
            "snippet": {
                "title": (title or "")[:100],
                "description": (description or "")[:5000],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }
        try:
            init_resp = await http.post(
                YOUTUBE_RESUMABLE_INIT_URL,
                headers=init_headers,
                json=metadata,
            )
        except _httpx.RequestError as exc:
            return {
                "success": False,
                "error": f"Network error initiating YouTube upload: {exc}",
                "reason": "network_error",
                "retriable": True,
                "remedy": "retry now",
                "stage": "initiate",
            }

        if init_resp.status_code != 200:
            return _map_youtube_error(init_resp, stage="initiate")

        session_url = init_resp.headers.get("Location")
        if not session_url:
            return {
                "success": False,
                "error": "YouTube did not return a session URL",
                "reason": "missing_location_header",
                "retriable": True,
                "remedy": "retry now",
                "stage": "initiate",
            }

        # 3. PUT bytes -- single shot for small files, chunked for large.
        if total_size <= YOUTUBE_SINGLE_PUT_THRESHOLD:
            try:
                # Pitfall 2: fresh headers dict -- no leakage from init dict.
                put_resp = await http.put(
                    session_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": mime_type,
                        "Content-Length": str(total_size),
                    },
                    content=video_bytes,
                )
            except _httpx.RequestError as exc:
                return {
                    "success": False,
                    "error": f"Network error uploading to YouTube: {exc}",
                    "reason": "network_error",
                    "retriable": True,
                    "remedy": "retry now",
                    "stage": "upload",
                    "session_url": session_url,
                }

            if put_resp.status_code == 201:
                data = put_resp.json()
                return {
                    "success": True,
                    "platform": "youtube",
                    "post_id": data.get("id"),
                    "privacy_status": data.get("status", {}).get("privacyStatus"),
                }
            return _map_youtube_error(put_resp, stage="upload", session_url=session_url)

        # Chunked path (>25MB).
        return await self._put_chunked(
            http, token, session_url, video_bytes, total_size, mime_type
        )

    async def _put_chunked(
        self,
        http: "httpx.AsyncClient",
        token: str,
        session_url: str,
        video_bytes: bytes,
        total_size: int,
        mime_type: str,
    ) -> dict[str, Any]:
        """PUT bytes in 8MB chunks with 308 Resume Incomplete handling.

        Each non-final chunk is a multiple of 256KB (``YOUTUBE_CHUNK_SIZE``
        is 8MB). Intermediate ``308`` responses contain a ``Range`` header
        of the form ``bytes=0-{last_received_byte}``; we resume from
        ``last_received_byte + 1``. The terminal ``201`` carries the full
        Video resource.
        """
        import httpx as _httpx

        offset = 0
        while offset < total_size:
            end = min(offset + YOUTUBE_CHUNK_SIZE, total_size) - 1
            chunk = video_bytes[offset : end + 1]
            try:
                resp = await http.put(
                    session_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Length": str(len(chunk)),
                        "Content-Type": mime_type,
                        "Content-Range": (f"bytes {offset}-{end}/{total_size}"),
                    },
                    content=chunk,
                )
            except _httpx.RequestError as exc:
                return {
                    "success": False,
                    "error": f"Network error during chunked PUT: {exc}",
                    "reason": "network_error",
                    "retriable": True,
                    "remedy": "retry now",
                    "stage": "upload_chunk",
                    "session_url": session_url,
                }

            if resp.status_code == 201:
                data = resp.json()
                return {
                    "success": True,
                    "platform": "youtube",
                    "post_id": data.get("id"),
                    "privacy_status": data.get("status", {}).get("privacyStatus"),
                }
            if resp.status_code == 308:
                range_hdr = resp.headers.get("Range", f"bytes=0-{end}")
                try:
                    received_upper = int(range_hdr.split("-")[-1])
                    offset = received_upper + 1
                except (ValueError, IndexError):
                    offset = end + 1
                continue
            return _map_youtube_error(
                resp, stage="upload_chunk", session_url=session_url
            )

        return {
            "success": False,
            "error": "Upload finished without 201",
            "reason": "no_terminal_response",
            "retriable": True,
            "remedy": "retry now",
            "stage": "upload_chunk",
            "session_url": session_url,
        }

    # ------------------------------------------------------------------
    # Public posting methods
    # ------------------------------------------------------------------

    async def post_text(
        self,
        user_id: str,
        platform: str,
        content: str,
    ) -> dict[str, Any]:
        """Post text-only content to a connected account."""
        return await self.post_with_media(
            user_id=user_id,
            platform=platform,
            content=content,
            media_urls=None,
            media_type="text",
            extra=None,
        )

    async def post_with_media(
        self,
        user_id: str,
        platform: str,
        content: str,
        media_urls: list[str] | None = None,
        media_type: str = "image",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Post content with optional media attachments.

        Args:
            user_id: Pikar-AI user ID.
            platform: Target platform (twitter, linkedin, facebook, instagram,
                      tiktok, youtube, threads, pinterest).
            content: Caption / text body.
            media_urls: List of public URLs to images or videos. First entry is
                        primary; extras form a carousel where supported.
            media_type: One of 'text', 'image', 'video', 'carousel'.
            extra: Optional per-platform kwargs. Pinterest REQUIRES
                   ``extra={'board_id': '<board id>'}`` -- the publisher
                   short-circuits with a structured error if it is missing
                   or empty. Other platforms ignore this argument today.

        Returns:
            Dict with success/error and post details.
        """
        import httpx

        token, err = await self._get_token_or_error(user_id, platform)
        if err:
            return err

        headers = {"Authorization": f"Bearer {token}"}
        has_media = bool(media_urls)

        try:
            async with httpx.AsyncClient(timeout=60.0) as http:
                # ----- TWITTER / X -----
                if platform == "twitter":
                    tweet_payload: dict[str, Any] = {"text": content}
                    if has_media:
                        if media_type == "video":
                            media_id = await self._upload_video_twitter(
                                http, headers, media_urls[0]
                            )
                        else:
                            media_id = await self._upload_image_twitter(
                                http, headers, media_urls[0]
                            )
                        if not media_id:
                            return {
                                "error": (
                                    "Twitter media upload failed. If you "
                                    "previously connected your Twitter account, "
                                    "please reconnect to grant the new "
                                    "media.write permission."
                                )
                            }
                        tweet_payload["media"] = {"media_ids": [media_id]}
                    resp = await http.post(
                        "https://api.twitter.com/2/tweets",
                        headers={**headers, "Content-Type": "application/json"},
                        json=tweet_payload,
                    )

                # ----- LINKEDIN -----
                elif platform == "linkedin":
                    return await self._post_linkedin(
                        http, token, user_id, content, media_urls, media_type
                    )

                # ----- FACEBOOK -----
                elif platform == "facebook":
                    if has_media and media_type == "video":
                        # Plan 107-01: three-phase resumable upload to the
                        # connected Page. Resolves (page_id, page_token) from
                        # connected_accounts (populated by Plan 107-02's OAuth
                        # callback) and streams chunks via _upload_facebook_video.
                        page_ctx, ctx_err = self._get_facebook_page_context(user_id)
                        if ctx_err:
                            return ctx_err
                        page_id, page_token = page_ctx  # type: ignore[misc]

                        fetch_resp = await http.get(media_urls[0])
                        if fetch_resp.status_code != 200:
                            return {
                                "error": (
                                    f"Failed to fetch media URL "
                                    f"({fetch_resp.status_code}): "
                                    f"{media_urls[0]}"
                                )
                            }
                        video_bytes = fetch_resp.content

                        try:
                            result = await _upload_facebook_video(
                                http,
                                page_id=page_id,
                                page_access_token=page_token,
                                video_bytes=video_bytes,
                                description=content,
                            )
                        except FacebookUploadError as exc:
                            return {
                                "error": str(exc),
                                "phase": exc.phase,
                                "session_id": exc.session_id,
                                "status_code": exc.status_code,
                            }

                        return {
                            "success": True,
                            "platform": "facebook",
                            "video_id": result["video_id"],
                            "post_id": result["video_id"],
                            "media_type": media_type,
                            "message": "Posted to facebook successfully",
                        }
                    elif has_media and media_type in ("image", "carousel"):
                        # Single or first image
                        resp = await http.post(
                            f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/photos",
                            headers=headers,
                            json={
                                "message": content,
                                "url": media_urls[0],
                            },
                        )
                    else:
                        resp = await http.post(
                            f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/feed",
                            headers=headers,
                            json={"message": content},
                        )

                # ----- INSTAGRAM -----
                elif platform == "instagram":
                    if has_media and media_type == "video":
                        # Container creation for Reels
                        container_resp = await http.post(
                            f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/media",
                            headers=headers,
                            json={
                                "caption": content,
                                "media_type": "REELS",
                                "video_url": media_urls[0],
                            },
                        )
                        container_id = container_resp.json().get("id")
                        if container_id:
                            resp = await http.post(
                                f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/media_publish",
                                headers=headers,
                                json={"creation_id": container_id},
                            )
                        else:
                            return {
                                "error": f"IG container creation failed: {container_resp.text}"
                            }
                    elif has_media and media_type == "carousel" and len(media_urls) > 1:
                        # Carousel: create each child, then carousel container
                        child_ids = []
                        for url in media_urls:
                            child = await http.post(
                                f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/media",
                                headers=headers,
                                json={"image_url": url, "is_carousel_item": True},
                            )
                            cid = child.json().get("id")
                            if cid:
                                child_ids.append(cid)
                        container_resp = await http.post(
                            f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/media",
                            headers=headers,
                            json={
                                "caption": content,
                                "media_type": "CAROUSEL",
                                "children": child_ids,
                            },
                        )
                        container_id = container_resp.json().get("id")
                        if container_id:
                            resp = await http.post(
                                f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/media_publish",
                                headers=headers,
                                json={"creation_id": container_id},
                            )
                        else:
                            return {
                                "error": f"IG carousel creation failed: {container_resp.text}"
                            }
                    elif has_media:
                        # Single image
                        container_resp = await http.post(
                            f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/media",
                            headers=headers,
                            json={
                                "caption": content,
                                "image_url": media_urls[0],
                            },
                        )
                        container_id = container_resp.json().get("id")
                        if container_id:
                            resp = await http.post(
                                f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/media_publish",
                                headers=headers,
                                json={"creation_id": container_id},
                            )
                        else:
                            return {
                                "error": f"IG media creation failed: {container_resp.text}"
                            }
                    else:
                        return {
                            "error": "Instagram requires media (image or video). "
                            "Text-only posts are not supported."
                        }

                # ----- TIKTOK -----
                elif platform == "tiktok":
                    if not has_media or media_type != "video":
                        return {
                            "error": "TikTok requires video content. "
                            "Provide a video URL with media_type='video'."
                        }
                    resp = await http.post(
                        "https://open.tiktokapis.com/v2/post/publish/video/init/",
                        headers={
                            **headers,
                            "Content-Type": "application/json; charset=UTF-8",
                        },
                        json={
                            "post_info": {
                                "title": content[:150],
                                "privacy_level": "PUBLIC_TO_EVERYONE",
                                "disable_duet": False,
                                "disable_comment": False,
                                "disable_stitch": False,
                            },
                            "source_info": {
                                "source": "PULL_FROM_URL",
                                "video_url": media_urls[0],
                            },
                        },
                    )
                    # TikTok response: branch BEFORE the generic 2xx handler
                    # because publish_id is nested under data and we must poll
                    # /status/fetch/ for the real outcome (POST-08).
                    if resp.status_code in (200, 201, 202):
                        tiktok_data = resp.json().get("data", {}) or {}
                        publish_id = tiktok_data.get("publish_id")
                        if not publish_id:
                            return {
                                "error": (
                                    f"TikTok init returned no publish_id: {resp.text}"
                                )
                            }
                        return await self._poll_tiktok_publish_status(
                            http, headers, publish_id
                        )
                    # Non-2xx falls through to the generic error handler below.

                # ----- YOUTUBE -----
                elif platform == "youtube":
                    if not has_media or media_type != "video":
                        return {
                            "error": "YouTube requires video content. "
                            "Provide a video URL with media_type='video'."
                        }
                    yt_result = await self._upload_video_youtube(
                        http,
                        token,
                        media_urls[0],
                        title=content[:100],
                        description=content,
                        privacy_status="public",
                    )
                    if yt_result.get("success"):
                        return {
                            **yt_result,
                            "media_type": media_type,
                            "message": "Posted to youtube successfully",
                        }
                    # Structured error -- pass through with the original
                    # ``{success, error, reason, retriable, remedy, stage}``
                    # shape so callers can drive remediation flows.
                    return yt_result

                # ----- THREADS (HYGIENE-01) -----
                elif platform == "threads":
                    # Threads requires the platform-side user id in the
                    # path; resolve from connected_accounts. Missing id
                    # short-circuits with a structured error and zero HTTP
                    # calls so callers can prompt a reconnect.
                    threads_user_id = self.connector.get_platform_user_id(
                        user_id, platform
                    )
                    if not threads_user_id:
                        return {"error": "Threads user ID missing -- reconnect account"}

                    base = f"https://graph.threads.net/v1.0/{threads_user_id}"
                    create_body: dict[str, Any] = {
                        "access_token": token,
                        "text": content,
                    }
                    if has_media and media_type == "video":
                        create_body["media_type"] = "VIDEO"
                        create_body["video_url"] = media_urls[0]
                    elif has_media:
                        create_body["media_type"] = "IMAGE"
                        create_body["image_url"] = media_urls[0]
                    else:
                        create_body["media_type"] = "TEXT"

                    container_resp = await http.post(
                        f"{base}/threads", data=create_body
                    )
                    if container_resp.status_code not in (200, 201):
                        return {
                            "error": (
                                f"Threads container creation failed: "
                                f"{container_resp.text}"
                            )
                        }
                    creation_id = container_resp.json().get("id")
                    if not creation_id:
                        return {
                            "error": (
                                "Threads creation_id missing in container response"
                            )
                        }

                    # NOTE: Meta recommends ~30s wait for image/video
                    # processing before publishing. We do NOT sleep here:
                    # (a) 2s is too short to matter for video processing,
                    # (b) tests would need the sleep mocked, (c) most CDN-
                    # hosted media is ready by the time the create call
                    # returns. If publish fails with a "media not ready"
                    # error, surface it via the standard envelope -- the
                    # caller can retry rather than us blocking the loop.
                    resp = await http.post(
                        f"{base}/threads_publish",
                        data={
                            "creation_id": creation_id,
                            "access_token": token,
                        },
                    )

                # ----- PINTEREST -----
                elif platform == "pinterest":
                    # Pinterest requires a board_id passed via the per-platform
                    # ``extra`` kwarg. Pin creation is a single JSON POST to
                    # /v5/pins -- no chunked upload, no container step.
                    board_id = (extra or {}).get("board_id")
                    if not board_id:
                        return {
                            "error": (
                                "Pinterest requires a board_id; pass via "
                                "extra={'board_id': ...}"
                            )
                        }
                    if not has_media:
                        return {"error": "Pinterest pins require an image URL"}
                    resp = await http.post(
                        "https://api.pinterest.com/v5/pins",
                        headers={**headers, "Content-Type": "application/json"},
                        json={
                            "board_id": board_id,
                            "title": content[:100],
                            "description": content[:500],
                            "media_source": {
                                "source_type": "image_url",
                                "url": media_urls[0],
                            },
                        },
                    )
                    # Falls through to the shared 200/201/202 envelope handler
                    # below -- /v5/pins returns 201 with {"id": "<pin-id>"}.

                else:
                    return {"error": f"Posting not implemented for {platform}"}

                # ----- Response handling -----
                if resp.status_code in [200, 201, 202]:
                    resp_data = resp.json()
                    post_id = (
                        resp_data.get("id")
                        or resp_data.get("data", {}).get("id")
                        or resp_data.get("publish_id")
                    )
                    return {
                        "success": True,
                        "platform": platform,
                        "post_id": post_id,
                        "media_type": media_type,
                        "message": f"Posted to {platform} successfully",
                    }
                else:
                    return {"error": f"Post failed ({resp.status_code}): {resp.text}"}

        except Exception as e:
            logger.exception("Error posting to %s", platform)
            return {"error": str(e)}

    async def get_post_analytics(
        self,
        user_id: str,
        platform: str,
        post_id: str,
    ) -> dict[str, Any]:
        """Fetch engagement metrics for a post.

        Delegates to SocialAnalyticsService for real platform API calls.
        """
        from app.social.analytics import get_social_analytics_service

        service = get_social_analytics_service()
        return await service.get_platform_analytics(
            user_id=user_id,
            platform=platform,
            metric_type="post",
            resource_id=post_id,
        )


# Singleton
_publisher: SocialPublisher | None = None


def get_social_publisher() -> SocialPublisher:
    """Return singleton SocialPublisher instance."""
    global _publisher
    if _publisher is None:
        _publisher = SocialPublisher()
    return _publisher
