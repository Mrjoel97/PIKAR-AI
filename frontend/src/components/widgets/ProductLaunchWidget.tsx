// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { WidgetProps } from './WidgetRegistry';
import { WidgetDefinition, ProductLaunchData, Milestone } from '@/types/widgets';
import { CheckCircle2, AlertTriangle, XCircle, Clock, Calendar } from 'lucide-react';

// =============================================================================
// Interfaces
// =============================================================================


// =============================================================================
// Helper Components
// =============================================================================

function MilestoneStatusBadge({ status }: { status: Milestone['status'] }) {
    switch (status) {
        case 'completed':
            return (
                <span className="px-2 py-1 text-xs font-medium text-emerald-700 bg-emerald-100 dark:text-emerald-300 dark:bg-emerald-900/30 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    Completed
                </span>
            );
        case 'in_progress':
            return (
                <span className="px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 dark:text-blue-300 dark:bg-blue-900/30 rounded-full flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    In Progress
                </span>
            );
        case 'delayed':
            return (
                <span className="px-2 py-1 text-xs font-medium text-red-700 bg-red-100 dark:text-red-300 dark:bg-red-900/30 rounded-full flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Delayed
                </span>
            );
        default:
            return (
                <span className="px-2 py-1 text-xs font-medium text-slate-700 bg-slate-100 dark:text-slate-300 dark:bg-slate-800 rounded-full flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Pending
                </span>
            );
    }
}

function LaunchStatusIndicator({ status }: { status: ProductLaunchData['status'] }) {
    switch (status) {
        case 'on_track':
            return (
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-semibold">On Track</span>
                </div>
            );
        case 'at_risk':
            return (
                <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="font-semibold">At Risk</span>
                </div>
            );
        case 'delayed':
            return (
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                    <XCircle className="w-5 h-5" />
                    <span className="font-semibold">Delayed</span>
                </div>
            );
        default:
            return (
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-semibold">On Track</span>
                </div>
            );
    }
}

function TimelineConnector({ isLast }: { isLast: boolean }) {
    if (isLast) return null;
    return (
        <div className="absolute left-6 top-10 bottom-0 w-0.5 bg-slate-200 dark:bg-slate-700 -ml-px h-full" />
    );
}

// =============================================================================
// Main Component
// =============================================================================

export default function ProductLaunchWidget({ definition, onAction }: WidgetProps) {
    const data = definition.data as unknown as ProductLaunchData || {
        milestones: [],
        status: 'on_track'
    };

    // Default values
    const milestones = data.milestones || [];
    const status = data.status || 'on_track';

    // Calculate progress
    const completedCount = milestones.filter(m => m.status === 'completed').length;
    const progress = milestones.length > 0
        ? Math.round((completedCount / milestones.length) * 100)
        : 0;

    const handleMilestoneClick = (milestone: Milestone) => {
        onAction?.('view_milestone', { milestone });
    };

    const formatDate = (dateStr: string) => {
        try {
            const date = new Date(dateStr);
            return new Intl.DateTimeFormat('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            }).format(date);
        } catch (e) {
            return dateStr;
        }
    };

    return (
        <div className="space-y-6">
            {/* Launch Status Header */}
            <div className="flex items-center justify-between bg-slate-50 dark:bg-slate-800/50 p-4 rounded-lg border border-slate-200 dark:border-slate-700">
                <div className="flex flex-col">
                    <span className="text-sm text-slate-500 dark:text-slate-400 mb-1">Overall Status</span>
                    <LaunchStatusIndicator status={status} />
                </div>
                <div className="flex flex-col items-end">
                    <span className="text-sm text-slate-500 dark:text-slate-400 mb-1">Progress</span>
                    <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-bold text-slate-800 dark:text-white">{progress}%</span>
                        <span className="text-xs text-slate-500">
                            ({completedCount}/{milestones.length})
                        </span>
                    </div>
                </div>
            </div>

            {/* Milestones Timeline */}
            <div className="relative space-y-0">
                {milestones.length === 0 ? (
                    <div className="text-center py-8 text-slate-500">
                        No milestones defined
                    </div>
                ) : (
                    milestones.map((milestone, index) => (
                        <div key={index} className="relative flex gap-4 pb-8 last:pb-0 group">
                            {/* Connector Line */}
                            <TimelineConnector isLast={index === milestones.length - 1} />

                            {/* Date Column */}
                            <div className="flex-none pt-1">
                                <div className="w-12 text-xs font-medium text-right text-slate-500 dark:text-slate-400">
                                    {formatDate(milestone.date).split(',')[0]}
                                </div>
                                <div className="w-12 text-[10px] text-right text-slate-400 dark:text-slate-500">
                                    {formatDate(milestone.date).split(',')[1]?.trim()}
                                </div>
                            </div>

                            {/* Timeline Dot */}
                            <div className="relative pt-1">
                                <div className={`w-3 h-3 rounded-full border-2 bg-white dark:bg-slate-800 transition-colors ${milestone.status === 'completed'
                                    ? 'border-emerald-500 bg-emerald-500'
                                    : milestone.status === 'delayed'
                                        ? 'border-red-500'
                                        : milestone.status === 'in_progress'
                                            ? 'border-blue-500'
                                            : 'border-slate-300 dark:border-slate-600'
                                    }`} />
                            </div>

                            {/* Content Card */}
                            <div
                                className="flex-1 -mt-1 hover:bg-slate-50 dark:hover:bg-slate-800/50 p-3 rounded-lg border border-transparent hover:border-slate-200 dark:hover:border-slate-700 transition-all cursor-pointer"
                                onClick={() => handleMilestoneClick(milestone)}
                            >
                                <div className="flex items-start justify-between gap-4 mb-1">
                                    <h4 className="font-medium text-slate-800 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                                        {milestone.name}
                                    </h4>
                                    <MilestoneStatusBadge status={milestone.status} />
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

// Add "use client" directive for Next.js App Router compatibility
'use client';
