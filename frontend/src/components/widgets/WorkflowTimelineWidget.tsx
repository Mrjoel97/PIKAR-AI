'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState } from 'react';
import { WidgetProps } from './WidgetRegistry';
import { fetchWithAuth } from '@/services/api';
import {
    Clock,
    CheckCircle2,
    XCircle,
    Loader2,
    AlertTriangle,
    RefreshCw,
    Link2,
    SkipForward,
    Pause,
} from 'lucide-react';

interface TimelineStep {
    id: string;
    phase_name: string;
    step_name: string;
    status: string;
    started_at: string | null;
    completed_at: string | null;
    phase_index: number;
    step_index: number;
    duration_ms: number | null;
    tool_name: string;
    error_message: string | null;
    outcome_text: string | null;
    outcome_source: 'tool' | 'llm' | 'status' | null;
}

interface TimelineData {
    execution_id: string;
    name: string;
    goal: string | null;
    status: string;
    created_at: string;
    completed_at: string | null;
    steps: TimelineStep[];
    chain_info: {
        parent_execution_id: string;
        parent_template_name: string | null;
        chain_depth: number;
    } | null;
}

const STATUS_CONFIG: Record<string, { icon: typeof Clock; color: string; bg: string; barColor: string }> = {
    completed: {
        icon: CheckCircle2,
        color: 'text-emerald-600 dark:text-emerald-400',
        bg: 'bg-emerald-50 dark:bg-emerald-900/30',
        barColor: 'bg-emerald-500',
    },
    failed: {
        icon: XCircle,
        color: 'text-red-600 dark:text-red-400',
        bg: 'bg-red-50 dark:bg-red-900/30',
        barColor: 'bg-red-500',
    },
    running: {
        icon: Loader2,
        color: 'text-blue-600 dark:text-blue-400',
        bg: 'bg-blue-50 dark:bg-blue-900/30',
        barColor: 'bg-blue-500 animate-pulse',
    },
    skipped: {
        icon: SkipForward,
        color: 'text-slate-400 dark:text-slate-500',
        bg: 'bg-slate-50 dark:bg-slate-800/50',
        barColor: 'bg-slate-300 dark:bg-slate-600',
    },
    waiting_approval: {
        icon: Pause,
        color: 'text-amber-600 dark:text-amber-400',
        bg: 'bg-amber-50 dark:bg-amber-900/30',
        barColor: 'bg-amber-500 animate-pulse',
    },
    pending: {
        icon: Clock,
        color: 'text-slate-400 dark:text-slate-500',
        bg: 'bg-slate-50 dark:bg-slate-800/50',
        barColor: 'bg-slate-300 dark:bg-slate-600',
    },
};

function getStatusConfig(status: string) {
    return STATUS_CONFIG[status] || STATUS_CONFIG.pending;
}

function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
    const mins = Math.floor(ms / 60_000);
    const secs = Math.round((ms % 60_000) / 1000);
    return `${mins}m ${secs}s`;
}

function computeDuration(step: TimelineStep): number | null {
    if (step.duration_ms) return step.duration_ms;
    if (step.started_at && step.completed_at) {
        return new Date(step.completed_at).getTime() - new Date(step.started_at).getTime();
    }
    return null;
}

