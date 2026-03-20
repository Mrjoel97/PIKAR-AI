'use client';

import React, { useEffect, useState } from 'react';
import { WidgetProps } from './WidgetRegistry';
import { fetchWithAuth } from '@/services/api';
import {
    Activity,
    AlertTriangle,
    CheckCircle2,
    Play,
    SkipForward,
    RefreshCw,
    Zap,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DepartmentSummary {
    id: string;
    name: string;
    type: string;
    status: string;
    last_heartbeat: string | null;
    trigger_count: number;
    decision_count_24h: number;
    active_workflows: number;
    last_cycle_metrics?: Record<string, unknown> | null;
}

interface ActivityItem {
    department_id: string;
    department_name: string;
    decision_type: string;
    decision_logic: string;
    outcome: string;
    timestamp: string;
}

interface ActivityData {
    departments: DepartmentSummary[];
    activity_feed: ActivityItem[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function relativeTime(iso: string | null): string {
    if (!iso) return 'Never';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
}

function statusColor(status: string): string {
    switch (status) {
        case 'RUNNING':
            return 'bg-emerald-500';
        case 'PAUSED':
            return 'bg-amber-400';
        default:
            return 'bg-slate-400';
    }
}

function decisionIcon(type: string) {
    switch (type) {
        case 'workflow_completed':
            return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
        case 'escalated':
            return <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
        case 'workflow_launched':
            return <Play className="w-3.5 h-3.5 text-blue-500 shrink-0" />;
        case 'no_action':
        case 'trigger_skipped':
            return <SkipForward className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
        default:
            return <Activity className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
    }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DepartmentActivityWidget({ definition }: WidgetProps) {
    const [data, setData] = useState<ActivityData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchActivity = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetchWithAuth('/departments/activity');
            const json = await res.json();
            setData(json);
        } catch (err) {
            setError('Failed to load department activity');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchActivity();
    }, []);

    // ----- Loading state -----
    if (loading) {
        return (
            <div className="p-6 animate-pulse space-y-3">
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3" />
                <div className="grid grid-cols-2 gap-3">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="h-20 bg-slate-100 dark:bg-slate-800 rounded-xl" />
                    ))}
                </div>
            </div>
        );
    }

    // ----- Error state -----
    if (error || !data) {
        return (
            <div className="p-6 text-center text-slate-500">
                <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">{error || 'No data available'}</p>
                <button
                    onClick={fetchActivity}
                    className="mt-2 text-sm text-indigo-500 hover:text-indigo-600"
                >
                    Retry
                </button>
            </div>
        );
    }

    const { departments, activity_feed } = data;

    return (
        <div className="flex flex-col bg-white dark:bg-slate-900">
            {/* Header */}
            <div className="px-4 pt-4 pb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Zap className="w-5 h-5 text-indigo-500" />
                    <div>
                        <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                            {definition.title || 'Department Activity'}
                        </h3>
                        <p className="text-[11px] text-slate-500">
                            {departments.filter(d => d.status === 'RUNNING').length} of{' '}
                            {departments.length} departments active
                        </p>
                    </div>
                </div>
                <button
                    onClick={fetchActivity}
                    className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                    title="Refresh"
                >
                    <RefreshCw className="w-4 h-4 text-slate-400" />
                </button>
            </div>

            {/* Department cards */}
            <div className="grid grid-cols-2 gap-2 px-4 pb-3">
                {departments.map(dept => (
                    <div
                        key={dept.id}
                        className="rounded-xl border border-slate-100 dark:border-slate-700/60 p-3 bg-slate-50/60 dark:bg-slate-800/40"
                    >
                        {/* Name + status */}
                        <div className="flex items-center gap-1.5 mb-2">
                            <span className={`w-2 h-2 rounded-full shrink-0 ${statusColor(dept.status)}`} />
                            <span className="text-xs font-semibold text-slate-700 dark:text-slate-200 truncate">
                                {dept.name}
                            </span>
                        </div>

                        {/* Metrics */}
                        <div className="space-y-1 text-[11px] text-slate-500 dark:text-slate-400">
                            <div className="flex justify-between">
                                <span>Heartbeat</span>
                                <span className="font-medium text-slate-600 dark:text-slate-300">
                                    {relativeTime(dept.last_heartbeat)}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span>Triggers</span>
                                <span className="font-medium text-slate-600 dark:text-slate-300">
                                    {dept.trigger_count} active
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span>Decisions</span>
                                <span className="font-medium text-slate-600 dark:text-slate-300">
                                    {dept.decision_count_24h} in 24h
                                </span>
                            </div>
                            {dept.active_workflows > 0 && (
                                <div className="flex justify-between">
                                    <span>Workflows</span>
                                    <span className="font-medium text-blue-600 dark:text-blue-400">
                                        {dept.active_workflows} running
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Activity feed */}
            {activity_feed.length > 0 && (
                <div className="px-4 pb-4">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        Recent Decisions
                    </h4>
                    <div className="space-y-1.5">
                        {activity_feed.slice(0, 5).map((item, i) => (
                            <div
                                key={`${item.department_id}-${item.timestamp}-${i}`}
                                className="flex items-start gap-2 text-xs p-2 bg-slate-50/70 dark:bg-slate-800/30 rounded-lg"
                            >
                                {decisionIcon(item.decision_type)}
                                <div className="flex-1 min-w-0">
                                    <span className="font-medium text-slate-700 dark:text-slate-300">
                                        {item.department_name}
                                    </span>
                                    <p className="text-slate-500 dark:text-slate-400 truncate">
                                        {item.decision_logic}
                                    </p>
                                </div>
                                <span className="text-[10px] text-slate-400 shrink-0">
                                    {relativeTime(item.timestamp)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Empty activity */}
            {activity_feed.length === 0 && (
                <div className="px-4 pb-4 text-center">
                    <Activity className="w-5 h-5 mx-auto mb-1 text-slate-300 dark:text-slate-600" />
                    <p className="text-xs text-slate-400">
                        No decisions recorded in the last 24 hours
                    </p>
                </div>
            )}
        </div>
    );
}
