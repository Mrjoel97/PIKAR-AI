// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useEffect, useState, useMemo } from 'react';
import { createClient } from '@/lib/supabase/client';
import type { RealtimeChannel } from '@supabase/supabase-js';

export interface PresenceState {
    user_id: string;
    user_name?: string;
    online_at: string;
}

export function usePresence(roomId: string | null | undefined, userId: string, userName?: string) {
    const [presenceState, setPresenceState] = useState<Record<string, PresenceState>>({});
    const [onlineUsers, setOnlineUsers] = useState<string[]>([]);
    const supabase = useMemo(() => createClient(), []);

    useEffect(() => {
        if (!roomId || !userId || roomId.includes('undefined')) return;

        let channel: RealtimeChannel;

        const setupPresence = async () => {
            channel = supabase.channel(`presence:${roomId}`, {
                config: {
                    presence: {
                        key: userId,
                    },
                },
            });

            channel
                .on('presence', { event: 'sync' }, () => {
                    const state = channel.presenceState();
                    setPresenceState(state as unknown as Record<string, PresenceState>);

                    // Extract online user IDs
                    const users = Object.keys(state);
                    setOnlineUsers(users);
                })
                .on('presence', { event: 'join' }, ({ key, newPresences }) => {
                    console.log('User joined:', key, newPresences);
                })
                .on('presence', { event: 'leave' }, ({ key, leftPresences }) => {
                    console.log('User left:', key, leftPresences);
                })
                .subscribe(async (status) => {
                    if (status === 'SUBSCRIBED') {
                        // Track this user's presence
                        await channel.track({
                            user_id: userId,
                            user_name: userName,
                            online_at: new Date().toISOString(),
                        });
                    }
                });
        };

        setupPresence();

        return () => {
            if (channel) {
                channel.untrack();
                supabase.removeChannel(channel);
            }
        };
    }, [roomId, userId, userName, supabase]);

    return { presenceState, onlineUsers };
}
