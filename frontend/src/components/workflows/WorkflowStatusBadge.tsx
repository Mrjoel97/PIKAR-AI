'use client';

import React from 'react';
import { WorkflowExecution } from '@/services/workflows';
import {
    ClockIcon,
    PlayIcon,
    PauseIcon,
    CheckCircleIcon,
    XCircleIcon,
    NoSymbolIcon
} from '@heroicons/react/24/outline';

interface WorkflowStatusBadgeProps {
    status: WorkflowExecution['status'];
}

export default function WorkflowStatusBadge({ status }: WorkflowStatusBadgeProps) {
    const config = {
        pending: { color: 'bg-slate-100 text-slate-600', icon: ClockIcon, text: 'Pending' },
        running: { color: 'bg-blue-100 text-blue-700', icon: PlayIcon, text: 'Running' },
        paused: { color: 'bg-amber-100 text-amber-700', icon: PauseIcon, text: 'Paused' },
        completed: { color: 'bg-green-100 text-green-700', icon: CheckCircleIcon, text: 'Completed' },
        failed: { color: 'bg-red-100 text-red-700', icon: XCircleIcon, text: 'Failed' },
        cancelled: { color: 'bg-slate-100 text-slate-500', icon: NoSymbolIcon, text: 'Cancelled' },
    };

    const { color, icon: Icon, text } = config[status] || config.pending;

    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
            <Icon className="w-3 h-3 mr-1" />
            {text}
        </span>
    );
}
