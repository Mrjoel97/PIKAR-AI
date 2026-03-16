import {
  WorkflowExecution,
  WorkflowTrigger,
  WorkflowTriggerFrequency,
  WorkflowTriggerType,
} from '@/services/workflows';

export type WorkflowTriggerDraft = {
  id?: string;
  template_id?: string;
  trigger_name: string;
  trigger_type: WorkflowTriggerType;
  schedule_frequency: WorkflowTriggerFrequency;
  event_name: string;
  context: Record<string, any>;
  enabled: boolean;
  run_source: string;
  queue_mode: string;
  lane: string;
  persona?: string | null;
  next_run_at?: string | null;
  last_run_at?: string | null;
  last_event_at?: string | null;
};

export const PERSONA_OPTIONS = ['solopreneur', 'startup', 'sme', 'enterprise'] as const;
export const DEPARTMENT_OPTIONS = ['marketing', 'sales', 'operations', 'finance', 'support', 'product', 'executive'] as const;
export const SCHEDULE_OPTIONS: WorkflowTriggerFrequency[] = ['hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'];

function titleize(value: string | null | undefined): string {
  return String(value || '')
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function createWorkflowTriggerDraft(
  overrides: Partial<WorkflowTriggerDraft> = {},
): WorkflowTriggerDraft {
  const defaultDepartment = typeof overrides.context?.department === 'string'
    ? overrides.context.department
    : '';

  return {
    id: overrides.id,
    template_id: overrides.template_id,
    trigger_name: overrides.trigger_name ?? '',
    trigger_type: overrides.trigger_type ?? 'schedule',
    schedule_frequency: overrides.schedule_frequency ?? 'daily',
    event_name: overrides.event_name ?? '',
    context: {
      department: defaultDepartment,
      ...(overrides.context || {}),
    },
    enabled: overrides.enabled ?? true,
    run_source: overrides.run_source ?? 'agent_ui',
    queue_mode: overrides.queue_mode ?? 'followup',
    lane: overrides.lane ?? (defaultDepartment ? 'department' : 'automation'),
    persona: overrides.persona ?? null,
    next_run_at: overrides.next_run_at ?? null,
    last_run_at: overrides.last_run_at ?? null,
    last_event_at: overrides.last_event_at ?? null,
  };
}

export function normalizeWorkflowTriggerDraft(
  trigger: Partial<WorkflowTrigger | WorkflowTriggerDraft>,
): WorkflowTriggerDraft {
  return createWorkflowTriggerDraft({
    id: typeof trigger.id === 'string' ? trigger.id : undefined,
    template_id: typeof trigger.template_id === 'string' ? trigger.template_id : undefined,
    trigger_name: typeof trigger.trigger_name === 'string' ? trigger.trigger_name : '',
    trigger_type: trigger.trigger_type === 'event' ? 'event' : 'schedule',
    schedule_frequency: (trigger.schedule_frequency as WorkflowTriggerFrequency | null) ?? 'daily',
    event_name: typeof trigger.event_name === 'string' ? trigger.event_name : '',
    context: trigger.context && typeof trigger.context === 'object' ? trigger.context : {},
    enabled: typeof trigger.enabled === 'boolean' ? trigger.enabled : true,
    run_source: typeof trigger.run_source === 'string' ? trigger.run_source : 'agent_ui',
    queue_mode: typeof trigger.queue_mode === 'string' ? trigger.queue_mode : 'followup',
    lane: typeof trigger.lane === 'string' ? trigger.lane : 'automation',
    persona: typeof trigger.persona === 'string' ? trigger.persona : null,
    next_run_at: typeof trigger.next_run_at === 'string' ? trigger.next_run_at : null,
    last_run_at: typeof trigger.last_run_at === 'string' ? trigger.last_run_at : null,
    last_event_at: typeof trigger.last_event_at === 'string' ? trigger.last_event_at : null,
  });
}

export function countApprovalGates(phases: Array<{ name?: string; steps?: Array<{ required_approval?: boolean }> }> = []): number {
  return phases.reduce((count, phase) => {
    const steps = Array.isArray(phase.steps) ? phase.steps : [];
    return count + steps.filter((step) => Boolean(step.required_approval)).length;
  }, 0);
}

export function getTriggerDepartment(trigger: Pick<WorkflowTriggerDraft, 'context'> | null | undefined): string | null {
  if (!trigger?.context || typeof trigger.context !== 'object') {
    return null;
  }

  const department = trigger.context.department;
  return typeof department === 'string' && department.trim() ? department.trim() : null;
}

export function formatAutomationTimestamp(value: string | null | undefined): string {
  if (!value) {
    return 'Not scheduled yet';
  }

  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return 'Unavailable';
  }

  return timestamp.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function getTriggerModeLabel(triggerType: WorkflowTriggerType): string {
  return triggerType === 'event' ? 'Event Hook' : 'Scheduled Run';
}

export function getExecutionAutomationSummary(execution: WorkflowExecution | null | undefined) {
  const context = execution?.context && typeof execution.context === 'object' ? execution.context : {};
  const trigger = context.trigger && typeof context.trigger === 'object'
    ? context.trigger as Record<string, unknown>
    : null;
  const kernel = context._agent_kernel && typeof context._agent_kernel === 'object'
    ? context._agent_kernel as Record<string, unknown>
    : null;
  const department = typeof context.department === 'string' && context.department.trim()
    ? context.department.trim()
    : null;
  const reason = typeof trigger?.reason === 'string' ? trigger.reason : null;
  const triggerType = trigger?.type === 'event' ? 'event' : trigger?.type === 'schedule' ? 'schedule' : null;
  const eventName = typeof trigger?.event_name === 'string' ? trigger.event_name : null;
  const approvalState = typeof execution?.approval_state === 'string'
    ? execution.approval_state
    : typeof context.approval_state === 'string'
      ? context.approval_state
      : null;
  const verificationStatus = typeof execution?.verification_status === 'string'
    ? execution.verification_status
    : typeof context.verification_status === 'string'
      ? context.verification_status
      : null;
  const evidenceCount = Array.isArray(execution?.evidence_refs) ? execution.evidence_refs.length : 0;
  const lane = typeof kernel?.lane === 'string'
    ? kernel.lane
    : typeof context.lane === 'string'
      ? context.lane
      : null;
  const queueMode = typeof kernel?.queue_mode === 'string'
    ? kernel.queue_mode
    : typeof context.queue_mode === 'string'
      ? context.queue_mode
      : null;
  const persona = typeof kernel?.persona === 'string'
    ? kernel.persona
    : typeof context.persona === 'string'
      ? context.persona
      : null;

  const modeLabel = triggerType ? getTriggerModeLabel(triggerType) : 'Manual launch';

  return {
    department,
    eventName,
    evidenceCount,
    isAutomated: Boolean(triggerType),
    lane,
    modeLabel,
    persona,
    queueMode,
    reason,
    approvalState,
    verificationStatus,
    triggerType,
  };
}

export function formatTrustLabel(value: string | null | undefined, fallback = 'Not started'): string {
  const normalized = typeof value === 'string' && value.trim() ? value : '';
  return normalized ? titleize(normalized) : fallback;
}

