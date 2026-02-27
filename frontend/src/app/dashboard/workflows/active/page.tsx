'use client';

import React, { useState, useEffect } from 'react';
import PremiumShell from '@/components/layout/PremiumShell';
import {
    listWorkflowExecutions,
    getWorkflowExecutionDetails,
    approveWorkflowStep,
    cancelWorkflowExecution,
    retryWorkflowStep,
    subscribeWorkflowExecutionEvents,
    WorkflowExecution,
    WorkflowExecutionDetails
} from '@/services/workflows';
import WorkflowExecutionCard from '@/components/workflows/WorkflowExecutionCard';
import WorkflowStepTimeline from '@/components/workflows/WorkflowStepTimeline';
import WorkflowStatusBadge from '@/components/workflows/WorkflowStatusBadge';
import { ArrowPathIcon, XMarkIcon, PlusIcon } from '@heroicons/react/24/outline';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

export default function ActiveWorkflowsPage() {
    const router = useRouter();
    const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
    const [details, setDetails] = useState<WorkflowExecutionDetails | null>(null);
    const [loadingDetails, setLoadingDetails] = useState(false);

    useEffect(() => {
        fetchExecutions();
    }, []);

    useEffect(() => {
        if (!selectedExecutionId) return;
        let cleanup: (() => void) | null = null;
        let pollInterval: ReturnType<typeof setInterval> | null = null;
        let closed = false;

        const startPollingFallback = () => {
            if (pollInterval) return;
            pollInterval = setInterval(() => {
                if (!closed && selectedExecutionId) {
                    fetchDetails(selectedExecutionId);
                }
            }, 5000);
        };

        (async () => {
            try {
                cleanup = await subscribeWorkflowExecutionEvents(selectedExecutionId, {
                    onStatus: (payload) => {
                        setDetails(payload);
                        setExecutions((prev) => prev.map((ex) => (ex.id === payload.execution.id ? payload.execution : ex)));
                        if (payload.execution.status === 'completed' || payload.execution.status === 'failed' || payload.execution.status === 'cancelled') {
                            if (cleanup) cleanup();
                            cleanup = null;
                            startPollingFallback();
                        }
                    },
                    onError: () => {
                        startPollingFallback();
                    },
                });
            } catch {
                startPollingFallback();
            }
        })();

        return () => {
            closed = true;
            if (cleanup) cleanup();
            if (pollInterval) clearInterval(pollInterval);
        };
    }, [selectedExecutionId]);

    const fetchExecutions = async () => {
        try {
            const [running, waitingApproval, pending] = await Promise.all([
                listWorkflowExecutions('running'),
                listWorkflowExecutions('waiting_approval'),
                listWorkflowExecutions('pending'),
            ]);
            const merged = [...running, ...waitingApproval, ...pending];
            const deduped = Array.from(new Map(merged.map((item) => [item.id, item])).values());
            setExecutions(deduped);
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

    const handleCancel = async (executionId: string) => {
        try {
            await cancelWorkflowExecution(executionId, 'Cancelled from run console');
            toast.success('Execution cancelled');
            await fetchExecutions();
            await fetchDetails(executionId);
        } catch (error) {
            toast.error('Failed to cancel execution');
        }
    };

    const handleRetryStep = async (executionId: string, stepId: string) => {
        try {
            await retryWorkflowStep(executionId, stepId);
            toast.success('Retry started');
            await fetchDetails(executionId);
        } catch (error) {
            toast.error('Failed to retry step');
            throw error;
        }
    };

    const detailsContext = details?.execution?.context ?? {};
    const detailsTopic = typeof detailsContext.topic === 'string' ? detailsContext.topic : '';
    const outcomeSummary = details?.execution?.outcome_summary ?? null;
    const outcomeSummaryText = typeof outcomeSummary?.summary === 'string' ? outcomeSummary.summary : '';
    const outcomeToolsUsed = Array.isArray(outcomeSummary?.tools_used) ? outcomeSummary.tools_used : [];
    const outcomeStepsCompleted = typeof outcomeSummary?.steps_completed === 'number' ? outcomeSummary.steps_completed : null;

    return (
        <PremiumShell>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-64px)] flex flex-col">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Active Workflows</h1>
                        <p className="mt-1 text-sm text-slate-500">Monitor and manage your running processes.</p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => router.push('/dashboard/workflows/templates')}
                            className="inline-flex items-center px-4 py-2 bg-slate-900 border border-transparent rounded-xl font-semibold text-xs text-white uppercase tracking-widest hover:bg-slate-700 active:bg-slate-900 focus:outline-none focus:border-slate-900 focus:ring ring-slate-300 disabled:opacity-25 transition ease-in-out duration-150"
                        >
                            <PlusIcon className="w-5 h-5 mr-2" />
                            New Workflow
                        </button>
                        <button
                            onClick={fetchExecutions}
                            className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100"
                        >
                            <ArrowPathIcon className="w-5 h-5" />
                        </button>
                    </div>
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
                                            execution={ex as unknown as Parameters<typeof WorkflowExecutionCard>[0]['execution']}
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
                                        <h2 className="text-xl font-bold text-slate-900">{detailsTopic || details.template_name}</h2>
                                        <p className="text-sm text-slate-500">{details.template_name}</p>
                                    </div>
                                )}
                                <div className="flex items-center gap-2">
                                    {details && <WorkflowStatusBadge status={details.execution.status} />}
                                    {details && !['completed', 'failed', 'cancelled'].includes(details.execution.status) && (
                                        <button
                                            onClick={() => handleCancel(details.execution.id)}
                                            className="px-3 py-1.5 text-xs rounded-lg bg-red-600 text-white hover:bg-red-700"
                                        >
                                            Cancel Run
                                        </button>
                                    )}
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
                                    {details.execution.status === 'completed' && outcomeSummary && (
                                        <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 text-sm">
                                            <h3 className="font-semibold text-emerald-900 mb-2">Outcome summary</h3>
                                            <p className="text-emerald-800 whitespace-pre-wrap mb-2">
                                                {outcomeSummaryText}
                                            </p>
                                            {outcomeToolsUsed.length > 0 && (
                                                <p className="text-emerald-700 text-xs">
                                                    Tools: {outcomeToolsUsed.join(', ')}
                                                    {outcomeStepsCompleted != null && (
                                                        <> · {outcomeStepsCompleted} step(s) completed</>
                                                    )}
                                                </p>
                                            )}
                                        </div>
                                    )}
                                    {/* Context Data */}
                                    <div className="bg-slate-50 rounded-xl p-4 text-sm border border-slate-100">
                                        <h3 className="font-semibold text-slate-900 mb-2">Context</h3>
                                        <pre className="whitespace-pre-wrap text-slate-600 font-mono text-xs">
                                            {JSON.stringify(detailsContext, null, 2)}
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
                                        onRetryStep={handleRetryStep}
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
