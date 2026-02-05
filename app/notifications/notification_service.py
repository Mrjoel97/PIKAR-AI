# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Notification Service for Pikar AI.

Handles creating and managing user notifications via Supabase.
Supports different notification types and real-time updates.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from enum import Enum
from supabase import Client
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TASK_UPDATE = "task_update"
    SYSTEM = "system"

class NotificationService:
    """Service for managing user notifications."""

    def __init__(self):
        try:
            self.client: Client = get_service_client()
        except Exception:
            logger.warning("Supabase credentials missing for NotificationService")
            self.client = None
        self.table_name = "notifications"

    async def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_immediately: bool = False
    ) -> Optional[dict]:
        """Create a new notification for a user.
        
        Args:
            user_id: The user to notify.
            title: Short title.
            message: Full message body.
            type: Notification type (default: info).
            link: Optional URL or path to redirect to.
            metadata: Optional extra data.
            send_immediately: If True, triggers the delivery Edge Function immediately.
            
        Returns:
            Created notification record.
        """
        if not self.client:
            return None
            
        try:
            data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": type.value,
                "link": link,
                "metadata": metadata or {},
                "is_read": False
            }
            
            response = self.client.table(self.table_name).insert(data).execute()
            if response.data:
                notification = response.data[0]
                logger.info(f"Notification sent to {user_id}: {title}")
                
                if send_immediately:
                    from app.services.edge_functions import edge_function_client
                    # Fire and forget / background task could be better, but here we await as per simple async flow
                    try:
                        await edge_function_client.send_notification(notification["id"])
                    except Exception as ef_error:
                        logger.error(f"Failed to trigger immediate notification delivery: {ef_error}")
                
                return notification
            return None
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return None

    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read."""
        if not self.client:
            return False
            
        try:
            response = (
                self.client.table(self.table_name)
                .update({"is_read": True})
                .eq("id", notification_id)
                .eq("user_id", user_id)
                .execute()
            )
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Failed to mark notification {notification_id} read: {e}")
            return False

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications for a user as read."""
        if not self.client:
            return 0
            
        try:
            response = (
                self.client.table(self.table_name)
                .update({"is_read": True})
                .eq("user_id", user_id)
                .eq("is_read", False)
                .execute()
            )
            return len(response.data)
        except Exception as e:
            logger.error(f"Failed to mark all notifications read for {user_id}: {e}")
            return 0

    async def list_notifications(
        self, 
        user_id: str, 
        limit: int = 50, 
        unread_only: bool = False
    ) -> List[dict]:
        """List notifications for a user."""
        if not self.client:
            return []
            
        try:
            query = (
                self.client.table(self.table_name)
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
            )
            
            if unread_only:
                query = query.eq("is_read", False)
                
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to list notifications for {user_id}: {e}")
            return []

# Singleton
_notification_service = None

def get_notification_service():
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
