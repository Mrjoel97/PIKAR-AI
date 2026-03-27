'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useCallback, useMemo, useState } from 'react'
import ReactFlow, {
  addEdge,
  Background,
  Connection,
  Controls,
  Edge,
  Node,
  Panel,
  useEdgesState,
  useNodesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Box, GitBranch, Layers, Play, Plus, Save, Settings } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'

import WorkflowTriggerCard from '@/components/workflows/WorkflowTriggerCard'
import {
  countApprovalGates,
  createWorkflowTriggerDraft,
  WorkflowTriggerDraft,
} from '@/components/workflows/automationUtils'
import { createWorkflowTemplate, createWorkflowTrigger } from '@/services/workflows'

const initialNodes: Node[] = [
  {
    id: '1',
    position: { x: 250, y: 5 },
    data: { label: 'User Input' },
    style: { background: '#6366f1', color: '#fff', borderRadius: '12px', border: 'none', padding: '10px' },
  },
  {
    id: '2',
    position: { x: 250, y: 150 },
    data: { label: 'ExecutiveAgent' },
    style: { background: '#1e293b', color: '#fff', borderRadius: '12px', border: '2px solid #6366f1', padding: '10px' },
  },
]

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#6366f1' } },
]

const TEMPLATE_CATEGORIES = ['operations', 'sales', 'marketing', 'finance', 'support', 'custom']

type BuilderStep = {
  name: string
  tool: string
  description: string
  required_approval: boolean
}

function deriveBuilderSteps(nodes: Node[], requireApproval: boolean): BuilderStep[] {
  const ordered = [...nodes].sort((a, b) => {
    const yDiff = (a.position?.y ?? 0) - (b.position?.y ?? 0)
    if (yDiff !== 0) return yDiff
    return (a.position?.x ?? 0) - (b.position?.x ?? 0)
  })

  const steps = ordered
    .map((node, idx) => {
      const label = String((node.data as { label?: string })?.label || `Step ${idx + 1}`).trim()
      if (!label || label.toLowerCase() === 'user input') {
        return null
      }

      const normalized = label.toLowerCase()
      if (normalized.includes('research') || normalized.includes('search')) {
        return {
          name: label,
          tool: 'mcp_web_search',
          description: `Research the topic and gather decision-ready context for ${label}.`,
          required_approval: requireApproval,
        }
      }
      if (normalized.includes('report') || normalized.includes('analysis')) {
        return {
          name: label,
          tool: 'create_report',
          description: `Create a structured report for ${label}.`,
          required_approval: requireApproval,
        }
      }
      if (normalized.includes('track') || normalized.includes('metric') || normalized.includes('analytics')) {
        return {
          name: label,
          tool: 'track_event',
          description: `Track the milestone or signal for ${label}.`,
          required_approval: requireApproval,
        }
      }

      return {
        name: label,
        tool: 'create_task',
        description: label === 'ExecutiveAgent'
          ? 'Review the request and create the next concrete action for the workflow.'
          : `Complete workflow step: ${label}.`,
        required_approval: requireApproval,
      }
    })
    .filter((step): step is BuilderStep => step !== null)

  if (steps.length > 0) {
    return steps
  }

  return [{
    name: 'Executive Follow-Up',
    tool: 'create_task',
    description: 'Create the next concrete action for this workflow.',
    required_approval: requireApproval,
  }]
}

