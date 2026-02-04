/**
 * Initiative Dashboard Widget
 * 
 * Displays business initiatives with status, progress, and action buttons.
 * Used when agent responds to requests like "Show me initiative status".
 */

import React from 'react';
import { WidgetProps } from './WidgetRegistry';
import { WidgetDefinition, InitiativeDashboardData, Initiative, InitiativeMetrics } from '@/types/widgets';
import { CheckCircle2, Clock, AlertTriangle, ArrowRight } from 'lucide-react';

// =============================================================================
// Data Types
// =============================================================================


// =============================================================================
// Helper Components
// =============================================================================

function StatusBadge({ status }: { status: Initiative['status'] }) {
    const config = {
        completed: { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300', icon: CheckCircle2 },
        in_progress: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300', icon: Clock },
        blocked: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-300', icon: AlertTriangle },
        not_started: { bg: 'bg-slate-100 dark:bg-slate-700', text: 'text-slate-600 dark:text-slate-300', icon: Clock },
    }[status];

    const Icon = config.icon;
    const label = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
            <Icon className="w-3 h-3" />
            {label}
        </span>
    );
}

function MetricCard({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div className="text-center p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
        </div>
    );
}

function ProgressBar({ progress }: { progress: number }) {
    return (
        <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
        </div>
    );
}

// =============================================================================
// Main Component
// =============================================================================

export default function InitiativeDashboard({ definition, onAction }: WidgetProps) {
    const data = definition.data as unknown as InitiativeDashboardData;

    // Provide defaults if data is incomplete
    const initiatives = data?.initiatives ?? [];
    const metrics = data?.metrics ?? {
        total: initiatives.length,
        completed: initiatives.filter(i => i.status === 'completed').length,
        in_progress: initiatives.filter(i => i.status === 'in_progress').length,
        blocked: initiatives.filter(i => i.status === 'blocked').length,
    };

    const handleInitiativeClick = (initiative: Initiative) => {
        onAction?.('view_initiative', { id: initiative.id, name: initiative.name });
    };

    const handleMarkComplete = (initiative: Initiative, e: React.MouseEvent) => {
        e.stopPropagation();
        onAction?.('mark_complete', { id: initiative.id });
    };

    return (
        <div className="space-y-4">
            {/* Metrics Summary */}
            <div className="grid grid-cols-4 gap-3">
                <MetricCard label="Total" value={metrics.total} color="text-slate-700 dark:text-slate-200" />
                <MetricCard label="Completed" value={metrics.completed} color="text-emerald-600" />
                <MetricCard label="In Progress" value={metrics.in_progress} color="text-blue-600" />
                <MetricCard label="Blocked" value={metrics.blocked} color="text-red-600" />
            </div>

            {/* Initiative List */}
            <div className="space-y-2">
                {initiatives.length === 0 ? (
                    <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">
                        No initiatives found
                    </p>
                ) : (
                    initiatives.map((initiative) => (
                        <div
                            key={initiative.id}
                            onClick={() => handleInitiativeClick(initiative)}
                            className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors border border-slate-200 dark:border-slate-700"
                        >
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <h5 className="font-medium text-slate-800 dark:text-slate-200 truncate">
                                            {initiative.name}
                                        </h5>
                                        <StatusBadge status={initiative.status} />
                                    </div>

                                    <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                                        {initiative.owner && <span>Owner: {initiative.owner}</span>}
                                        {initiative.dueDate && <span>Due: {initiative.dueDate}</span>}
                                        <span>{initiative.progress}% complete</span>
                                    </div>

                                    <div className="mt-2">
                                        <ProgressBar progress={initiative.progress} />
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    {initiative.status === 'in_progress' && (
                                        <button
                                            onClick={(e) => handleMarkComplete(initiative, e)}
                                            className="px-2 py-1 text-xs bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded hover:bg-emerald-200 dark:hover:bg-emerald-800/50 transition-colors"
                                        >
                                            Mark Complete
                                        </button>
                                    )}
                                    <ArrowRight className="w-4 h-4 text-slate-400" />
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
