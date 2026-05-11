// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth, fetchWithAuthRaw, getClientPersonaHeader } from './api';
import { createClient } from '@/lib/supabase/client';
import type { components } from '@/types/api.generated';

// ---------------------------------------------------------------------------
// Types sourced from generated OpenAPI schema (api.generated.ts)
// These are kept in sync automatically via `npm run generate:types`.
// ---------------------------------------------------------------------------

/** Workflow template metadata from the backend. */
export type WorkflowTemplate = components['schemas']['WorkflowTemplateResponse'];

/**
 * Graph projection sub-types (Phase 109 / Spec B Phase 1).
 *
 * These mirror the Pydantic models in `app/routers/workflows.py`. They are
 * named exports here so Plan 109-03's NodeCanvas component (and any future
 * editor surfaces) can import them by name instead of digging through the
 * generated `components['schemas']` index.
 *
 * Phase 1 only renders `trigger`, `agent-action`, `output`. The remaining
 * kinds are reserved for Spec B Phases 3-4 but live in the union now so
 * frontend types stay stable across phases.
 */

/** Pixel-space position of a graph node (React Flow / dagre output). */
export interface NodePosition {
    x: number;
    y: number;
}

/** All node kinds the workflow editor will ever render (Phase 1 uses 3 of 7). */
export type NodeKind =
    | 'trigger'
    | 'agent-action'
    | 'condition'
    | 'parallel'
    | 'merge'
    | 'human-approval'
    | 'output';

/** One node in the workflow graph projection. */
export interface GraphNode {
    id: string;
    kind: NodeKind;
    label: string;
    config?: Record<string, unknown> | null;
}

/** One directed edge between two graph nodes. */
export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    source_handle?: string | null;
    label?: string | null;
}

/**
 * One structural error returned by POST /workflows/templates/{id}/validate
 * (Phase 110-03). ``node_id`` is null for graph-level errors (e.g. "no
 * trigger node" or "no output node"); ``rule`` is one of 1, 2, 3, 6, 7.
 *
 * Mirrors ``app.workflows.graph_validation.ValidationError`` byte-for-byte.
 * Plan 04's ``useGraphValidation`` hook will import this alias instead of
 * digging through ``components['schemas']['ValidationErrorItem']``.
 */
export type ValidationError = components['schemas']['ValidationErrorItem'];

/**
 * Response from POST /workflows/templates/{id}/validate (Phase 110-03).
 * Empty ``errors`` array means the graph is valid; a non-empty array MUST
 * block Save in the frontend (and is also blocked server-side at PUT time).
 */
export type ValidateGraphResponse = components['schemas']['ValidateGraphResponse'];

/**
 * Save endpoint typed schemas from Plan 02 (PUT /workflows/templates/{id}).
 * Re-exported as named aliases so Plan 04 consumers don't need to dig into
 * components['schemas'].
 */
export type WorkflowTemplateVersion = components['schemas']['WorkflowTemplateVersion'];
export type SaveTemplateSuccessResponse =
    components['schemas']['SaveTemplateSuccessResponse'];
export type SeedForkResponse = components['schemas']['SeedForkResponse'];
export type SaveTemplateRequest = components['schemas']['SaveTemplateRequest'];

/**
 * Workflow template enriched with the captured ETag from the GET response
 * header (canonical for GET per Plan 02 B-2 contract). Plan 04 editor page
 * stores ``_etag`` for the next PUT's If-Match header.
 */
export interface WorkflowTemplateWithEtag extends WorkflowTemplate {
    _etag?: string;
}

/** Response from starting a workflow execution. */
export type StartWorkflowResponse = components['schemas']['StartWorkflowResponse'];

/**
 * A single step record from the workflow execution history.
 * Re-exported as WorkflowStep for backward compatibility.
 */
export type WorkflowStep = components['schemas']['WorkflowHistoryItem'];

// ---------------------------------------------------------------------------
// Types NOT yet in the generated schema — kept hand-maintained with TODO.
// TODO(ARCH-04): Align backend schema to expose these as Pydantic models.
// ---------------------------------------------------------------------------

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

