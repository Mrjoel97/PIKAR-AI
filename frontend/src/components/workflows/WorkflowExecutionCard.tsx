'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React from 'react';
import { CalendarIcon } from '@heroicons/react/24/outline';

import { WorkflowExecution } from '@/services/workflows';
import WorkflowStatusBadge from './WorkflowStatusBadge';
import { formatTrustLabel, getExecutionAutomationSummary } from './automationUtils';

interface WorkflowExecutionCardProps {
  execution: WorkflowExecution;
  onClick: (id: string) => void;
}

function badgeClass(tone: 'slate' | 'blue' | 'amber' | 'emerald'): string {
  const styles = {
    slate: 'bg-slate-100 text-slate-700',
    blue: 'bg-blue-100 text-blue-700',
    amber: 'bg-amber-100 text-amber-700',
    emerald: 'bg-emerald-100 text-emerald-700',
  };
  return `inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium ${styles[tone]}`;
}

export default function WorkflowExecutionCard({ execution, onClick }: WorkflowExecutionCardProps) {
  const formattedDate = new Date(execution.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  });
  const topic = execution.context?.topic;
  const templateName = execution.template_name || 'Workflow run';
  const displayTitle = typeof topic === 'string' && topic.trim() ? topic : templateName;
  const automation = getExecutionAutomationSummary(execution);

  const totalPhases = execution.total_phases ?? 5;
  const progress = totalPhases > 0
    ? Math.min(100, Math.round(((execution.current_phase_index + 1) / totalPhases) * 100))
    : 0;

  return (
    <div
      onClick={() => onClick(execution.id)}
      className="block bg-white border border-slate-200 rounded-2xl p-4 hover:border-blue-500 hover:shadow-md transition-all cursor-pointer"
    >
      <div className="flex justify-between items-start mb-2 gap-3">
        <div>
          <h4 className="text-base font-semibold text-slate-900 mb-1">
            {displayTitle}
          </h4>
          <p className="text-sm text-slate-500">
            {templateName}
          </p>
        </div>
        <WorkflowStatusBadge status={execution.status} />
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <span className={badgeClass(automation.isAutomated ? 'blue' : 'slate')}>
          {automation.modeLabel}
        </span>
        {automation.department ? (
          <span className={badgeClass('slate')}>
            {automation.department}
          </span>
        ) : null}
        <span className={badgeClass(execution.approval_state === 'pending' ? 'amber' : 'emerald')}>
          Approval: {formatTrustLabel(execution.approval_state, 'Not required')}
        </span>
        <span className={badgeClass(execution.verification_status === 'failed' ? 'amber' : 'emerald')}>
          Verification: {formatTrustLabel(execution.verification_status, 'Not started')}
        </span>
        {automation.evidenceCount > 0 ? (
          <span className={badgeClass('slate')}>
            {automation.evidenceCount} evidence item{automation.evidenceCount === 1 ? '' : 's'}
          </span>
        ) : null}
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

      <div className="mt-4 flex items-center justify-between text-xs text-slate-400 gap-3">
        <div className="flex items-center min-w-0">
          <CalendarIcon className="w-3.5 h-3.5 mr-1.5" />
          <span className="truncate">Started {formattedDate}</span>
        </div>
        {automation.eventName ? (
          <span className="truncate text-slate-500">Event: {automation.eventName}</span>
        ) : null}
      </div>
    </div>
  );
}
