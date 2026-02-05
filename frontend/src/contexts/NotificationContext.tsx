'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useRealtimeNotifications } from '@/hooks/useRealtimeNotifications';

interface NotificationContextType {
    unreadCount: number;
    refreshUnreadCount: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType>({
    unreadCount: 0,
    refreshUnreadCount: async () => { },
});

export function NotificationProvider({ children }: { children: React.ReactNode }) {
    const [userId, setUserId] = useState<string>();
    const [unreadCount, setUnreadCount] = useState(0);
    const supabase = createClient();

    // Get user ID
    useEffect(() => {
        const getUser = async () => {
            const { data } = await supabase.auth.getUser();
            if (data.user) setUserId(data.user.id);
        };
        getUser();
    }, [supabase]);

    // Subscribe to realtime notifications
    useRealtimeNotifications(userId);

    // Fetch unread count
    const refreshUnreadCount = async () => {
        if (!userId) return;

        const { count } = await supabase
            .from('notifications')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', userId)
            .eq('is_read', false);

        setUnreadCount(count || 0);
    };

    useEffect(() => {
        refreshUnreadCount();
    }, [userId]);

    return (
        <NotificationContext.Provider value={{ unreadCount, refreshUnreadCount }}>
            {children}
        </NotificationContext.Provider>
    );
}

export const useNotifications = () => useContext(NotificationContext);
