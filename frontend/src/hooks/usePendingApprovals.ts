import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchWithAuthRaw } from '@/services/api';
import { createClient } from '@/lib/supabase/client';

export interface PendingApproval {
    id: string;
    action_type: string;
    created_at: string;
    token: string | null;
}

const POLL_INTERVAL_MS = 30_000;

/**
 * Hook to fetch and poll pending approval requests for the current user.
 * Returns the count, list, loading state, and a manual refresh function.
 * No-ops gracefully if the user is not logged in.
 */
export function usePendingApprovals() {
    const [approvals, setApprovals] = useState<PendingApproval[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const mountedRef = useRef(true);
    const supabase = createClient();

    const fetchPending = useCallback(async () => {
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) {
                // Not logged in — silently clear
                setApprovals([]);
                return;
            }

            setIsLoading(true);
            const response = await fetchWithAuthRaw('/approvals/pending/list');
            if (!response.ok) {
                // Non-critical — don't throw, just clear
                setApprovals([]);
                return;
            }

            const data: PendingApproval[] = await response.json();
            if (mountedRef.current) {
                setApprovals(data);
                setError(null);
            }
        } catch (err) {
            if (mountedRef.current) {
                setError(err instanceof Error ? err : new Error('Failed to fetch approvals'));
                setApprovals([]);
            }
        } finally {
            if (mountedRef.current) {
                setIsLoading(false);
            }
        }
    }, [supabase]);

    useEffect(() => {
        mountedRef.current = true;
        fetchPending();

        const interval = setInterval(fetchPending, POLL_INTERVAL_MS);

        return () => {
            mountedRef.current = false;
            clearInterval(interval);
        };
    }, [fetchPending]);

    return {
        count: approvals.length,
        approvals,
        isLoading,
        error,
        refresh: fetchPending,
    };
}
