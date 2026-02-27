# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Social Media Publisher.

Handles posting content to connected social media accounts.
"""

from typing import Dict, Any, Optional, List

from app.social.connector import get_social_connector

class SocialPublisher:
    """Publishes content to connected social media accounts."""
    
    def __init__(self):
        self.connector = get_social_connector()

    async def post_text(
        self,
        user_id: str,
        platform: str,
        content: str
    ) -> Dict[str, Any]:
        """Post text content to a connected account.
        
        Args:
            user_id: Pikar-AI user ID
            platform: Target platform
            content: Text content to post
            
        Returns:
            Dict with post result
        """
        import httpx
        
        # Get access token
        token = self.connector.get_access_token(user_id, platform)
        if not token:
            return {"error": f"No active connection for {platform}"}
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with httpx.AsyncClient() as http:
                if platform == "twitter":
                    resp = await http.post(
                        "https://api.twitter.com/2/tweets",
                        headers=headers,
                        json={"text": content}
                    )
                elif platform == "linkedin":
                    # LinkedIn requires author URN
                    # This is simplified - real impl needs user's LinkedIn ID
                    resp = await http.post(
                        "https://api.linkedin.com/v2/ugcPosts",
                        headers={**headers, "X-Restli-Protocol-Version": "2.0.0"},
                        json={
                            "author": "urn:li:person:PERSON_ID",  # Needs real ID
                            "lifecycleState": "PUBLISHED",
                            "specificContent": {
                                "com.linkedin.ugc.ShareContent": {
                                    "shareCommentary": {"text": content},
                                    "shareMediaCategory": "NONE"
                                }
                            },
                            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
                        }
                    )
                elif platform == "facebook":
                    # Requires page_id from metadata
                    resp = await http.post(
                        "https://graph.facebook.com/v18.0/me/feed",
                        headers=headers,
                        json={"message": content}
                    )
                elif platform == "tiktok":
                    # TikTok Content Posting API
                    # Note: TikTok primarily supports video content
                    # For text-based content, we create a simple caption
                    resp = await http.post(
                        "https://open.tiktokapis.com/v2/post/publish/content/init/",
                        headers={
                            **headers,
                            "Content-Type": "application/json; charset=UTF-8"
                        },
                        json={
                            "post_info": {
                                "title": content[:150],  # TikTok title limit
                                "privacy_level": "PUBLIC_TO_EVERYONE",
                                "disable_duet": False,
                                "disable_comment": False,
                                "disable_stitch": False
                            },
                            "source_info": {
                                "source": "PULL_FROM_URL",
                                "video_url": ""  # Would need video URL for actual posting
                            }
                        }
                    )
                elif platform == "instagram":
                    # Instagram Graph API for business accounts
                    # Requires media container creation first
                    resp = await http.post(
                        "https://graph.facebook.com/v18.0/me/media",
                        headers=headers,
                        json={
                            "caption": content,
                            "media_type": "TEXT"  # For text-only stories
                        }
                    )
                else:
                    return {"error": f"Posting not implemented for {platform}"}
                
                if resp.status_code in [200, 201]:
                    return {
                        "success": True,
                        "platform": platform,
                        "post_id": resp.json().get("id") or resp.json().get("data", {}).get("id"),
                        "message": f"Posted to {platform} successfully"
                    }
                else:
                    return {"error": f"Post failed: {resp.text}"}
                    
        except Exception as e:
            return {"error": str(e)}

    async def post_with_media(
        self,
        user_id: str,
        platform: str,
        content: str,
        media_urls: List[str]
    ) -> Dict[str, Any]:
        """Post content with media attachments.
        
        Note: This is a placeholder - media posting requires platform-specific
        upload flows (e.g., Twitter media upload, Facebook photo upload).
        """
        # For MVP, we'll fall back to text-only
        return await self.post_text(user_id, platform, content)

    def get_post_analytics(
        self,
        user_id: str,
        platform: str,
        post_id: str
    ) -> Dict[str, Any]:
        """Fetch engagement metrics for a post.
        
        Note: This requires platform-specific API calls.
        """
        return {
            "platform": platform,
            "post_id": post_id,
            "note": "Analytics not yet implemented"
        }


# Singleton
_publisher: Optional[SocialPublisher] = None

def get_social_publisher() -> SocialPublisher:
    global _publisher
    if _publisher is None:
        _publisher = SocialPublisher()
    return _publisher