// TODO(ARCH-04): WorkflowExecution is not a named Pydantic schema in the
// OpenAPI spec — the backend returns it as `{[key: string]: unknown}` inside
// WorkflowExecutionResponse.execution. Keep hand-maintained until the backend
// exposes a typed WorkflowExecution Pydantic model.
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
    total_phases?: number | null;
    trust_summary?: Record<string, unknown> | null;
    verification_status?: string | null;
    approval_state?: string | null;
    evidence_refs?: unknown[] | null;
}

// TODO(ARCH-04): WorkflowExecutionDetails wraps WorkflowExecution which is
// not yet a named schema. Keep hand-maintained until backend aligns.
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

// TODO(ARCH-04): CreateWorkflowTemplateRequest is not a named Pydantic schema
// in the generated spec. Keep hand-maintained until backend exposes it.
export interface CreateWorkflowTemplateRequest {
    name: string;
    description?: string;
    category: string;
    phases: Array<Record<string, any>>;
    template_key?: string;
    personas_allowed?: string[];
    is_generated?: boolean;
}

// TODO(ARCH-04): WorkflowTrigger and related types are not in the generated
// spec. Keep hand-maintained until backend exposes them as Pydantic models.
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

export async function resumeWorkflowExecution(executionId: string): Promise<{ status: string; execution_id: string; steps_reset: number; message: string }> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

export interface TimelineStep {
    id: string;
    phase_name: string;
    step_name: string;
    status: string;
    started_at: string | null;
    completed_at: string | null;
    phase_index: number;
    step_index: number;
    duration_ms: number | null;
    tool_name: string;
    error_message: string | null;
}

export interface ExecutionTimeline {
    execution_id: string;
    name: string;
    status: string;
    created_at: string;
    completed_at: string | null;
    steps: TimelineStep[];
    chain_info: {
        parent_execution_id: string;
        parent_template_name: string | null;
        chain_depth: number;
    } | null;
}

