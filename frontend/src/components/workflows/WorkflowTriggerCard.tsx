'use client';

import React from 'react';

import type { WorkflowTriggerType } from '@/services/workflows';
import {
  DEPARTMENT_OPTIONS,
  PERSONA_OPTIONS,
  SCHEDULE_OPTIONS,
  WorkflowTriggerDraft,
  formatAutomationTimestamp,
  getTriggerDepartment,
  getTriggerModeLabel,
} from './automationUtils';

type TemplateOption = {
  id: string;
  name: string;
};

type WorkflowTriggerCardProps = {
  trigger: WorkflowTriggerDraft;
  onChange: (trigger: WorkflowTriggerDraft) => void;
  onSave?: () => void | Promise<void>;
  onDelete?: () => void | Promise<void>;
  templateOptions?: TemplateOption[];
  fixedTemplateId?: string;
  templateLabel?: string;
  lockedDepartment?: string;
  approvalGateCount?: number;
  saving?: boolean;
  disabled?: boolean;
  saveLabel?: string;
};

function updateContext(
  trigger: WorkflowTriggerDraft,
  patch: Record<string, any>,
): WorkflowTriggerDraft {
  return {
    ...trigger,
    context: {
      ...(trigger.context || {}),
      ...patch,
    },
  };
}

export default function WorkflowTriggerCard({
  trigger,
  onChange,
  onSave,
  onDelete,
  templateOptions = [],
  fixedTemplateId,
  templateLabel,
  lockedDepartment,
  approvalGateCount = 0,
  saving = false,
  disabled = false,
  saveLabel = 'Save automation',
}: WorkflowTriggerCardProps) {
  const department = lockedDepartment || getTriggerDepartment(trigger) || '';
  const resolvedTemplateId = fixedTemplateId || trigger.template_id || '';
  const modeLabel = getTriggerModeLabel(trigger.trigger_type);
  const templateName = templateLabel || templateOptions.find((option) => option.id === resolvedTemplateId)?.name || 'Select a workflow';

  const handleTypeChange = (value: WorkflowTriggerType) => {
    if (value === 'event') {
      onChange({
        ...trigger,
        trigger_type: value,
        schedule_frequency: trigger.schedule_frequency || 'daily',
      });
      return;
    }

    onChange({
      ...trigger,
      trigger_type: value,
      event_name: '',
    });
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{modeLabel}</p>
          <p className="mt-1 text-sm text-slate-600">
            {approvalGateCount > 0
              ? `${approvalGateCount} approval gate${approvalGateCount === 1 ? '' : 's'} remain active when this automation runs.`
              : 'This automation can run straight through without a human approval step.'}
          </p>
        </div>
        <label className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">
          <input
            type="checkbox"
            checked={trigger.enabled}
            disabled={disabled}
            onChange={(event) => onChange({ ...trigger, enabled: event.target.checked })}
          />
          Enabled
        </label>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="space-y-1 text-sm text-slate-700">
          <span className="font-medium">Automation name</span>
          <input
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2"
            value={trigger.trigger_name}
            disabled={disabled}
            placeholder="Monday revenue review"
            onChange={(event) => onChange({ ...trigger, trigger_name: event.target.value })}
          />
        </label>

        {!fixedTemplateId ? (
          <label className="space-y-1 text-sm text-slate-700">
            <span className="font-medium">Workflow</span>
            <select
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2"
              value={resolvedTemplateId}
              disabled={disabled}
              onChange={(event) => onChange({ ...trigger, template_id: event.target.value })}
            >
              <option value="">Select a published workflow</option>
              {templateOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <div className="space-y-1 text-sm text-slate-700">
            <span className="font-medium">Workflow</span>
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-slate-600">{templateName}</div>
          </div>
        )}

        <label className="space-y-1 text-sm text-slate-700">
          <span className="font-medium">Launch mode</span>
          <select
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2"
            value={trigger.trigger_type}
            disabled={disabled}
            onChange={(event) => handleTypeChange(event.target.value as WorkflowTriggerType)}
          >
            <option value="schedule">Scheduled run</option>
            <option value="event">Event hook</option>
          </select>
        </label>

        {trigger.trigger_type === 'schedule' ? (
          <label className="space-y-1 text-sm text-slate-700">
            <span className="font-medium">Schedule</span>
            <select
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2"
              value={trigger.schedule_frequency}
              disabled={disabled}
              onChange={(event) => onChange({ ...trigger, schedule_frequency: event.target.value as WorkflowTriggerDraft['schedule_frequency'] })}
            >
              {SCHEDULE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="space-y-1 text-sm text-slate-700">
            <span className="font-medium">Event name</span>
            <input
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2"
              value={trigger.event_name}
              disabled={disabled}
              placeholder="workflow.started"
              onChange={(event) => onChange({ ...trigger, event_name: event.target.value })}
            />
          </label>
        )}

        <label className="space-y-1 text-sm text-slate-700">
          <span className="font-medium">Department</span>
          <select
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2"
            value={department}
            disabled={disabled || Boolean(lockedDepartment)}
            onChange={(event) => onChange(updateContext(trigger, { department: event.target.value }))}
          >
            <option value="">No department lane</option>
            {DEPARTMENT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option.charAt(0).toUpperCase() + option.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm text-slate-700">
          <span className="font-medium">Persona</span>
          <select
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2"
            value={trigger.persona || ''}
            disabled={disabled}
            onChange={(event) => onChange({ ...trigger, persona: event.target.value || null })}
          >
            <option value="">Inherit active workspace persona</option>
            {PERSONA_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option.charAt(0).toUpperCase() + option.slice(1)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-3 rounded-2xl border border-dashed border-slate-200 bg-white/70 p-3 text-xs text-slate-500 md:grid-cols-3">
        <div>
          <p className="font-semibold uppercase tracking-wide text-slate-400">Next run</p>
          <p className="mt-1 text-sm text-slate-700">{formatAutomationTimestamp(trigger.next_run_at)}</p>
        </div>
        <div>
          <p className="font-semibold uppercase tracking-wide text-slate-400">Last run</p>
          <p className="mt-1 text-sm text-slate-700">{formatAutomationTimestamp(trigger.last_run_at)}</p>
        </div>
        <div>
          <p className="font-semibold uppercase tracking-wide text-slate-400">Last event</p>
          <p className="mt-1 text-sm text-slate-700">
            {trigger.trigger_type === 'event'
              ? `${trigger.event_name || 'Awaiting event'} · ${formatAutomationTimestamp(trigger.last_event_at)}`
              : 'Not event-driven'}
          </p>
        </div>
      </div>

      {(onSave || onDelete) ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-slate-500">
            Runs in <span className="font-medium text-slate-700">{trigger.lane}</span> lane using <span className="font-medium text-slate-700">{trigger.queue_mode}</span> queue mode.
          </p>
          <div className="flex gap-2">
            {onDelete ? (
              <button
                type="button"
                disabled={saving}
                onClick={() => void onDelete()}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-50"
              >
                Remove
              </button>
            ) : null}
            {onSave ? (
              <button
                type="button"
                disabled={disabled || saving}
                onClick={() => void onSave()}
                className="rounded-xl bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
              >
                {saving ? 'Saving...' : saveLabel}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
