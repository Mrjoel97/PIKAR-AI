'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import PremiumShell from '@/components/layout/PremiumShell';
import {
  createWorkflowTemplate,
  diffWorkflowTemplate,
  getWorkflowTemplate,
  listWorkflowTools,
  publishWorkflowTemplate,
  updateWorkflowTemplate,
} from '@/services/workflows';
import { toast } from 'sonner';
import { ArrowPathIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline';

type Step = {
  name: string;
  tool: string;
  description?: string;
  required_approval?: boolean;
};

type Phase = {
  name: string;
  steps: Step[];
};

type DraftTemplate = {
  id?: string;
  name: string;
  description: string;
  category: string;
  phases: Phase[];
  lifecycle_status?: string;
  version?: number;
};

const EMPTY_TEMPLATE: DraftTemplate = {
  name: '',
  description: '',
  category: 'operations',
  phases: [{ name: 'Phase 1', steps: [{ name: 'Step 1', tool: 'create_task', description: '', required_approval: false }] }],
};

function normalizeSteps(rawSteps: unknown): Step[] {
  if (!Array.isArray(rawSteps)) return [];
  return rawSteps.map((step, idx) => {
    const s = (step && typeof step === 'object') ? step as Record<string, unknown> : {};
    return {
      name: typeof s.name === 'string' && s.name.trim() ? s.name : `Step ${idx + 1}`,
      tool: typeof s.tool === 'string' && s.tool.trim() ? s.tool : 'create_task',
      description: typeof s.description === 'string' ? s.description : '',
      required_approval: Boolean(s.required_approval),
    };
  });
}

function normalizePhases(rawPhases: unknown): Phase[] {
  let value = rawPhases;

  if (typeof value === 'string') {
    try {
      value = JSON.parse(value);
    } catch {
      return [...EMPTY_TEMPLATE.phases];
    }
  }

  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const maybePhases = (value as { phases?: unknown }).phases;
    if (Array.isArray(maybePhases)) {
      value = maybePhases;
    }
  }

  if (!Array.isArray(value)) {
    return [...EMPTY_TEMPLATE.phases];
  }

  const phases = value.map((phase, idx) => {
    const p = (phase && typeof phase === 'object') ? phase as Record<string, unknown> : {};
    return {
      name: typeof p.name === 'string' && p.name.trim() ? p.name : `Phase ${idx + 1}`,
      steps: normalizeSteps(p.steps),
    };
  });

  return phases.length ? phases : [...EMPTY_TEMPLATE.phases];
}

