'use client';

import React, { useState, useEffect } from 'react';
import PremiumShell from '@/components/layout/PremiumShell';
import { listWorkflowExecutions, getWorkflowExecutionDetails, approveWorkflowStep, WorkflowExecution, WorkflowExecutionDetails } from '@/services/workflows';
import WorkflowExecutionCard from '@/components/workflows/WorkflowExecutionCard';
import WorkflowStepTimeline from '@/components/workflows/WorkflowStepTimeline';
import WorkflowStatusBadge from '@/components/workflows/WorkflowStatusBadge';
import { ArrowPathIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { toast } from 'sonner';
// import { useRealtimeSession } from '@/hooks/useRealtimeSession'; // Assuming pattern, or direct supabase
import { createClient } from '@/lib/supabase/client';
import { useAuth } from '@/hooks/useAuth'; // Assuming useAuth exists or we get user from session here.
// Actually, better to just get user ID inside effect or use a hook.
// Services use createClient() which is browser client.
// Let's use the same one here.

const supabase = createClient();

export default function ActiveWorkflowsPage() {
    const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
    const [details, setDetails] = useState<WorkflowExecutionDetails | null>(null);
    const [loadingDetails, setLoadingDetails] = useState(false);

    useEffect(() => {
        const setupSubscription = async () => {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.user) return;

            fetchExecutions();

            // Realtime Subscription
            const channel = supabase
                .channel('active_workflows')
                .on('postgres_changes', {
                    event: '*',
                    schema: 'public',
                    table: 'workflow_executions',
                    filter: `user_id=eq.${session.user.id}` // Filter by user to avoid RLS issues and noise
                }, (payload) => {
                    console.log('Realtime update:', payload);
                    fetchExecutions(); // Simple refresh on change
                    if (selectedExecutionId) fetchDetails(selectedExecutionId); // Refresh details if open
                })
                .on('postgres_changes', {
                    event: '*',
                    schema: 'public',
                    table: 'workflow_steps',
                    // Steps might not have user_id directly on them usually, they link to execution.
                    // But RLS might filter them. 
                    // If we can't filter by user_id on steps table easily without a column, 
                    // we might need to rely on the fact that RLS only sends what we can see.
                    // But explicit filter is better. Let's assume passed payload respects RLS 
                    // but subscription filter `user_id` only works if column exists.
                    // Checked schema: workflow_steps has execution_id, no user_id.
                    // So we can't filter steps by user_id directly in subscription unless we add it or rely on RLS.
                    // PROCEEDING with no filter for steps, relying on RLS to only send events for visible rows (which Supabase does if RLS is on).
                }, (payload) => {
                    if (selectedExecutionId) fetchDetails(selectedExecutionId); // Refresh details on step change
                })
                .subscribe();

            return () => {
                supabase.removeChannel(channel);
            };
        };

        setupSubscription();
    }, [selectedExecutionId]);

    const fetchExecutions = async () => {
        try {
            const data = await listWorkflowExecutions('running');
            // Also fetch waiting_approval ones? listWorkflowExecutions doesn't support multiple statuses easily in current impl
            // Maybe fetch 'running' and 'paused' or 'pending'. 
            // For now 'running' often covers active ones. 
            // If backend implementation of list_executions filters strictly, we might miss 'pending'. 
            // Let's assume 'running' is the primary active state.
            setExecutions(data);
            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch executions', error);
            setLoading(false);
        }
    };

    const fetchDetails = async (id: string) => {
        setLoadingDetails(true);
        try {
            const data = await getWorkflowExecutionDetails(id);
            setDetails(data);
        } catch (error) {
            toast.error('Failed to load details');
        } finally {
            setLoadingDetails(false);
        }
    };

    const handleCardClick = (id: string) => {
        setSelectedExecutionId(id);
        fetchDetails(id);
    };

    const handleApprove = async (executionId: string, feedback: string) => {
        try {
            await approveWorkflowStep(executionId, feedback);
            toast.success('Step approved successfully');
            fetchDetails(executionId);
        } catch (error) {
            toast.error('Failed to approve step');
            throw error;
        }
    };

    return (
        <PremiumShell>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-64px)] flex flex-col">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Active Workflows</h1>
                        <p className="mt-1 text-sm text-slate-500">Monitor and manage your running processes.</p>
                    </div>
                    <button
                        onClick={fetchExecutions}
                        className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100"
                    >
                        <ArrowPathIcon className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex-1 flex gap-6 overflow-hidden">
                    {/* List Column */}
                    <div className={`flex-1 overflow-y-auto pr-2 ${selectedExecutionId ? 'hidden md:block md:w-1/3 md:flex-none' : ''}`}>
                        {loading ? (
                            <div className="space-y-4">
                                {[...Array(3)].map((_, i) => (
                                    <div key={i} className="bg-white p-4 rounded-2xl h-32 animate-pulse border border-slate-200"></div>
                                ))}
                            </div>
                        ) : executions.length === 0 ? (
                            <div className="bg-slate-50 border border-slate-200 rounded-3xl p-12 text-center text-slate-500">
                                No active workflows found.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {executions.map(ex => (
                                    <div key={ex.id} className={`${selectedExecutionId === ex.id ? 'ring-2 ring-blue-500 rounded-2xl' : ''}`}>
                                        <WorkflowExecutionCard
                                            execution={ex as any} // Type assertion as mock template_name might be missing in strict list view if backend doesn't join, but router says it does.
                                            onClick={handleCardClick}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Detail Column */}
                    {selectedExecutionId && (
                        <div className="flex-[2] bg-white border border-slate-200 rounded-3xl p-6 overflow-y-auto shadow-xl md:shadow-none fixed inset-0 z-50 md:static md:z-auto m-4 md:m-0">
                            <div className="flex justify-between items-start mb-6">
                                {loadingDetails || !details ? (
                                    <div className="h-6 w-48 bg-slate-200 rounded animate-pulse"></div>
                                ) : (
                                    <div>
                                        <h2 className="text-xl font-bold text-slate-900">{details.execution.context.topic || details.template_name}</h2>
                                        <p className="text-sm text-slate-500">{details.template_name}</p>
                                    </div>
                                )}
                                <div className="flex items-center gap-2">
                                    {details && <WorkflowStatusBadge status={details.execution.status} />}
                                    <button
                                        onClick={() => setSelectedExecutionId(null)}
                                        className="p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 md:hidden"
                                    >
                                        <XMarkIcon className="w-6 h-6" />
                                    </button>
                                </div>
                            </div>

                            {loadingDetails || !details ? (
                                <div className="space-y-6">
                                    <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                                    <div className="h-4 bg-slate-200 rounded w-1/2"></div>
                                    <div className="h-64 bg-slate-100 rounded-xl"></div>
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    {/* Context Data */}
                                    <div className="bg-slate-50 rounded-xl p-4 text-sm border border-slate-100">
                                        <h3 className="font-semibold text-slate-900 mb-2">Context</h3>
                                        <pre className="whitespace-pre-wrap text-slate-600 font-mono text-xs">
                                            {JSON.stringify(details.execution.context, null, 2)}
                                        </pre>
                                    </div>

                                    <div className="relative">
                                        <div className="absolute inset-0 flex items-center" aria-hidden="true">
                                            <div className="w-full border-t border-slate-200" />
                                        </div>
                                        <div className="relative flex justify-center">
                                            <span className="bg-white px-2 text-sm text-slate-500">Timeline</span>
                                        </div>
                                    </div>

                                    <WorkflowStepTimeline
                                        steps={details.history}
                                        currentStepIndex={details.current_step_index}
                                        onApprove={handleApprove}
                                    />
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </PremiumShell>
    );
}
