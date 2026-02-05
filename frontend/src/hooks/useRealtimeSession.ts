import { useEffect, useCallback } from 'react';
import { createClient } from '@/lib/supabase/client';
import type { RealtimeChannel } from '@supabase/supabase-js';
import type { Message } from './useAgentChat';

export interface SessionEventPayload {
    id: string;
    app_name: string;
    user_id: string;
    session_id: string;
    event_data: any;
    event_index: number;
    created_at: string;
}

export interface UseRealtimeSessionOptions {
    sessionId: string;
    userId: string;
    onNewEvent?: (event: SessionEventPayload) => void;
    onEventUpdate?: (event: SessionEventPayload) => void;
}

export function useRealtimeSession({
    sessionId,
    userId,
    onNewEvent,
    onEventUpdate,
}: UseRealtimeSessionOptions) {
    const supabase = createClient();

    useEffect(() => {
        if (!sessionId || !userId) return;

        let channel: RealtimeChannel;

        const setupSubscription = async () => {
            channel = supabase
                .channel(`session:${sessionId}`)
                .on(
                    'postgres_changes',
                    {
                        event: 'INSERT',
                        schema: 'public',
                        table: 'session_events',
                        filter: `session_id=eq.${sessionId}`,
                    },
                    (payload) => {
                        const event = payload.new as SessionEventPayload;
                        onNewEvent?.(event);
                    }
                )
                .on(
                    'postgres_changes',
                    {
                        event: 'UPDATE',
                        schema: 'public',
                        table: 'session_events',
                        filter: `session_id=eq.${sessionId}`,
                    },
                    (payload) => {
                        const event = payload.new as SessionEventPayload;
                        onEventUpdate?.(event);
                    }
                )
                .subscribe((status) => {
                    if (status === 'SUBSCRIBED') {
                        console.log(`✅ Realtime session subscribed: ${sessionId}`);
                    }
                });
        };

        setupSubscription();

        return () => {
            if (channel) {
                supabase.removeChannel(channel);
            }
        };
    }, [sessionId, userId, supabase, onNewEvent, onEventUpdate]);
}