export default function WorkflowEditorPage() {
  const params = useParams<{ templateId: string }>();
  const router = useRouter();
  const templateId = Array.isArray(params?.templateId) ? params.templateId[0] : params?.templateId;
  const isNew = templateId === 'new';

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [template, setTemplate] = useState<DraftTemplate>(EMPTY_TEMPLATE);
  const [tools, setTools] = useState<string[]>([]);
  const [diffResult, setDiffResult] = useState<any>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const availableTools = await listWorkflowTools();
        if (mounted) setTools(availableTools);
        if (isNew) {
          try {
            const raw = localStorage.getItem('workflow_builder_draft');
            if (raw && mounted) {
              const parsed = JSON.parse(raw) as { nodes?: Array<{ data?: { label?: string } }>; edges?: unknown[] };
              const nodes = parsed.nodes || [];
              if (nodes.length > 0) {
                const steps = nodes.map((node, idx) => ({
                  name: node?.data?.label || `Step ${idx + 1}`,
                  tool: 'create_task',
                  description: '',
                  required_approval: false,
                }));
                setTemplate((prev) => ({
                  ...prev,
                  name: prev.name || 'Workflow Builder Draft',
                  category: prev.category || 'custom',
                  phases: [{ name: 'Builder Flow', steps }],
                }));
              }
              localStorage.removeItem('workflow_builder_draft');
            }
          } catch {
            // Ignore draft hydration issues and keep empty template.
          }
        }
        if (!isNew && templateId) {
          const data = await getWorkflowTemplate(templateId);
          if (mounted) {
            setTemplate({
              id: typeof data.id === 'string' ? data.id : undefined,
              name: typeof data.name === 'string' ? data.name : '',
              description: typeof data.description === 'string' ? data.description : '',
              category: typeof data.category === 'string' ? data.category : 'operations',
              phases: normalizePhases(data.phases),
              lifecycle_status: data.lifecycle_status,
              version: data.version,
            });
            const diff = await diffWorkflowTemplate(templateId);
            setDiffResult(diff);
          }
        }
      } catch (e) {
        toast.error('Failed to load workflow editor');
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [isNew, templateId]);

  const validationErrors = useMemo(() => {
    const errs: string[] = [];
    if (!template.name.trim()) errs.push('Template name is required');
    if (!template.category.trim()) errs.push('Category is required');
    if (!template.phases.length) errs.push('At least one phase is required');
    template.phases.forEach((phase, pIdx) => {
      if (!phase.name.trim()) errs.push(`Phase ${pIdx + 1} name is required`);
      if (!phase.steps.length) errs.push(`Phase ${pIdx + 1} must have at least one step`);
      phase.steps.forEach((step, sIdx) => {
        if (!step.name.trim()) errs.push(`Phase ${pIdx + 1} Step ${sIdx + 1}: name is required`);
        if (!step.tool.trim()) errs.push(`Phase ${pIdx + 1} Step ${sIdx + 1}: tool is required`);
      });
    });
    return errs;
  }, [template]);

  const onSave = async () => {
    if (validationErrors.length) {
      toast.error('Fix validation errors before saving');
      return;
    }
    setSaving(true);
    try {
      if (isNew) {
        const created = await createWorkflowTemplate({
          name: template.name,
          description: template.description,
          category: template.category,
          phases: template.phases,
        });
        toast.success('Draft created');
        router.replace(`/dashboard/workflows/editor/${created.id}`);
      } else if (templateId) {
        await updateWorkflowTemplate(templateId, {
          name: template.name,
          description: template.description,
          category: template.category,
          phases: template.phases,
        });
        toast.success('Draft saved');
      }
    } catch (e) {
      toast.error('Failed to save draft');
    } finally {
      setSaving(false);
    }
  };

  const onPublish = async () => {
    if (isNew || !templateId) {
      toast.error('Save draft before publishing');
      return;
    }
    if (validationErrors.length) {
      toast.error('Fix validation errors before publishing');
      return;
    }
    setPublishing(true);
    try {
      await publishWorkflowTemplate(templateId);
      toast.success('Template published');
      const latest = await getWorkflowTemplate(templateId);
      setTemplate((prev) => ({ ...prev, lifecycle_status: latest.lifecycle_status, version: latest.version }));
      setDiffResult(await diffWorkflowTemplate(templateId));
    } catch (e: any) {
      const msg = e?.message || 'Publish failed';
      toast.error(msg);
    } finally {
      setPublishing(false);
    }
  };

  const addPhase = () => {
    setTemplate((prev) => ({
      ...prev,
      phases: [...prev.phases, { name: `Phase ${prev.phases.length + 1}`, steps: [] }],
    }));
  };

  const addStep = (phaseIndex: number) => {
    setTemplate((prev) => {
      const phases = [...prev.phases];
      phases[phaseIndex] = {
        ...phases[phaseIndex],
        steps: [...phases[phaseIndex].steps, { name: `Step ${phases[phaseIndex].steps.length + 1}`, tool: 'create_task' }],
      };
      return { ...prev, phases };
    });
  };

  const removePhase = (phaseIndex: number) => {
    setTemplate((prev) => ({ ...prev, phases: prev.phases.filter((_, i) => i !== phaseIndex) }));
  };

  const removeStep = (phaseIndex: number, stepIndex: number) => {
    setTemplate((prev) => {
      const phases = [...prev.phases];
      phases[phaseIndex] = { ...phases[phaseIndex], steps: phases[phaseIndex].steps.filter((_, i) => i !== stepIndex) };
      return { ...prev, phases };
    });
  };

  if (loading) {
    return (
      <PremiumShell>
        <div className="max-w-6xl mx-auto p-8">Loading editor...</div>
      </PremiumShell>
    );
  }

  return (
    <PremiumShell>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Workflow Editor</h1>
            <p className="text-sm text-slate-500">
              {isNew ? 'Create a new workflow draft' : `Template ${template.lifecycle_status ?? 'draft'} v${template.version ?? '-'}`}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onSave}
              disabled={saving}
              className="inline-flex items-center px-4 py-2 rounded-xl bg-slate-900 text-white text-sm disabled:opacity-50"
            >
              {saving ? <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" /> : null}
              Save Draft
            </button>
            <button
              onClick={onPublish}
              disabled={publishing || isNew}
              className="inline-flex items-center px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm disabled:opacity-50"
            >
              {publishing ? <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" /> : null}
              Publish
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
              <input
                className="w-full border border-slate-300 rounded-lg px-3 py-2"
                value={template.name}
                placeholder="Template name"
                onChange={(e) => setTemplate((prev) => ({ ...prev, name: e.target.value }))}
              />
              <input
                className="w-full border border-slate-300 rounded-lg px-3 py-2"
                value={template.description}
                placeholder="Description"
                onChange={(e) => setTemplate((prev) => ({ ...prev, description: e.target.value }))}
              />
              <input
                className="w-full border border-slate-300 rounded-lg px-3 py-2"
                value={template.category}
                placeholder="Category"
                onChange={(e) => setTemplate((prev) => ({ ...prev, category: e.target.value }))}
              />
            </div>

            {template.phases.map((phase, pIdx) => (
              <div key={`${pIdx}-${phase.name}`} className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <input
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 mr-2"
                    value={phase.name}
                    placeholder={`Phase ${pIdx + 1}`}
                    onChange={(e) => {
                      const phases = [...template.phases];
                      phases[pIdx] = { ...phases[pIdx], name: e.target.value };
                      setTemplate((prev) => ({ ...prev, phases }));
                    }}
                  />
                  <button onClick={() => removePhase(pIdx)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg">
                    <TrashIcon className="w-5 h-5" />
                  </button>
                </div>

                {phase.steps.map((step, sIdx) => (
                  <div key={`${pIdx}-${sIdx}`} className="grid grid-cols-1 md:grid-cols-4 gap-2 bg-slate-50 rounded-lg p-3">
                    <input
                      className="border border-slate-300 rounded-md px-2 py-1"
                      placeholder="Step name"
                      value={step.name}
                      onChange={(e) => {
                        const phases = [...template.phases];
                        const steps = [...phases[pIdx].steps];
                        steps[sIdx] = { ...steps[sIdx], name: e.target.value };
                        phases[pIdx] = { ...phases[pIdx], steps };
                        setTemplate((prev) => ({ ...prev, phases }));
                      }}
                    />
                    <select
                      className="border border-slate-300 rounded-md px-2 py-1"
                      value={step.tool}
                      onChange={(e) => {
                        const phases = [...template.phases];
                        const steps = [...phases[pIdx].steps];
                        steps[sIdx] = { ...steps[sIdx], tool: e.target.value };
                        phases[pIdx] = { ...phases[pIdx], steps };
                        setTemplate((prev) => ({ ...prev, phases }));
                      }}
                    >
                      {tools.length > 0 ? (
                        tools.map((tool) => (
                          <option key={tool} value={tool}>
                            {tool}
                          </option>
                        ))
                      ) : (
                        <option value={step.tool || 'create_task'}>
                          {step.tool || 'create_task'}
                        </option>
                      )}
                    </select>
                    <input
                      className="border border-slate-300 rounded-md px-2 py-1"
                      placeholder="Description"
                      value={step.description ?? ''}
                      onChange={(e) => {
                        const phases = [...template.phases];
                        const steps = [...phases[pIdx].steps];
                        steps[sIdx] = { ...steps[sIdx], description: e.target.value };
                        phases[pIdx] = { ...phases[pIdx], steps };
                        setTemplate((prev) => ({ ...prev, phases }));
                      }}
                    />
                    <div className="flex items-center justify-between gap-2">
                      <label className="text-sm inline-flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={!!step.required_approval}
                          onChange={(e) => {
                            const phases = [...template.phases];
                            const steps = [...phases[pIdx].steps];
                            steps[sIdx] = { ...steps[sIdx], required_approval: e.target.checked };
                            phases[pIdx] = { ...phases[pIdx], steps };
                            setTemplate((prev) => ({ ...prev, phases }));
                          }}
                        />
                        Approval
                      </label>
                      <button onClick={() => removeStep(pIdx, sIdx)} className="p-1 text-red-500 hover:bg-red-100 rounded-md">
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}

                <button onClick={() => addStep(pIdx)} className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg bg-slate-100 hover:bg-slate-200">
                  <PlusIcon className="w-4 h-4 mr-1" /> Add Step
                </button>
              </div>
            ))}

            <button onClick={addPhase} className="inline-flex items-center px-4 py-2 rounded-xl bg-white border border-slate-300 hover:bg-slate-50">
              <PlusIcon className="w-4 h-4 mr-2" /> Add Phase
            </button>
          </div>

          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-2xl p-4">
              <h3 className="font-semibold text-slate-900 mb-2">Validation</h3>
              {validationErrors.length === 0 ? (
                <p className="text-sm text-emerald-700">No client-side validation issues.</p>
              ) : (
                <ul className="text-sm text-red-600 list-disc pl-5 space-y-1">
                  {validationErrors.map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              )}
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-4">
              <h3 className="font-semibold text-slate-900 mb-2">Draft vs Published Diff</h3>
              {!diffResult ? (
                <p className="text-sm text-slate-500">No diff loaded yet.</p>
              ) : (
                <pre className="text-xs text-slate-600 whitespace-pre-wrap overflow-x-auto">{JSON.stringify(diffResult.diff ?? diffResult, null, 2)}</pre>
              )}
            </div>
          </div>
        </div>
      </div>
    </PremiumShell>
  );
}