export default function WorkflowTimelineWidget({ definition }: WidgetProps) {
    const executionId = (definition.data as Record<string, unknown>)?.execution_id as string | undefined;
    const [timeline, setTimeline] = useState<TimelineData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [pendingApproval, setPendingApproval] = React.useState<Set<string>>(new Set());
    const [forceExpand, setForceExpand] = React.useState(false);

    const handleApprove = async (stepId: string, decision: 'approve' | 'reject') => {
        setPendingApproval(prev => new Set(prev).add(stepId));
        try {
            await fetchWithAuth(
                `/workflows/executions/${executionId}/steps/${stepId}/${decision}`,
                { method: 'POST' },
            );
        } catch (e) {
            setPendingApproval(prev => {
                const next = new Set(prev);
                next.delete(stepId);
                return next;
            });
        }
    };

    const fetchTimeline = async () => {
        if (!executionId) {
            setError('No execution_id provided');
            setLoading(false);
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const res = await fetchWithAuth(`/workflows/executions/${executionId}/timeline`);
            const data = await res.json();
            setTimeline(data);
        } catch (err) {
            setError('Failed to load timeline');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTimeline();
    }, [executionId]);

    if (loading) {
        return (
            <div className="p-6 animate-pulse space-y-3">
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3" />
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 rounded-lg" />
                ))}
            </div>
        );
    }

    if (error || !timeline) {
        return (
            <div className="p-6 text-center text-slate-500">
                <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>{error || 'No timeline data'}</p>
                <button onClick={fetchTimeline} className="mt-2 text-sm text-indigo-500 hover:text-indigo-600">
                    Retry
                </button>
            </div>
        );
    }

    // Collapsed-strip variant for non-interactive (automated) runs
    const interactive = (definition.data as Record<string, unknown>)?.interactive !== false;
    const awaitingApproval = timeline?.steps?.some(s => s.status === 'waiting_approval') ?? false;
    const renderAsStrip = !interactive && !awaitingApproval && timeline?.status !== 'failed' && !forceExpand;

    if (renderAsStrip && timeline) {
        const total = timeline.steps.length;
        const runningIdx = timeline.steps.findIndex(s => s.status === 'running');
        const stepLabel = runningIdx >= 0
            ? `step ${runningIdx + 1} of ${total}`
            : timeline.status;
        return (
            <button
                type="button"
                data-testid="workflow-strip"
                onClick={() => setForceExpand(true)}
                className="flex w-full items-center gap-3 rounded-xl border border-slate-100 bg-white px-4 py-2 text-left text-sm hover:bg-slate-50"
            >
                <span aria-hidden="true">▶</span>
                <span className="font-medium text-slate-800">{timeline.name}</span>
                <span className="text-slate-500">• {stepLabel}</span>
            </button>
        );
    }

    // Group steps by phase
    const phases: Record<string, TimelineStep[]> = {};
    for (const step of timeline.steps) {
        const key = step.phase_name || `Phase ${step.phase_index}`;
        if (!phases[key]) phases[key] = [];
        phases[key].push(step);
    }

    // Compute max duration for bar scaling
    const allDurations = timeline.steps.map(computeDuration).filter((d): d is number => d !== null);
    const maxDuration = Math.max(...allDurations, 1);

    const overallConfig = getStatusConfig(timeline.status);
    const OverallIcon = overallConfig.icon;

    return (
        <div className="p-5 space-y-4">
            {/* Awaiting approval banner */}
            {awaitingApproval && (
                <div className="bg-amber-50 px-5 py-2 text-sm font-medium text-amber-900 border-t-2 border-amber-400">
                    ⏸ Awaiting your approval
                </div>
            )}
            {/* Header */}
            <header className="border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <OverallIcon className={`w-5 h-5 ${overallConfig.color}`} />
                        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 truncate max-w-[250px]">
                            {timeline.name || 'Workflow Timeline'}
                        </h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${overallConfig.bg} ${overallConfig.color} font-medium`}>
                            {timeline.status}
                        </span>
                    </div>
                    <button
                        onClick={fetchTimeline}
                        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                </div>
                {timeline.goal && (
                    <p className="mt-1 text-sm italic text-slate-500 dark:text-slate-400 truncate" title={timeline.goal}>
                        {timeline.goal}
                    </p>
                )}
            </header>

            {/* Chain info */}
            {timeline.chain_info && (
                <div className="flex items-center gap-1.5 text-xs text-indigo-500 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg px-3 py-1.5">
                    <Link2 className="w-3 h-3" />
                    <span>
                        Chained from <span className="font-medium">{timeline.chain_info.parent_template_name || 'parent workflow'}</span>
                        {timeline.chain_info.chain_depth > 1 && ` (depth ${timeline.chain_info.chain_depth})`}
                    </span>
                </div>
            )}

            {/* Timeline */}
            <div className="space-y-4">
                {Object.entries(phases).map(([phaseName, steps]) => (
                    <div key={phaseName}>
                        <h4 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                            {phaseName}
                        </h4>
                        <div className="space-y-1">
                            {steps.map((step) => {
                                const config = getStatusConfig(step.status);
                                const StepIcon = config.icon;
                                const duration = computeDuration(step);
                                const barWidth = duration ? Math.max(4, (duration / maxDuration) * 100) : 0;

                                return (
                                    <div
                                        key={step.id}
                                        className="group relative py-1.5 px-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                                    >
                                        {/* Main row */}
                                        <div className="flex items-center gap-2.5">
                                            {/* Status icon */}
                                            <StepIcon className={`w-3.5 h-3.5 flex-shrink-0 ${config.color} ${step.status === 'running' ? 'animate-spin' : ''}`} />

                                            {/* Step name */}
                                            <span className="text-xs text-slate-700 dark:text-slate-300 min-w-[100px] max-w-[160px] truncate">
                                                {step.step_name}
                                            </span>

                                            {/* Duration bar */}
                                            <div className="flex-1 flex items-center gap-2">
                                                <div className="flex-1 h-4 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                                    {barWidth > 0 && (
                                                        <div
                                                            className={`h-full ${config.barColor} rounded-full transition-all duration-500`}
                                                            style={{ width: `${barWidth}%` }}
                                                        />
                                                    )}
                                                </div>
                                                <span className="text-[10px] text-slate-400 dark:text-slate-500 w-12 text-right tabular-nums">
                                                    {duration ? formatDuration(duration) : '--'}
                                                </span>
                                            </div>

                                            {/* Tool name tooltip on hover */}
                                            {step.tool_name && (
                                                <span className="hidden group-hover:block absolute -top-6 left-8 text-[10px] bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 px-2 py-0.5 rounded shadow-sm whitespace-nowrap z-10">
                                                    {step.tool_name}
                                                </span>
                                            )}

                                            {/* Error tooltip on hover for failed steps */}
                                            {step.error_message && (
                                                <span className="hidden group-hover:block absolute -bottom-6 left-8 text-[10px] bg-red-800 text-white px-2 py-0.5 rounded shadow-sm whitespace-nowrap z-10 max-w-[300px] truncate">
                                                    {step.error_message}
                                                </span>
                                            )}
                                        </div>

                                        {/* Outcome text or shimmer */}
                                        {step.outcome_text ? (
                                            <p className="mt-1 text-sm text-slate-600 leading-snug">{step.outcome_text}</p>
                                        ) : step.status === 'completed' ? (
                                            <div
                                                data-testid="outcome-shimmer"
                                                className="mt-1 h-3 w-2/3 rounded bg-slate-100 animate-pulse"
                                                aria-label="Generating outcome summary..."
                                            />
                                        ) : null}

                                        {/* Inline approval buttons */}
                                        {step.status === 'waiting_approval' && (
                                            <div className="mt-2 flex items-center gap-2">
                                                <button
                                                    type="button"
                                                    disabled={pendingApproval.has(step.id)}
                                                    onClick={() => handleApprove(step.id, 'approve')}
                                                    className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                                                >
                                                    Approve
                                                </button>
                                                <button
                                                    type="button"
                                                    disabled={pendingApproval.has(step.id)}
                                                    onClick={() => handleApprove(step.id, 'reject')}
                                                    className="rounded-md bg-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-300 disabled:opacity-50"
                                                >
                                                    Reject
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            {/* Summary footer */}
            {timeline.steps.length > 0 && (
                <div className="flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <span>{timeline.steps.length} step{timeline.steps.length !== 1 ? 's' : ''}</span>
                    {allDurations.length > 0 && (
                        <span>
                            Total: {formatDuration(allDurations.reduce((a, b) => a + b, 0))}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}
