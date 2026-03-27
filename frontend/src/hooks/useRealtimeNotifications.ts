// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useEffect, useCallback, useMemo } from 'react';
import { createClient } from '@/lib/supabase/client';
import { toast } from 'sonner';
import type { RealtimeChannel } from '@supabase/supabase-js';

export type NotificationType = 'info' | 'success' | 'warning' | 'error' | 'task_update' | 'system';

export interface Notification {
    id: string;
    user_id: string;
    title: string;
    message: string;
    type: NotificationType;
    link?: string;
    is_read: boolean;
    created_at: string;
    metadata?: Record<string, unknown>;
}

export function useRealtimeNotifications(userId: string | undefined) {
    const supabase = useMemo(() => createClient(), []);

    const handleNotification = useCallback((notification: Notification) => {
        // Display toast based on notification type
        switch (notification.type) {
            case 'success':
                toast.success(notification.title, {
                    description: notification.message,
                    action: notification.link ? {
                        label: 'View',
                        onClick: () => {
                            const link = notification.link!;
                            // Only allow relative paths or same-origin URLs
                            if (link.startsWith('/')) {
                                window.location.href = link;
                            } else {
                                try {
                                    const url = new URL(link, window.location.origin);
                                    if (url.origin === window.location.origin) {
                                        window.location.href = link;
                                    }
                                } catch {
                                    // Invalid URL, ignore
                                }
                            }
                        }
                    } : undefined,
                });
                break;
            case 'error':
                toast.error(notification.title, {
                    description: notification.message,
                });
                break;
            case 'warning':
                toast.warning(notification.title, {
                    description: notification.message,
                });
                break;
            case 'task_update':
                toast.info(notification.title, {
                    description: notification.message,
                    icon: '📋',
                });
                break;
            default:
                toast(notification.title, {
                    description: notification.message,
                });
        }
    }, []);

    useEffect(() => {
        if (!userId) return;

        let channel: RealtimeChannel;

        const setupSubscription = async () => {
            channel = supabase
                .channel(`notifications:${userId}`)
                .on(
                    'postgres_changes',
                    {
                        event: 'INSERT',
                        schema: 'public',
                        table: 'notifications',
                        filter: `user_id=eq.${userId}`,
                    },
                    (payload: { new: Notification }) => {
                        const notification = payload.new as Notification;
                        handleNotification(notification);
                    }
                )
                .subscribe((status: string) => {
                    if (status === 'SUBSCRIBED') {
                        console.log('✅ Realtime notifications subscribed');
                    }
                });
        };

        setupSubscription();

        return () => {
            if (channel) {
                supabase.removeChannel(channel);
            }
        };
    }, [userId, supabase, handleNotification]);
}
