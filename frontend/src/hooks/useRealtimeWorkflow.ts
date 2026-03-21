import { useEffect, useState, useMemo } from 'react';
import { createClient } from '@/lib/supabase/client';
import type { RealtimeChannel } from '@supabase/supabase-js';

export interface WorkflowExecution {
    id: string;
    user_id: string;
    template_id?: string;
    name: string;
    status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
    current_phase_index: number;
    current_step_index: number;
    context: Record<string, unknown>;
    created_at: string;
    updated_at: string;
    completed_at?: string;
}

export function useRealtimeWorkflow(userId: string | undefined) {
    const [workflows, setWorkflows] = useState<WorkflowExecution[]>([]);
    const supabase = useMemo(() => createClient(), []);

    useEffect(() => {
        if (!userId) return;

        let channel: RealtimeChannel;

        const setupSubscription = async () => {
            // Initial fetch
            const { data } = await supabase
                .from('workflow_executions')
                .select('*')
                .eq('user_id', userId)
                .order('created_at', { ascending: false });

            if (data) setWorkflows(data);

            // Subscribe to changes
            channel = supabase
                .channel(`workflows:${userId}`)
                .on(
                    'postgres_changes',
                    {
                        event: '*',
                        schema: 'public',
                        table: 'workflow_executions',
                        filter: `user_id=eq.${userId}`,
                    },
                    (payload: { eventType: 'INSERT' | 'UPDATE' | 'DELETE', new: any, old: any }) => {
                        if (payload.eventType === 'INSERT') {
                            setWorkflows((prev) => [payload.new as WorkflowExecution, ...prev]);
                        } else if (payload.eventType === 'UPDATE') {
                            setWorkflows((prev) =>
                                prev.map((w) => (w.id === payload.new.id ? (payload.new as WorkflowExecution) : w))
                            );
                        } else if (payload.eventType === 'DELETE') {
                            setWorkflows((prev) => prev.filter((w) => w.id !== payload.old.id));
                        }
                    }
                )
                .subscribe();
        };

        setupSubscription();

        return () => {
            if (channel) {
                supabase.removeChannel(channel);
            }
        };
    }, [userId, supabase]);

    return { workflows };
}
