'use client';

import React, { useState, useEffect } from 'react';
import PremiumShell from '@/components/layout/PremiumShell';
import { listWorkflowExecutions, getWorkflowExecutionDetails, retryWorkflowStep, WorkflowExecution, WorkflowExecutionDetails } from '@/services/workflows';
import WorkflowExecutionCard from '@/components/workflows/WorkflowExecutionCard';
import WorkflowStepTimeline from '@/components/workflows/WorkflowStepTimeline';
import WorkflowStatusBadge from '@/components/workflows/WorkflowStatusBadge';
import { ChevronLeftIcon, ChevronRightIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { toast } from 'sonner';

export default function CompletedWorkflowsPage() {
    const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
    const [details, setDetails] = useState<WorkflowExecutionDetails | null>(null);
    const [loadingDetails, setLoadingDetails] = useState(false);

    // Pagination
    const [offset, setOffset] = useState(0);
    const limit = 20;
    const [hasMore, setHasMore] = useState(true);

    useEffect(() => {
        fetchExecutions();
    }, [offset]);

    const fetchExecutions = async () => {
        setLoading(true);
        try {
            const data = await listWorkflowExecutions('completed', limit, offset);
            setExecutions(data);
            setHasMore(data.length === limit); // Simple heuristic
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

    const handleRetryStep = async (executionId: string, stepId: string) => {
        try {
            await retryWorkflowStep(executionId, stepId);
            toast.success('Retry started');
            await fetchDetails(executionId);
            await fetchExecutions();
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
    const outcomeArtifacts = Array.isArray(outcomeSummary?.artifacts) ? outcomeSummary.artifacts : [];
    const outcomeNextActions = Array.isArray(outcomeSummary?.next_actions) ? outcomeSummary.next_actions : [];

    return (
        <PremiumShell>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-64px)] flex flex-col">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Completed Workflows</h1>
                        <p className="mt-1 text-sm text-slate-500">History of all your finished processes.</p>
                    </div>
                </div>

                <div className="flex-1 flex gap-6 overflow-hidden">
                    {/* List Column */}
                    <div className={`flex-1 overflow-y-auto pr-2 flex flex-col ${selectedExecutionId ? 'hidden md:flex md:w-1/3 md:flex-none' : ''}`}>
                        {loading ? (
                            <div className="space-y-4">
                                {[...Array(5)].map((_, i) => (
                                    <div key={i} className="bg-white p-4 rounded-2xl h-24 animate-pulse border border-slate-200"></div>
                                ))}
                            </div>
                        ) : executions.length === 0 ? (
                            <div className="bg-slate-50 border border-slate-200 rounded-3xl p-12 text-center text-slate-500 flex-1">
                                No completed workflows found.
                            </div>
                            ) : (
                            <div className="space-y-4 flex-1">
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

                        {/* Pagination Controls */}
                        <div className="pt-4 flex justify-between items-center border-t border-slate-200 mt-4">
                            <button
                                onClick={() => setOffset(Math.max(0, offset - limit))}
                                disabled={offset === 0}
                                className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-30"
                            >
                                <ChevronLeftIcon className="w-5 h-5 text-slate-600" />
                            </button>
                            <span className="text-sm text-slate-500">
                                {offset + 1}-{offset + executions.length}
                            </span>
                            <button
                                onClick={() => setOffset(offset + limit)}
                                disabled={!hasMore}
                                className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-30"
                            >
                                <ChevronRightIcon className="w-5 h-5 text-slate-600" />
                            </button>
                        </div>
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
                                    <div className="h-64 bg-slate-100 rounded-xl"></div>
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    {outcomeSummary && (
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
                                            {outcomeArtifacts.length > 0 && (
                                                <div className="mt-3">
                                                    <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-900/80">Artifacts</h4>
                                                    <ul className="mt-2 space-y-2 text-xs text-emerald-800">
                                                        {outcomeArtifacts.map((artifact, index) => (
                                                            <li key={`${artifact.type}-${artifact.label}-${index}`} className="rounded-lg border border-emerald-100 bg-white/60 px-3 py-2">
                                                                <span className="font-medium">{artifact.label}</span>
                                                                {artifact.value ? <> · {artifact.value}</> : null}
                                                                {artifact.href ? (
                                                                    <a href={artifact.href} target="_blank" rel="noreferrer" className="ml-2 text-emerald-700 underline underline-offset-2">
                                                                        Open
                                                                    </a>
                                                                ) : null}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            {outcomeNextActions.length > 0 && (
                                                <div className="mt-3">
                                                    <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-900/80">Next actions</h4>
                                                    <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-emerald-800">
                                                        {outcomeNextActions.map((action, index) => (
                                                            <li key={`${action}-${index}`}>{action}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    <div className="bg-slate-50 rounded-xl p-4 text-sm border border-slate-100">
                                        <h3 className="font-semibold text-slate-900 mb-2">Context</h3>
                                        <pre className="whitespace-pre-wrap text-slate-600 font-mono text-xs">
                                            {JSON.stringify(detailsContext, null, 2)}
                                        </pre>
                                    </div>

                                    <WorkflowStepTimeline
                                        steps={details.history}
                                        currentStepIndex={1000} // Force all completed checked
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

