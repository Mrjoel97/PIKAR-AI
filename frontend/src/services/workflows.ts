import { fetchWithAuth } from './api';
import { createClient } from '@/lib/supabase/client';

export interface WorkflowTemplate {
    id: string;
    name: string;
    description: string;
    category: string;
    template_key?: string;
    version?: number;
    lifecycle_status?: 'draft' | 'published' | 'archived';
    is_generated?: boolean;
    personas_allowed?: string[];
    last_published_at?: string | null;
}

export interface WorkflowOutcomeSummary {
    steps_completed?: number;
    tools_used?: string[];
    summary?: string;
}

export interface WorkflowExecution {
    id: string;
    user_id: string;
    template_id: string;
    name: string;
    status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'waiting_approval';
    current_phase_index: number;
    current_step_index: number;
    context: Record<string, any>;
    created_at: string;
    updated_at: string;
    completed_at?: string;
    outcome_summary?: WorkflowOutcomeSummary | null;
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
    attempt_count?: number;
    phase_key?: string;
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
    status: 'pending' | 'running' | 'waiting_approval';
    current_step: string;
    message: string;
}

export interface CreateWorkflowTemplateRequest {
    name: string;
    description?: string;
    category: string;
    phases: Array<Record<string, any>>;
    template_key?: string;
    personas_allowed?: string[];
    is_generated?: boolean;
}

export type WorkflowEventPayload = WorkflowExecutionDetails;

export async function listWorkflowTemplates(category?: string): Promise<WorkflowTemplate[]> {
    const query = category ? `?category=${encodeURIComponent(category)}` : '';
    const response = await fetchWithAuth(`/workflows/templates${query}`);
    if (!response.ok) {
        throw new Error('Failed to list workflow templates');
    }
    return response.json();
}

export async function listWorkflowTools(): Promise<string[]> {
    const response = await fetchWithAuth('/workflows/tool-registry');
    if (!response.ok) {
        throw new Error('Failed to list workflow tools');
    }
    const data = await response.json();
    return data.tools ?? [];
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

export async function startWorkflowByTemplateId(
    templateId: string,
    topic: string,
    templateVersion?: number,
    runSource: 'user_ui' | 'agent_ui' | 'system' = 'user_ui',
): Promise<StartWorkflowResponse> {
    const response = await fetchWithAuth('/workflows/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            template_id: templateId,
            template_version: templateVersion,
            topic,
            run_source: runSource,
        }),
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

export async function getWorkflowTemplate(templateId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}`);
    if (!response.ok) {
        throw new Error('Failed to load workflow template');
    }
    return response.json();
}

export async function createWorkflowTemplate(body: CreateWorkflowTemplateRequest): Promise<any> {
    const response = await fetchWithAuth('/workflows/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to create workflow template' }));
        throw new Error(error.detail || 'Failed to create workflow template');
    }
    return response.json();
}

export async function updateWorkflowTemplate(templateId: string, updates: Record<string, any>): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to update workflow template' }));
        throw new Error(error.detail || 'Failed to update workflow template');
    }
    return response.json();
}

export async function cloneWorkflowTemplate(templateId: string, newName?: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to clone workflow template' }));
        throw new Error(error.detail || 'Failed to clone workflow template');
    }
    return response.json();
}

export async function publishWorkflowTemplate(templateId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/publish`, {
        method: 'POST',
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to publish workflow template' }));
        throw new Error(error.detail || 'Failed to publish workflow template');
    }
    return response.json();
}

export async function archiveWorkflowTemplate(templateId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/archive`, {
        method: 'POST',
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to archive workflow template' }));
        throw new Error(error.detail || 'Failed to archive workflow template');
    }
    return response.json();
}

export async function listWorkflowTemplateVersions(templateId: string): Promise<any[]> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/versions`);
    if (!response.ok) {
        throw new Error('Failed to load template versions');
    }
    return response.json();
}

export async function diffWorkflowTemplate(templateId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/diff?against=published`);
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to diff template' }));
        throw new Error(error.detail || 'Failed to diff template');
    }
    return response.json();
}

export async function cancelWorkflowExecution(executionId: string, reason = 'Cancelled by user'): Promise<any> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to cancel execution' }));
        throw new Error(error.detail || 'Failed to cancel execution');
    }
    return response.json();
}

export async function retryWorkflowStep(executionId: string, stepId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}/retry-step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step_id: stepId }),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to retry step' }));
        throw new Error(error.detail || 'Failed to retry step');
    }
    return response.json();
}

export async function subscribeWorkflowExecutionEvents(
    executionId: string,
    handlers: {
        onStatus: (payload: WorkflowEventPayload) => void;
        onError?: (error: unknown) => void;
    },
): Promise<() => void> {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
    if (!token) {
        throw new Error('No auth session for workflow event stream');
    }

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${API_BASE_URL}/workflows/executions/${executionId}/events`;
    const controller = new AbortController();

    (async () => {
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: 'text/event-stream',
                },
                signal: controller.signal,
            });
            if (!response.ok || !response.body) {
                throw new Error(`SSE request failed (${response.status})`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                let idx = buffer.indexOf('\n\n');
                while (idx !== -1) {
                    const chunk = buffer.slice(0, idx);
                    buffer = buffer.slice(idx + 2);
                    idx = buffer.indexOf('\n\n');

                    const lines = chunk.split('\n');
                    let eventName = 'message';
                    let data = '';
                    for (const line of lines) {
                        if (line.startsWith('event:')) {
                            eventName = line.slice(6).trim();
                        } else if (line.startsWith('data:')) {
                            data += line.slice(5).trim();
                        }
                    }

                    if (!data) continue;
                    if (eventName === 'status') {
                        handlers.onStatus(JSON.parse(data));
                    } else if (eventName === 'error') {
                        handlers.onError?.(new Error(data));
                    }
                }
            }
        } catch (error) {
            if (!controller.signal.aborted) {
                handlers.onError?.(error);
            }
        }
    })();

    return () => controller.abort();
}
