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
        )

    async def post_with_media(
        self,
        user_id: str,
        platform: str,
        content: str,
        media_urls: list[str] | None = None,
        media_type: str = "image",
    ) -> dict[str, Any]:
        """Post content with optional media attachments.

        Args:
            user_id: Pikar-AI user ID.
            platform: Target platform (twitter, linkedin, facebook, instagram,
                      tiktok, youtube).
            content: Caption / text body.
            media_urls: List of public URLs to images or videos. First entry is
                        primary; extras form a carousel where supported.
            media_type: One of 'text', 'image', 'video', 'carousel'.

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
                        resp = await http.post(
                            "https://graph.facebook.com/v18.0/me/videos",
                            headers=headers,
                            json={
                                "description": content,
                                "file_url": media_urls[0],
                            },
                        )
                    elif has_media and media_type in ("image", "carousel"):
                        # Single or first image
                        resp = await http.post(
                            "https://graph.facebook.com/v18.0/me/photos",
                            headers=headers,
                            json={
                                "message": content,
                                "url": media_urls[0],
                            },
                        )
                    else:
                        resp = await http.post(
                            "https://graph.facebook.com/v18.0/me/feed",
                            headers=headers,
                            json={"message": content},
                        )

                # ----- INSTAGRAM -----
                elif platform == "instagram":
                    if has_media and media_type == "video":
                        # Container creation for Reels
                        container_resp = await http.post(
                            "https://graph.facebook.com/v18.0/me/media",
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
                                "https://graph.facebook.com/v18.0/me/media_publish",
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
                                "https://graph.facebook.com/v18.0/me/media",
                                headers=headers,
                                json={"image_url": url, "is_carousel_item": True},
                            )
                            cid = child.json().get("id")
                            if cid:
                                child_ids.append(cid)
                        container_resp = await http.post(
                            "https://graph.facebook.com/v18.0/me/media",
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
                                "https://graph.facebook.com/v18.0/me/media_publish",
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
                            "https://graph.facebook.com/v18.0/me/media",
                            headers=headers,
                            json={
                                "caption": content,
                                "image_url": media_urls[0],
                            },
                        )
                        container_id = container_resp.json().get("id")
                        if container_id:
                            resp = await http.post(
                                "https://graph.facebook.com/v18.0/me/media_publish",
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
                        "https://open.tiktokapis.com/v2/post/publish/content/init/",
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

                # ----- YOUTUBE -----
                elif platform == "youtube":
                    if not has_media or media_type != "video":
                        return {
                            "error": "YouTube requires video content. "
                            "Provide a video URL with media_type='video'."
                        }
                    resp = await http.post(
                        "https://www.googleapis.com/upload/youtube/v3/videos"
                        "?part=snippet,status",
                        headers=headers,
                        json={
                            "snippet": {
                                "title": content[:100],
                                "description": content,
                            },
                            "status": {"privacyStatus": "public"},
                            "source_url": media_urls[0],
                        },
                    )

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
