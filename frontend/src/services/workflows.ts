import { fetchWithAuth, getClientPersonaHeader } from './api';
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
    artifacts?: Array<{
        type: string;
        label: string;
        value?: string;
        href?: string;
    }>;
    next_actions?: string[];
}

export type WorkflowExecutionStatus =
    | 'pending'
    | 'running'
    | 'paused'
    | 'completed'
    | 'failed'
    | 'cancelled'
    | 'waiting_approval';

export type WorkflowStepStatus =
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'skipped'
    | 'waiting_approval';

export interface WorkflowExecution {
    id: string;
    user_id: string;
    template_id: string;
    name: string;
    status: WorkflowExecutionStatus;
    current_phase_index: number;
    current_step_index: number;
    context: Record<string, any> | null;
    created_at: string;
    updated_at: string;
    completed_at?: string | null;
    outcome_summary?: WorkflowOutcomeSummary | null;
    template_name?: string;
    trust_summary?: Record<string, unknown> | null;
    verification_status?: string | null;
    approval_state?: string | null;
    evidence_refs?: unknown[] | null;
}

export interface WorkflowStep {
    id?: string | null;
    execution_id?: string | null;
    phase_name?: string | null;
    step_name?: string | null;
    status?: WorkflowStepStatus | null;
    input_data?: Record<string, any> | null;
    output_data?: Record<string, any> | null;
    error_message?: string | null;
    started_at?: string | null;
    completed_at?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
    phase_index?: number | null;
    step_index?: number | null;
    attempt_count?: number | null;
    phase_key?: string | null;
    tool_name?: string | null;
    trust_class?: string | null;
    verification_status?: string | null;
    evidence_refs?: unknown[] | null;
    last_failure_reason?: string | null;
}

export interface WorkflowExecutionDetails {
    execution: WorkflowExecution;
    template_name: string;
    history: WorkflowStep[];
    current_phase_index: number;
    current_step_index: number;
    trust_summary?: Record<string, unknown> | null;
    verification_status?: string | null;
    approval_state?: string | null;
    evidence_refs?: unknown[] | null;
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

export type WorkflowTriggerType = 'schedule' | 'event';

export type WorkflowTriggerFrequency =
    | 'hourly'
    | 'daily'
    | 'weekly'
    | 'monthly'
    | 'quarterly'
    | 'yearly';

export interface WorkflowTrigger {
    id: string;
    template_id: string;
    trigger_name: string;
    trigger_type: WorkflowTriggerType;
    schedule_frequency?: WorkflowTriggerFrequency | null;
    event_name?: string | null;
    context: Record<string, any>;
    enabled: boolean;
    run_source: string;
    next_run_at?: string | null;
    last_run_at?: string | null;
    last_event_at?: string | null;
    queue_mode: string;
    lane: string;
    persona?: string | null;
    created_at?: string;
    updated_at?: string;
}

export interface CreateWorkflowTriggerRequest {
    template_id: string;
    trigger_name: string;
    trigger_type: WorkflowTriggerType;
    schedule_frequency?: WorkflowTriggerFrequency | null;
    event_name?: string | null;
    context?: Record<string, any>;
    enabled?: boolean;
    run_source?: string;
    queue_mode?: string;
    lane?: string;
    persona?: string | null;
}

export interface UpdateWorkflowTriggerRequest {
    trigger_name?: string;
    trigger_type?: WorkflowTriggerType;
    schedule_frequency?: WorkflowTriggerFrequency | null;
    event_name?: string | null;
    context?: Record<string, any>;
    enabled?: boolean;
    run_source?: string;
    queue_mode?: string;
    lane?: string;
    persona?: string | null;
}

export type WorkflowEventPayload = WorkflowExecutionDetails;

function parseSseChunk(chunk: string): { eventName: string; data: string | null } | null {
    const lines = chunk.split('\n');
    let eventName = 'message';
    const dataLines: string[] = [];

    for (const rawLine of lines) {
        const line = rawLine.trimEnd();
        if (!line || line.startsWith(':')) {
            continue;
        }
        if (line.startsWith('event:')) {
            eventName = line.slice(6).trim();
            continue;
        }
        if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trimStart());
        }
    }

    if (dataLines.length === 0 || eventName === 'heartbeat') {
        return null;
    }

    return {
        eventName,
        data: dataLines.join('\n'),
    };
}

export async function listWorkflowTemplates(
    category?: string,
    options?: {
        lifecycleStatus?: string;
        persona?: string;
    },
): Promise<WorkflowTemplate[]> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (options?.lifecycleStatus) params.append('lifecycle_status', options.lifecycleStatus);
    if (options?.persona) params.append('persona', options.persona);

    const query = params.toString() ? `?${params.toString()}` : '';
    const response = await fetchWithAuth(`/workflows/templates${query}`);
    return response.json();
}

