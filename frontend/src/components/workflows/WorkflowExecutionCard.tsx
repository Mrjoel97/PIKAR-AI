'use client';

import React from 'react';
import { WorkflowExecution } from '@/services/workflows';
import WorkflowStatusBadge from './WorkflowStatusBadge';
import { CalendarIcon } from '@heroicons/react/24/outline';

interface WorkflowExecutionCardProps {
    execution: WorkflowExecution & { template_name: string };
    onClick: (id: string) => void;
}

export default function WorkflowExecutionCard({ execution, onClick }: WorkflowExecutionCardProps) {
    const formattedDate = new Date(execution.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric'
    });
    const topic = execution.context?.topic;
    const displayTitle = typeof topic === 'string' && topic.trim() ? topic : execution.template_name;

    // Mock progress calculation if not available directly
    // Assuming 5 phases as generic fallback if not present
    const totalPhases = 5;
    const progress = Math.min(100, Math.round(((execution.current_phase_index + 1) / totalPhases) * 100));

    return (
        <div
            onClick={() => onClick(execution.id)}
            className="block bg-white border border-slate-200 rounded-2xl p-4 hover:border-blue-500 hover:shadow-md transition-all cursor-pointer"
        >
            <div className="flex justify-between items-start mb-2">
                <div>
                    <h4 className="text-base font-semibold text-slate-900 mb-1">
                        {displayTitle}
                    </h4>
                    <p className="text-sm text-slate-500">
                        {execution.template_name}
                    </p>
                </div>
                <WorkflowStatusBadge status={execution.status} />
            </div>

            <div className="mt-4">
                <div className="flex justify-between text-xs text-slate-500 mb-1">
                    <span>Progress</span>
                    <span>{progress}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-1.5">
                    <div
                        className={`h-1.5 rounded-full ${execution.status === 'failed' ? 'bg-red-500' :
                                execution.status === 'completed' ? 'bg-green-500' :
                                    'bg-blue-600'
                            }`}
                        style={{ width: `${progress}%` }}
                    />
                </div>
            </div>

            <div className="mt-4 flex items-center text-xs text-slate-400">
                <CalendarIcon className="w-3.5 h-3.5 mr-1.5" />
                Started {formattedDate}
            </div>
        </div>
    );
}
