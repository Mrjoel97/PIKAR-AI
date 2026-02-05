import { fetchWithAuth } from './api';

export interface WorkflowTemplate {
    id: string;
    name: string;
    description: string;
    category: string;
}

export interface WorkflowExecution {
    id: string;
    user_id: string;
    template_id: string;
    name: string;
    status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
    current_phase_index: number;
    current_step_index: number;
    context: Record<string, any>;
    created_at: string;
    updated_at: string;
    completed_at?: string;
}

export interface WorkflowStep {
    id: string;
    execution_id: string;
    phase_name: string;
    step_name: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'waiting_approval';
    input_data?: Record<string, any>;
    output_data?: Record<string, any>;
    error_message?: string;
    started_at?: string;
    completed_at?: string;
}

export interface WorkflowExecutionDetails {
    execution: WorkflowExecution;
    template_name: string;
    history: WorkflowStep[];
    current_phase_index: number;
    current_step_index: number;
}

export interface StartWorkflowResponse {
    execution_id: string;
    status: string;
    current_step: string;
    message: string;
}

export async function listWorkflowTemplates(category?: string): Promise<WorkflowTemplate[]> {
    const query = category ? `?category=${encodeURIComponent(category)}` : '';
    const response = await fetchWithAuth(`/workflows/templates${query}`);
    if (!response.ok) {
        throw new Error('Failed to list workflow templates');
    }
    return response.json();
}

export async function startWorkflow(templateName: string, topic: string): Promise<StartWorkflowResponse> {
    const response = await fetchWithAuth('/workflows/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ template_name: templateName, topic }),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to start workflow' }));
        throw new Error(error.detail || 'Failed to start workflow');
    }
    return response.json();
}

export async function listWorkflowExecutions(status?: string, limit?: number, offset?: number): Promise<WorkflowExecution[]> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());

    const response = await fetchWithAuth(`/workflows/executions?${params.toString()}`);
    if (!response.ok) {
        throw new Error('Failed to list workflow executions');
    }
    return response.json();
}

export async function getWorkflowExecutionDetails(executionId: string): Promise<WorkflowExecutionDetails> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}`);
    if (!response.ok) {
        throw new Error('Failed to get workflow execution details');
    }
    return response.json();
}

export async function approveWorkflowStep(executionId: string, feedback: string): Promise<{ status: string, message: string }> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}/approve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ feedback }),
    });
    if (!response.ok) {
        throw new Error('Failed to approve workflow step');
    }
    return response.json();
}

export async function generateWorkflow(description: string, category: string): Promise<any> {
    const response = await fetchWithAuth('/workflows/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ description, category }),
    });
    // API returns 501 or similar for now, so we expose the error as useful info if it's not implemented
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to generate workflow' }));
        throw new Error(error.detail || 'Failed to generate workflow');
    }
    return response.json();
}
