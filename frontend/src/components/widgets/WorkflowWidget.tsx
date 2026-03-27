'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState } from 'react';
import { WidgetProps } from './WidgetRegistry';
import WorkflowStepTimeline from '@/components/workflows/WorkflowStepTimeline';
import { getWorkflowExecutionDetails, approveWorkflowStep, WorkflowExecutionDetails } from '@/services/workflows';
import { toast } from 'sonner';

export default function WorkflowWidget({ definition, onAction }: WidgetProps) {
    const [details, setDetails] = useState<WorkflowExecutionDetails | null>(null);
    const [loading, setLoading] = useState(true);
    const executionId = definition.data?.execution_id as string | undefined;

    useEffect(() => {
        if (executionId) {
            fetchDetails();
        }
    }, [executionId]);

    const fetchDetails = async () => {
        setLoading(true);
        try {
            // If data is provided in definition fully, use it, otherwise fetch
            // Ideally agent provides ID and we fetch fresh status
            if (definition.data?.history) {
                setDetails(definition.data as unknown as WorkflowExecutionDetails);
            } else if (executionId) {
                const data = await getWorkflowExecutionDetails(executionId);
                setDetails(data);
            }
        } catch (error) {
            console.error('Failed to load workflow details', error);
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async (execId: string, feedback: string) => {
        try {
            await approveWorkflowStep(execId, feedback);
            toast.success('Step approved');
            await fetchDetails(); // Refresh
            if (onAction) {
                onAction('step_approved', { executionId: execId, feedback });
            }
        } catch (error) {
            toast.error('Failed to approve step');
        }
    };

    if (loading) {
        return <div className="p-4 animate-pulse h-32 bg-slate-50 rounded-xl"></div>;
    }

    if (!details) {
        return <div className="p-4 text-slate-500">Workflow execution not found.</div>;
    }

    const detailsContext = details.execution?.context ?? {};
    const detailsTopic = typeof detailsContext.topic === 'string' ? detailsContext.topic : '';

    return (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
            <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
                <span className="font-medium text-slate-900 text-sm">
                    {detailsTopic || details.template_name}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${details.execution.status === 'running' ? 'bg-blue-100 text-blue-700' :
                    details.execution.status === 'completed' ? 'bg-green-100 text-green-700' :
                        'bg-slate-100 text-slate-600'
                    }`}>
                    {details.execution.status}
                </span>
            </div>
            <div className="p-4 max-h-96 overflow-y-auto">
                <WorkflowStepTimeline
                    steps={details.history}
                    currentStepIndex={details.current_step_index}
                    onApprove={handleApprove}
                />
            </div>
        </div>
    );
}
