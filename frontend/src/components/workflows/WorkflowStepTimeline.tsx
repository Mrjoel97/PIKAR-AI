'use client';

import React, { useState } from 'react';
import { WorkflowStep } from '@/services/workflows';
import { CheckIcon, ClockIcon, ExclamationTriangleIcon, PlayIcon, HandThumbUpIcon, ArrowPathIcon } from '@heroicons/react/24/solid';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface WorkflowStepTimelineProps {
    steps: WorkflowStep[];
    currentStepIndex: number;
    onApprove?: (executionId: string, feedback: string) => Promise<void>;
    onRetryStep?: (executionId: string, stepId: string) => Promise<void>;
}

export default function WorkflowStepTimeline({ steps, currentStepIndex, onApprove, onRetryStep }: WorkflowStepTimelineProps) {
    const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
    const [approving, setApproving] = useState<string | null>(null);
    const [retrying, setRetrying] = useState<string | null>(null);
    const [feedback, setFeedback] = useState('');
    const safeSteps = Array.isArray(steps) ? steps : [];

    const toggleStep = (stepId: string) => {
        const newExpanded = new Set(expandedSteps);
        if (newExpanded.has(stepId)) {
            newExpanded.delete(stepId);
        } else {
            newExpanded.add(stepId);
        }
        setExpandedSteps(newExpanded);
    };

    const handleRetry = async (executionId: string, stepId: string) => {
        if (!onRetryStep || !executionId) return;
        setRetrying(stepId);
        try {
            await onRetryStep(executionId, stepId);
        } catch (error) {
            console.error('Failed to retry step:', error);
        } finally {
            setRetrying(null);
        }
    };

    const handleApprove = async (executionId: string, stepId: string) => {
        if (!onApprove || !executionId) return;
        setApproving(stepId);
        try {
            await onApprove(executionId, feedback);
            setFeedback('');
        } catch (error) {
            console.error('Failed to approve:', error);
        } finally {
            setApproving(null);
        }
    };

    return (
        <div className="flow-root">
            <ul role="list" className="-mb-8">
                {safeSteps.map((step, stepIdx) => {
                    const executionId = typeof step.execution_id === 'string' ? step.execution_id : '';
                    const phaseName = typeof step.phase_name === 'string' && step.phase_name.trim() ? step.phase_name : 'phase';
                    const stepName = typeof step.step_name === 'string' && step.step_name.trim() ? step.step_name : `Step ${stepIdx + 1}`;
                    const stepId = typeof step.id === 'string' && step.id
                        ? step.id
                        : `${executionId || 'execution'}-${phaseName}-${stepIdx}`;
                    const isLast = stepIdx === safeSteps.length - 1;
                    const isCurrent = stepIdx === currentStepIndex || step.status === 'running' || step.status === 'waiting_approval';
                    const isCompleted = step.status === 'completed';
                    const isFailed = step.status === 'failed';
                    const isWaitingApproval = step.status === 'waiting_approval';

                    let Icon = ClockIcon;
                    let iconBg = 'bg-slate-100';
                    let iconColor = 'text-slate-500';

                    if (isCompleted) {
                        Icon = CheckIcon;
                        iconBg = 'bg-green-500';
                        iconColor = 'text-white';
                    } else if (isFailed) {
                        Icon = ExclamationTriangleIcon;
                        iconBg = 'bg-red-500';
                        iconColor = 'text-white';
                    } else if (isWaitingApproval) {
                        Icon = HandThumbUpIcon;
                        iconBg = 'bg-amber-500';
                        iconColor = 'text-white';
                    } else if (isCurrent) {
                        Icon = PlayIcon;
                        iconBg = 'bg-blue-500';
                        iconColor = 'text-white animate-pulse';
                    }

                    return (
                        <li key={stepId}>
                            <div className="relative pb-8">
                                {!isLast && (
                                    <span
                                        className={`absolute top-4 left-4 -ml-px h-full w-0.5 ${isCompleted ? 'bg-green-500' : 'bg-slate-200'}`}
                                        aria-hidden="true"
                                    />
                                )}
                                <div className="relative flex space-x-3">
                                    <div>
                                        <span className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${iconBg}`}>
                                            <Icon className={`h-5 w-5 ${iconColor}`} aria-hidden="true" />
                                        </span>
                                    </div>
                                    <div className="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
                                        <div className="w-full">
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <p className={`text-sm font-medium ${isCurrent ? 'text-slate-900' : 'text-slate-500'}`}>
                                                        {stepName} <span className="text-slate-400 font-normal ml-1">({phaseName})</span>
                                                    </p>
                                                    {typeof step.attempt_count === 'number' && step.attempt_count > 1 && (
                                                        <p className="text-[11px] text-amber-700 mt-0.5">Attempt {step.attempt_count}</p>
                                                    )}
                                                </div>
                                                <div className="text-right text-xs text-slate-400 whitespace-nowrap">
                                                    {step.completed_at ? new Date(step.completed_at).toLocaleTimeString() : ''}
                                                </div>
                                            </div>

                                            {(step.output_data || step.input_data || step.error_message || isWaitingApproval) && (
                                                <div className="mt-2">
                                                    <button
                                                        onClick={() => toggleStep(stepId)}
                                                        className="text-xs text-blue-600 hover:text-blue-800 flex items-center"
                                                    >
                                                        {expandedSteps.has(stepId) ? (
                                                            <>Hide Details <ChevronUpIcon className="w-3 h-3 ml-1" /></>
                                                        ) : (
                                                            <>Show Details <ChevronDownIcon className="w-3 h-3 ml-1" /></>
                                                        )}
                                                    </button>

                                                    {expandedSteps.has(stepId) && (
                                                        <div className="mt-2 space-y-2 bg-slate-50 rounded-lg p-3 text-xs overflow-x-auto">
                                                            {step.error_message && (
                                                                <div className="text-red-600 font-medium">
                                                                    Error: {step.error_message}
                                                                </div>
                                                            )}
                                                            {step.input_data && Object.keys(step.input_data).length > 0 && (
                                                                <div>
                                                                    <span className="font-semibold text-slate-700">Input:</span>
                                                                    <pre className="text-slate-600 mt-1">{JSON.stringify(step.input_data, null, 2)}</pre>
                                                                </div>
                                                            )}
                                                            {step.output_data && Object.keys(step.output_data).length > 0 && (
                                                                <div>
                                                                    <span className="font-semibold text-slate-700">Output:</span>
                                                                    <pre className="text-slate-600 mt-1">{JSON.stringify(step.output_data, null, 2)}</pre>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}

                                                    {isWaitingApproval && onApprove && executionId && (
                                                        <div className="mt-3 bg-amber-50 p-3 rounded-md border border-amber-100">
                                                            <p className="text-sm text-amber-800 mb-2">This step requires your approval.</p>
                                                            <textarea
                                                                className="w-full text-sm p-2 border border-slate-300 rounded-md focus:ring-amber-500 focus:border-amber-500 mb-2"
                                                                placeholder="Optional feedback..."
                                                                rows={2}
                                                                value={feedback}
                                                                onChange={(e) => setFeedback(e.target.value)}
                                                            />
                                                            <button
                                                                onClick={() => handleApprove(executionId, stepId)}
                                                                disabled={!!approving}
                                                                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 disabled:opacity-50"
                                                            >
                                                                {approving === stepId ? (
                                                                    <><ArrowPathIcon className="w-3 h-3 mr-1 animate-spin" /> Approving...</>
                                                                ) : 'Approve & Continue'}
                                                            </button>
                                                        </div>
                                                    )}

                                                    {(step.status === 'failed' || step.status === 'skipped') && onRetryStep && executionId && (
                                                        <div className="mt-3">
                                                            <button
                                                                onClick={() => handleRetry(executionId, stepId)}
                                                                disabled={!!retrying}
                                                                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                                            >
                                                                {retrying === stepId ? (
                                                                    <><ArrowPathIcon className="w-3 h-3 mr-1 animate-spin" /> Retrying...</>
                                                                ) : 'Retry Step'}
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