export async function getExecutionTimeline(executionId: string): Promise<ExecutionTimeline> {
    const response = await fetchWithAuth(`/workflows/executions/${executionId}/timeline`);
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

// ============================================================================
// Phase 110 Plan 04: editable workflow editor service surface
//
// Save (PUT) / Validate (POST) / Get-with-ETag methods + three typed error
// classes wired to Plan 02's PUT contract (B-2 wire format + W-4 SeedFork
// response shape + Plan 03's PUT-time validation 400 path).
// ============================================================================

/**
 * Thrown when PUT returns 412 Precondition Failed (If-Match mismatch).
 *
 * Carries the fresh template body (so Plan 05's ConflictModal can render
 * "View their changes") AND ``freshEtag`` — read from ``body.etag``, NOT
 * the response header, per Plan 02's B-2 wire-format contract.
 *
 * Plan 05's ConflictModal Overwrite path re-fires PUT with ``freshEtag``
 * as the If-Match header.
 */
export class ETagMismatchError extends Error {
    constructor(
        public readonly currentTemplate: WorkflowTemplate,
        public readonly freshEtag: string,
    ) {
        super(
            'Template was modified by another save; refresh to see the latest version',
        );
        this.name = 'ETagMismatchError';
    }
}

/**
 * Thrown when PUT against a seed template (``created_by IS NULL``) returns
 * 409 with SeedForkResponse. Reads BOTH ``body.copied_template_id`` AND
 * ``body.seed_name`` per W-4 (Plan 02 guarantees both keys present).
 *
 * Plan 04 editor page catches this, shows a sonner toast
 * ``Created your private copy of "${err.seedName}"`` and
 * ``router.push('/dashboard/workflows/editor/' + err.copiedTemplateId)``.
 */
export class CopyForkError extends Error {
    constructor(
        public readonly copiedTemplateId: string,
        public readonly seedName: string,
    ) {
        super(`Created a private copy of seed template "${seedName}"`);
        this.name = 'CopyForkError';
    }
}

/**
 * Thrown when PUT returns 400 because Plan 03's server-side
 * ``validate_workflow_graph()`` rejected the graph. Carries the list of
 * structured validation errors so the editor page can surface them.
 *
 * Note: the editor SHOULD never hit this — client-side useGraphValidation
 * (Task 04-02) blocks Save before the PUT goes out. But the server
 * enforces validation as a defence-in-depth, and direct API callers can
 * trigger this path.
 */
export class ValidationFailedError extends Error {
    constructor(public readonly errors: ValidationError[]) {
        super(`Save blocked: ${errors.length} validation error(s)`);
        this.name = 'ValidationFailedError';
    }
}

/**
 * GET /workflows/templates/{id} with the response ETag captured.
 *
 * The ETag header is canonical for GET responses (per Plan 02 B-2: GET
 * has no etag in body; PUT 200/412 have etag in BODY). The editor page
 * stores ``_etag`` for the next save's If-Match header.
 */
export async function getWorkflowTemplateWithEtag(
    templateId: string,
): Promise<WorkflowTemplateWithEtag> {
    const response = await fetchWithAuthRaw(
        `/workflows/templates/${templateId}`,
    );
    if (!response.ok) {
        throw new Error(
            `Failed to load workflow template: ${response.status} ${response.statusText}`,
        );
    }
    const body = (await response.json()) as WorkflowTemplate;
    const etag = response.headers.get('etag') ?? undefined;
    return { ...body, _etag: etag };
}

interface SaveTemplatePayload {
    graph_nodes: GraphNode[];
    graph_edges: GraphEdge[];
    graph_layout?: Record<string, NodePosition>;
    comment?: string;
}

/**
 * PUT /workflows/templates/{id} — save a new version with If-Match
 * optimistic locking. The returned ``etag`` is the next-write ETag,
 * read from ``body.etag`` (NOT the response header) per Plan 02 B-2.
 *
 * The ``etag`` parameter is sent verbatim as the ``If-Match`` header
 * (the server defensively strips quotes if you forget, but the canonical
 * format is the quoted ISO8601 returned by the previous GET/PUT — pass
 * it through without modification).
 *
 * Throws:
 *   - ETagMismatchError on 412 (with fresh body + body.etag as freshEtag)
 *   - CopyForkError on 409 (with body.copied_template_id + body.seed_name)
 *   - ValidationFailedError on 400 (with body.detail.errors)
 *   - Generic Error on 428 / other non-2xx
 */
export async function saveTemplate(
    templateId: string,
    payload: SaveTemplatePayload,
    etag: string,
): Promise<SaveTemplateSuccessResponse> {
    const response = await fetchWithAuthRaw(
        `/workflows/templates/${templateId}`,
        {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'If-Match': etag,
            },
            body: JSON.stringify(payload),
        },
    );

    if (response.status === 412) {
        // B-2: fresh ETag is in body.etag (not response header).
        const body = (await response.json()) as WorkflowTemplate & {
            etag?: string;
        };
        const freshEtag = body.etag ?? '';
        throw new ETagMismatchError(body as WorkflowTemplate, freshEtag);
    }
    if (response.status === 409) {
        // W-4: body has {error, copied_template_id, seed_name, message}.
        const body = (await response.json()) as SeedForkResponse;
        throw new CopyForkError(body.copied_template_id, body.seed_name);
    }
    if (response.status === 400) {
        // Plan 03's validate_workflow_graph() rejected the graph at PUT time.
        const body = (await response.json()) as {
            detail?: { errors?: ValidationError[] };
            errors?: ValidationError[];
        };
        const errors = body.detail?.errors ?? body.errors ?? [];
        throw new ValidationFailedError(errors);
    }
    if (response.status === 428) {
        throw new Error('If-Match header required (428 Precondition Required)');
    }
    if (!response.ok) {
        let text = '';
        try {
            text = await response.text();
        } catch {
            // ignore
        }
        throw new Error(`Save failed: ${response.status} ${text}`.trim());
    }
    return (await response.json()) as SaveTemplateSuccessResponse;
}

/**
 * POST /workflows/templates/{id}/validate — server-side validation
 * without saving. Plan 04's editor page can call this on every keystroke
 * (returns the same errors[] shape as the client useGraphValidation).
 *
 * In practice Plan 04 uses the client validator for live feedback and
 * only relies on the server enforcement at Save time. This method is
 * exposed for completeness / future test-run flows.
 */
export async function validateTemplate(
    templateId: string,
    graph: { graph_nodes: GraphNode[]; graph_edges: GraphEdge[] },
): Promise<ValidationError[]> {
    const response = await fetchWithAuthRaw(
        `/workflows/templates/${templateId}/validate`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(graph),
        },
    );
    if (!response.ok) {
        throw new Error(`Validate failed: ${response.status}`);
    }
    const body = (await response.json()) as ValidateGraphResponse;
    return body.errors;
}
