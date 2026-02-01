import { useState, useEffect, useCallback } from 'react';
import { createClient } from '@/lib/supabase/client';

export type SessionSummary = {
    app_name: string;
    user_id: string;
    session_id: string;
    state: Record<string, any>;
    created_at: string;
    updated_at: string;
};

export function useSessionHistory() {
    const [sessions, setSessions] = useState<SessionSummary[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
    const supabase = createClient();

    const fetchSessions = useCallback(async () => {
        try {
            setIsLoading(true);
            const { data: { user } } = await supabase.auth.getUser();

            if (!user) {
                setSessions([]);
                return;
            }

            const { data, error } = await supabase
                .from('sessions')
                .select('*')
                .eq('user_id', user.id)
                .order('updated_at', { ascending: false });

            if (error) throw error;

            setSessions(data || []);
        } catch (err) {
            console.error('Failed to fetch sessions:', err);
            setError(err instanceof Error ? err : new Error('Unknown error'));
        } finally {
            setIsLoading(false);
        }
    }, [supabase]);

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    const deleteSession = async (sessionId: string) => {
        try {
            const { error } = await supabase
                .from('sessions')
                .delete()
                .eq('session_id', sessionId);

            if (error) throw error;

            // Optimistic update
            setSessions(prev => prev.filter(s => s.session_id !== sessionId));
        } catch (err) {
            console.error('Failed to delete session:', err);
            throw err;
        }
    };

    return {
        sessions,
        isLoading,
        error,
        refresh: fetchSessions,
        deleteSession
    };
}
