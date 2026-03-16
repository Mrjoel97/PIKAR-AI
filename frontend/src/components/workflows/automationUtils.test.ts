import { describe, expect, it } from 'vitest'

import {
  countApprovalGates,
  createWorkflowTriggerDraft,
  formatTrustLabel,
  getExecutionAutomationSummary,
} from '@/components/workflows/automationUtils'

describe('automationUtils', () => {
  it('counts approval gates across phases', () => {
    expect(countApprovalGates([
      { steps: [{ required_approval: true }, { required_approval: false }] },
      { steps: [{ required_approval: true }] },
    ])).toBe(2)
  })

  it('summarizes trigger-driven executions for UI badges', () => {
    const summary = getExecutionAutomationSummary({
      context: {
        department: 'operations',
        trigger: {
          type: 'schedule',
          reason: 'schedule',
        },
        _agent_kernel: {
          lane: 'department',
          queue_mode: 'followup',
          persona: 'startup',
        },
      },
      approval_state: 'pending',
      verification_status: 'verified',
      evidence_refs: [{ id: 1 }],
    } as any)

    expect(summary.modeLabel).toBe('Scheduled Run')
    expect(summary.department).toBe('operations')
    expect(summary.lane).toBe('department')
    expect(summary.queueMode).toBe('followup')
    expect(summary.persona).toBe('startup')
    expect(summary.evidenceCount).toBe(1)
  })

  it('creates default trigger drafts with automation-safe defaults', () => {
    const draft = createWorkflowTriggerDraft({ context: { department: 'sales' } })

    expect(draft.lane).toBe('department')
    expect(formatTrustLabel('waiting_approval')).toBe('Waiting Approval')
  })
})