export function WorkflowBuilder() {
  const router = useRouter()
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [workflowName, setWorkflowName] = useState('Executive Follow-Up Loop')
  const [workflowDescription, setWorkflowDescription] = useState('A repeatable AI workflow for keeping work moving without manual coordination.')
  const [workflowCategory, setWorkflowCategory] = useState('operations')
  const [requireApproval, setRequireApproval] = useState(true)
  const [triggerDrafts, setTriggerDrafts] = useState<WorkflowTriggerDraft[]>([
    createWorkflowTriggerDraft({
      trigger_name: 'Daily operator review',
      trigger_type: 'schedule',
      schedule_frequency: 'daily',
    }),
  ])
  const [isSaving, setIsSaving] = useState(false)

  const builderSteps = useMemo(() => deriveBuilderSteps(nodes, requireApproval), [nodes, requireApproval])
  const approvalGateCount = useMemo(
    () => countApprovalGates([{ name: 'Builder Flow', steps: builderSteps }]),
    [builderSteps],
  )

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#6366f1' } }, eds)),
    [setEdges],
  )

  const addAgent = (type: string) => {
    const id = crypto.randomUUID()
    const newNode: Node = {
      id,
      position: { x: 100 + Math.random() * 320, y: 80 + Math.random() * 320 },
      data: { label: type },
      style: { background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '10px' },
    }
    setNodes((nds) => nds.concat(newNode))
  }

  const updateTriggerDraft = (index: number, trigger: WorkflowTriggerDraft) => {
    setTriggerDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? trigger : item)))
  }

  const addTriggerDraft = () => {
    setTriggerDrafts((current) => current.concat(createWorkflowTriggerDraft({
      trigger_name: `${workflowName || 'Workflow'} automation`,
      trigger_type: 'schedule',
      schedule_frequency: 'weekly',
    })))
  }

  const removeTriggerDraft = (index: number) => {
    setTriggerDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index))
  }

  const handleSave = async () => {
    if (!workflowName.trim()) {
      toast.error('Name this workflow before saving it.')
      return
    }

    setIsSaving(true)
    try {
      const created = await createWorkflowTemplate({
        name: workflowName.trim(),
        description: workflowDescription.trim(),
        category: workflowCategory,
        phases: [{ name: 'Builder Flow', steps: builderSteps }],
        is_generated: true,
      })

      let createdAutomationCount = 0
      let skippedAutomations = 0

      for (const draft of triggerDrafts) {
        const triggerName = draft.trigger_name.trim() || `${workflowName.trim()} automation`
        if (draft.trigger_type === 'event' && !draft.event_name.trim()) {
          skippedAutomations += 1
          continue
        }

        await createWorkflowTrigger({
          template_id: created.id,
          trigger_name: triggerName,
          trigger_type: draft.trigger_type,
          schedule_frequency: draft.trigger_type === 'schedule' ? draft.schedule_frequency : undefined,
          event_name: draft.trigger_type === 'event' ? draft.event_name.trim() : undefined,
          context: draft.context,
          enabled: draft.enabled,
          persona: draft.persona || undefined,
          run_source: 'agent_ui',
          queue_mode: draft.queue_mode,
          lane: draft.context.department ? 'department' : draft.lane,
        })
        createdAutomationCount += 1
      }

      if (createdAutomationCount > 0) {
        toast.success(`Workflow saved with ${createdAutomationCount} automation${createdAutomationCount === 1 ? '' : 's'}.`)
      } else {
        toast.success('Workflow saved. You can add automations from the editor next.')
      }

      if (skippedAutomations > 0) {
        toast.warning(`${skippedAutomations} automation${skippedAutomations === 1 ? ' was' : 's were'} skipped because required fields were missing.`)
      }

      router.push(`/dashboard/workflows/editor/${created.id}`)
    } catch (error) {
      console.error('Failed to save workflow draft', error)
      toast.error('Failed to save workflow automation plan.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 h-[760px] flex flex-col overflow-hidden">
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-600 rounded-lg text-white">
              <GitBranch size={18} />
            </div>
            <div>
              <h2 className="font-bold text-slate-800 dark:text-slate-100">Workflow Designer</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Shape the workflow, then decide how it should safely operate on its own.</p>
            </div>
          </div>
          <div className="h-6 w-[1px] bg-slate-200 dark:bg-slate-700 mx-2" />
          <div className="flex gap-2">
            <button
              onClick={() => addAgent('SpecialistAgent')}
              className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 transition"
            >
              <Plus size={14} /> Add Agent
            </button>
            <button
              onClick={() => addAgent('ResearchAgent')}
              className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 transition"
            >
              <Layers size={14} /> Add Logic
            </button>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => toast.message('Save the workflow first, then use the run console to launch it safely.')}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-600 rounded-xl text-sm font-bold hover:bg-emerald-100 transition"
          >
            <Play size={16} /> Run
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-200 dark:shadow-none disabled:opacity-50"
          >
            <Save size={16} /> {isSaving ? 'Saving...' : 'Save With Automations'}
          </button>
        </div>
      </div>

      <div className="flex-1 grid lg:grid-cols-[minmax(0,1fr)_360px] overflow-hidden">
        <div className="relative min-h-[420px] border-b lg:border-b-0 lg:border-r border-slate-200 dark:border-slate-800">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
          >
            <Background color="#cbd5e1" gap={20} />
            <Controls />
            <Panel position="top-right" className="bg-white/80 dark:bg-slate-900/80 backdrop-blur p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-lg">
              <h4 className="text-xs font-bold text-slate-400 uppercase mb-3">Components</h4>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                  <Box size={14} className="text-indigo-500" /> Executive Node
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                  <Box size={14} className="text-emerald-500" /> Task Node
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                  <Box size={14} className="text-amber-500" /> Data Source
                </div>
              </div>
            </Panel>
          </ReactFlow>
        </div>

        <aside className="overflow-y-auto bg-slate-50/70 dark:bg-slate-950/30 p-4 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Workflow Setup</p>
              <h3 className="mt-1 text-lg font-semibold text-slate-900">Make the workflow understandable before you automate it</h3>
            </div>
            <label className="space-y-1 text-sm text-slate-700 block">
              <span className="font-medium">Workflow name</span>
              <input
                className="w-full rounded-xl border border-slate-300 px-3 py-2"
                value={workflowName}
                onChange={(event) => setWorkflowName(event.target.value)}
              />
            </label>
            <label className="space-y-1 text-sm text-slate-700 block">
              <span className="font-medium">Description</span>
              <textarea
                className="w-full rounded-xl border border-slate-300 px-3 py-2 min-h-[88px]"
                value={workflowDescription}
                onChange={(event) => setWorkflowDescription(event.target.value)}
              />
            </label>
            <label className="space-y-1 text-sm text-slate-700 block">
              <span className="font-medium">Category</span>
              <select
                className="w-full rounded-xl border border-slate-300 px-3 py-2"
                value={workflowCategory}
                onChange={(event) => setWorkflowCategory(event.target.value)}
              >
                {TEMPLATE_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category.charAt(0).toUpperCase() + category.slice(1)}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
              <input
                type="checkbox"
                className="mt-1"
                checked={requireApproval}
                onChange={(event) => setRequireApproval(event.target.checked)}
              />
              <span>
                <span className="block font-medium text-slate-900">Require approval on builder-generated steps</span>
                <span className="block text-slate-500">Use this when the workflow can publish, spend, message customers, or change sensitive business records.</span>
              </span>
            </label>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Safety Snapshot</p>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">What ships with this workflow</h3>
              </div>
              <button
                onClick={addTriggerDraft}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
              >
                Add automation
              </button>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-2xl bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">Executable steps</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{builderSteps.length}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">Approval gates</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{approvalGateCount}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">Automations</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{triggerDrafts.length}</p>
              </div>
            </div>
            <p className="text-sm text-slate-500">Each automation is saved alongside the workflow so teams can understand exactly what will run, why, and under which safety guardrails.</p>
          </div>

          <div className="space-y-3">
            {triggerDrafts.map((trigger, index) => (
              <WorkflowTriggerCard
                key={trigger.id || `draft-${index}`}
                trigger={trigger}
                approvalGateCount={approvalGateCount}
                onChange={(next) => updateTriggerDraft(index, next)}
                onDelete={() => removeTriggerDraft(index)}
              />
            ))}
            {triggerDrafts.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
                No automations yet. Save just the workflow, or add a schedule/event hook now so it launches without manual babysitting.
              </div>
            ) : null}
          </div>
        </aside>
      </div>

      <div className="p-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-800 flex justify-between items-center px-6">
        <div className="flex gap-4">
          <span className="text-[10px] font-bold text-slate-400 uppercase">Nodes: {nodes.length}</span>
          <span className="text-[10px] font-bold text-slate-400 uppercase">Connections: {edges.length}</span>
          <span className="text-[10px] font-bold text-slate-400 uppercase">Approval gates: {approvalGateCount}</span>
        </div>
        <div className="flex items-center gap-2">
          <Settings size={14} className="text-slate-400" />
          <span className="text-[10px] font-medium text-slate-500">Auto-layout enabled</span>
        </div>
      </div>
    </div>
  )
}
