'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState } from 'react';
import { WidgetProps } from './WidgetRegistry';
import { fetchWithAuth } from '@/services/api';
import {
    Activity,
    CheckCircle2,
    XCircle,
    Clock,
    AlertTriangle,
    TrendingUp,
    BarChart3,
    RefreshCw,
} from 'lucide-react';
import PersonaEmptyState from './PersonaEmptyState';

interface ExecutionStats {
    total: number;
    completed: number;
    failed: number;
    running: number;
    cancelled: number;
    success_rate: number;
    failure_rate: number;
    top_failing_tools: Array<{ tool: string; count: number }>;
    recent_failures: Array<{ id: string; name: string; created_at: string }>;
    status_breakdown: Record<string, number>;
    duration?: {
        avg_ms: number;
        p95_ms: number;
        slowest_tools: Array<{ tool: string; avg_ms: number; count: number }>;
    };
}

export default function WorkflowObservabilityWidget({ definition }: WidgetProps) {
    const [stats, setStats] = useState<ExecutionStats | null>(
        (definition.data as unknown as ExecutionStats)?.total !== undefined
            ? (definition.data as unknown as ExecutionStats)
            : null
    );
    const [loading, setLoading] = useState(!stats);
    const [error, setError] = useState<string | null>(null);

    const fetchStats = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetchWithAuth('/workflows/executions/stats');
            const data = await res.json();
            setStats(data);
        } catch (err) {
            setError('Failed to load workflow stats');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!stats) {
            fetchStats();
        }
    }, []);

    if (loading) {
        return (
            <div className="p-6 animate-pulse space-y-4">
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3" />
                <div className="grid grid-cols-4 gap-3">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="h-16 bg-slate-100 dark:bg-slate-800 rounded-xl" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6 text-center text-slate-500">
                <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>{error}</p>
                <button
                    onClick={fetchStats}
                    className="mt-2 text-sm text-indigo-500 hover:text-indigo-600"
                >
                    Retry
                </button>
            </div>
        );
    }

    if (!stats || stats.total === 0) {
        return <PersonaEmptyState widgetType="workflow_observability" />;
    }

    const statCards = [
        {
            label: 'Running',
            value: stats.running,
            icon: Activity,
            color: 'text-blue-600 dark:text-blue-400',
            bg: 'bg-blue-50 dark:bg-blue-900/30',
        },
        {
            label: 'Completed',
            value: stats.completed,
            icon: CheckCircle2,
            color: 'text-emerald-600 dark:text-emerald-400',
            bg: 'bg-emerald-50 dark:bg-emerald-900/30',
        },
        {
            label: 'Failed',
            value: stats.failed,
            icon: XCircle,
            color: 'text-red-600 dark:text-red-400',
            bg: 'bg-red-50 dark:bg-red-900/30',
        },
        {
            label: 'Cancelled',
            value: stats.cancelled,
            icon: Clock,
            color: 'text-slate-600 dark:text-slate-400',
            bg: 'bg-slate-50 dark:bg-slate-800/50',
        },
    ];

    return (
        <div className="flex flex-col h-full bg-white dark:bg-slate-900">
            {/* Header */}
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-indigo-500" />
                    <div>
                        <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                            Pipeline Health
                        </h3>
                        <p className="text-xs text-slate-500">
                            {stats.total} total executions
                        </p>
                    </div>
                </div>
                <button
                    onClick={fetchStats}
                    className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                    title="Refresh"
                >
                    <RefreshCw className="w-4 h-4 text-slate-400" />
                </button>
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-4 gap-3 p-4">
                {statCards.map(card => (
                    <div
                        key={card.label}
                        className={`${card.bg} rounded-xl p-3 text-center`}
                    >
                        <card.icon className={`w-5 h-5 mx-auto mb-1 ${card.color}`} />
                        <div className={`text-xl font-bold ${card.color}`}>
                            {card.value}
                        </div>
                        <div className="text-[10px] uppercase tracking-wider text-slate-500 mt-0.5">
                            {card.label}
                        </div>
                    </div>
                ))}
            </div>

            {/* Success / Failure Rate */}
            <div className="px-4 pb-3">
                <div className="flex items-center gap-4">
                    <div className="flex-1">
                        <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-slate-500">Success Rate</span>
                            <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                                {stats.success_rate}%
                            </span>
                        </div>
                        <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-emerald-500 rounded-full transition-all"
                                style={{ width: `${stats.success_rate}%` }}
                            />
                        </div>
                    </div>
                    <div className="flex-1">
                        <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-slate-500">Failure Rate</span>
                            <span className="font-semibold text-red-600 dark:text-red-400">
                                {stats.failure_rate}%
                            </span>
                        </div>
                        <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-red-500 rounded-full transition-all"
                                style={{ width: `${stats.failure_rate}%` }}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Duration Metrics */}
            {stats.duration && stats.duration.avg_ms > 0 && (
                <div className="px-4 pb-3">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        Step Performance
                    </h4>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="text-center p-2 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                            <div className="text-lg font-bold text-slate-700 dark:text-slate-200">
                                {stats.duration.avg_ms < 1000
                                    ? `${stats.duration.avg_ms}ms`
                                    : `${(stats.duration.avg_ms / 1000).toFixed(1)}s`}
                            </div>
                            <div className="text-[10px] uppercase tracking-wider text-slate-500">Avg Duration</div>
                        </div>
                        <div className="text-center p-2 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                            <div className="text-lg font-bold text-slate-700 dark:text-slate-200">
                                {stats.duration.p95_ms < 1000
                                    ? `${stats.duration.p95_ms}ms`
                                    : `${(stats.duration.p95_ms / 1000).toFixed(1)}s`}
                            </div>
                            <div className="text-[10px] uppercase tracking-wider text-slate-500">P95 Duration</div>
                        </div>
                    </div>
                    {stats.duration.slowest_tools.length > 0 && (
                        <div className="mt-2 space-y-1">
                            {stats.duration.slowest_tools.slice(0, 3).map(item => (
                                <div
                                    key={item.tool}
                                    className="flex items-center justify-between text-xs"
                                >
                                    <span className="text-slate-600 dark:text-slate-400 font-mono truncate">
                                        {item.tool}
                                    </span>
                                    <span className="text-amber-600 dark:text-amber-400 font-semibold ml-2 shrink-0">
                                        {item.avg_ms < 1000 ? `${item.avg_ms}ms` : `${(item.avg_ms / 1000).toFixed(1)}s`} avg
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Top Failing Tools */}
            {stats.top_failing_tools.length > 0 && (
                <div className="px-4 pb-3">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        Top Failing Tools
                    </h4>
                    <div className="space-y-1.5">
                        {stats.top_failing_tools.slice(0, 5).map(item => (
                            <div
                                key={item.tool}
                                className="flex items-center justify-between text-sm"
                            >
                                <span className="text-slate-700 dark:text-slate-300 font-mono text-xs truncate">
                                    {item.tool}
                                </span>
                                <span className="text-red-500 font-semibold text-xs ml-2 shrink-0">
                                    {item.count} failure{item.count !== 1 ? 's' : ''}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Recent Failures */}
            {stats.recent_failures.length > 0 && (
                <div className="px-4 pb-4">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        Recent Failures
                    </h4>
                    <div className="space-y-1.5">
                        {stats.recent_failures.map(f => (
                            <div
                                key={f.id}
                                className="flex items-center gap-2 text-xs p-2 bg-red-50/50 dark:bg-red-900/10 rounded-lg"
                            >
                                <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                                <span className="text-slate-700 dark:text-slate-300 truncate flex-1">
                                    {f.name || f.id.slice(0, 8)}
                                </span>
                                <span className="text-slate-400 shrink-0">
                                    {f.created_at ? new Date(f.created_at).toLocaleDateString() : ''}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Empty state for no failures */}
            {stats.failed === 0 && stats.total > 0 && (
                <div className="px-4 pb-4 text-center">
                    <TrendingUp className="w-6 h-6 mx-auto mb-1 text-emerald-400" />
                    <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                        All workflows running clean — no failures detected
                    </p>
                </div>
            )}
        </div>
    );
}
