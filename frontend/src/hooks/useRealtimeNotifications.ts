import { useEffect, useCallback } from 'react';
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
    const supabase = createClient();

    const handleNotification = useCallback((notification: Notification) => {
        // Display toast based on notification type
        switch (notification.type) {
            case 'success':
                toast.success(notification.title, {
                    description: notification.message,
                    action: notification.link ? {
                        label: 'View',
                        onClick: () => window.location.href = notification.link!
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
                    (payload) => {
                        const notification = payload.new as Notification;
                        handleNotification(notification);
                    }
                )
                .subscribe((status) => {
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