export async function listWorkflowTools(): Promise<string[]> {
    const response = await fetchWithAuth('/workflows/tool-registry');
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
    return response.json();
}

export async function listWorkflowExecutions(status?: string | string[], limit?: number, offset?: number): Promise<WorkflowExecution[]> {
    const params = new URLSearchParams();
    if (Array.isArray(status)) {
        const normalizedStatuses = status
            .map((value) => value.trim())
            .filter((value) => value.length > 0);

        if (normalizedStatuses.length === 1) {
            params.append('status', normalizedStatuses[0]);
        } else if (normalizedStatuses.length > 1) {
            params.append('statuses', normalizedStatuses.join(','));
        }
    } else if (status) {
        params.append('status', status);
    }
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());

    const suffix = params.toString();
    const response = await fetchWithAuth(`/workflows/executions${suffix ? `?${suffix}` : ''}`);
    return response.json();
}

export async function getWorkflowExecutionDetails(executionId: string): Promise<WorkflowExecutionDetails> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}`);
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
    return response.json();
}

export async function getWorkflowTemplate(templateId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}`);
    return response.json();
}

export async function createWorkflowTemplate(body: CreateWorkflowTemplateRequest): Promise<any> {
    const response = await fetchWithAuth('/workflows/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return response.json();
}

export async function updateWorkflowTemplate(templateId: string, updates: Record<string, any>): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    return response.json();
}

export async function cloneWorkflowTemplate(templateId: string, newName?: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
    });
    return response.json();
}

export async function publishWorkflowTemplate(templateId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/publish`, {
        method: 'POST',
    });
    return response.json();
}

export async function archiveWorkflowTemplate(templateId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/archive`, {
        method: 'POST',
    });
    return response.json();
}

export async function listWorkflowTriggers(options: {
    templateId?: string;
    enabled?: boolean;
    department?: string;
} = {}): Promise<WorkflowTrigger[]> {
    const params = new URLSearchParams();
    if (options.templateId) params.append('template_id', options.templateId);
    if (typeof options.enabled === 'boolean') params.append('enabled', String(options.enabled));
    if (options.department) params.append('department', options.department);

    const query = params.toString() ? `?${params.toString()}` : '';
    const response = await fetchWithAuth(`/workflow-triggers${query}`);
    const data = await response.json();
    return data.triggers ?? [];
}

export async function createWorkflowTrigger(
    body: CreateWorkflowTriggerRequest,
): Promise<{ status: string; trigger: WorkflowTrigger }> {
    const response = await fetchWithAuth('/workflow-triggers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return response.json();
}

export async function updateWorkflowTrigger(
    triggerId: string,
    body: UpdateWorkflowTriggerRequest,
): Promise<{ status: string; trigger: WorkflowTrigger }> {
    const response = await fetchWithAuth(`/workflow-triggers/${triggerId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return response.json();
}

export async function deleteWorkflowTrigger(
    triggerId: string,
): Promise<{ status: string; trigger: WorkflowTrigger }> {
    const response = await fetchWithAuth(`/workflow-triggers/${triggerId}`, {
        method: 'DELETE',
    });
    return response.json();
}

export async function dispatchWorkflowTriggerEvent(
    event_name: string,
    payload: Record<string, any> = {},
    source = 'user_event',
): Promise<any> {
    const response = await fetchWithAuth('/workflow-triggers/events/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_name, payload, source }),
    });
    return response.json();
}

export async function listWorkflowTemplateVersions(templateId: string): Promise<any[]> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/versions`);
    return response.json();
}

export async function diffWorkflowTemplate(templateId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/templates/${templateId}/diff?against=published`);
    return response.json();
}

export async function cancelWorkflowExecution(executionId: string, reason = 'Cancelled by user'): Promise<any> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
    });
    return response.json();
}

export async function retryWorkflowStep(executionId: string, stepId: string): Promise<any> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}/retry-step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step_id: stepId }),
    });
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
    const persona = getClientPersonaHeader();

    (async () => {
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: 'text/event-stream',
                    ...(persona ? { 'x-pikar-persona': persona } : {}),
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
                buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');

                let idx = buffer.indexOf('\n\n');
                while (idx !== -1) {
                    const chunk = buffer.slice(0, idx);
                    buffer = buffer.slice(idx + 2);
                    idx = buffer.indexOf('\n\n');

                    const parsed = parseSseChunk(chunk);
                    if (!parsed?.data) {
                        continue;
                    }

                    if (parsed.eventName === 'status') {
                        handlers.onStatus(JSON.parse(parsed.data));
                    } else if (parsed.eventName === 'error') {
                        try {
                            const payload = JSON.parse(parsed.data) as { error?: string };
                            handlers.onError?.(new Error(payload.error || parsed.data));
                        } catch {
                            handlers.onError?.(new Error(parsed.data));
                        }
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


