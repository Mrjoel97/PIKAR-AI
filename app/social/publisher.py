# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Social Media Publisher.

Handles posting content (text, images, video, carousels) to connected
social media accounts with platform-specific media upload flows.
"""

import logging
from typing import Dict, Any, Optional, List

from app.social.connector import get_social_connector

logger = logging.getLogger(__name__)


class SocialPublisher:
    """Publishes content to connected social media accounts."""

    def __init__(self):
        self.connector = get_social_connector()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_token_or_error(self, user_id: str, platform: str) -> tuple[Optional[str], Optional[Dict]]:
        """Return (token, None) or (None, error_dict)."""
        token = self.connector.get_access_token(user_id, platform)
        if not token:
            return None, {
                "error": f"No active connection for {platform}. "
                         "Use 'get_oauth_url' to connect the account first."
            }
        return token, None

    async def _upload_media_twitter(
        self, http, headers: dict, media_url: str, media_type: str
    ) -> Optional[str]:
        """Upload media to Twitter and return media_id."""
        # Twitter v1.1 media upload (chunked init → append → finalize)
        init_resp = await http.post(
            "https://upload.twitter.com/1.1/media/upload.json",
            headers=headers,
            data={
                "command": "INIT",
                "media_type": "video/mp4" if media_type == "video" else "image/jpeg",
                "media_category": "tweet_video" if media_type == "video" else "tweet_image",
                "source_url": media_url,
            },
        )
        if init_resp.status_code not in [200, 201, 202]:
            logger.warning("Twitter media INIT failed: %s", init_resp.text)
            return None
        return init_resp.json().get("media_id_string")

    # ------------------------------------------------------------------
    # Public posting methods
    # ------------------------------------------------------------------

    async def post_text(
        self,
        user_id: str,
        platform: str,
        content: str,
    ) -> Dict[str, Any]:
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
        media_urls: Optional[List[str]] = None,
        media_type: str = "image",
    ) -> Dict[str, Any]:
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

        token, err = self._get_token_or_error(user_id, platform)
        if err:
            return err

        headers = {"Authorization": f"Bearer {token}"}
        has_media = bool(media_urls)

        try:
            async with httpx.AsyncClient(timeout=60.0) as http:
                # ----- TWITTER / X -----
                if platform == "twitter":
                    tweet_payload: Dict[str, Any] = {"text": content}
                    if has_media:
                        media_id = await self._upload_media_twitter(
                            http, headers, media_urls[0], media_type,
                        )
                        if media_id:
                            tweet_payload["media"] = {"media_ids": [media_id]}
                    resp = await http.post(
                        "https://api.twitter.com/2/tweets",
                        headers=headers,
                        json=tweet_payload,
                    )

                # ----- LINKEDIN -----
                elif platform == "linkedin":
                    share_media_category = "NONE"
                    share_content: Dict[str, Any] = {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": share_media_category,
                    }
                    if has_media:
                        share_media_category = (
                            "VIDEO" if media_type == "video" else "IMAGE"
                        )
                        share_content["shareMediaCategory"] = share_media_category
                        share_content["media"] = [
                            {
                                "status": "READY",
                                "originalUrl": url,
                                "title": {"text": content[:100]},
                            }
                            for url in media_urls
                        ]
                    resp = await http.post(
                        "https://api.linkedin.com/v2/ugcPosts",
                        headers={
                            **headers,
                            "X-Restli-Protocol-Version": "2.0.0",
                        },
                        json={
                            "author": "urn:li:person:PERSON_ID",
                            "lifecycleState": "PUBLISHED",
                            "specificContent": {
                                "com.linkedin.ugc.ShareContent": share_content,
                            },
                            "visibility": {
                                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
                            },
                        },
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
                            return {"error": f"IG container creation failed: {container_resp.text}"}
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
                            return {"error": f"IG carousel creation failed: {container_resp.text}"}
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
                            return {"error": f"IG media creation failed: {container_resp.text}"}
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
    ) -> Dict[str, Any]:
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
_publisher: Optional[SocialPublisher] = None


def get_social_publisher() -> SocialPublisher:
    """Return singleton SocialPublisher instance."""
    global _publisher
    if _publisher is None:
        _publisher = SocialPublisher()
    return _publisher
