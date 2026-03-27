'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import {
    ArrowLeft,
    CheckCircle2,
    Clock,
    AlertTriangle,
    Pause,
    Circle,
    MessageSquare,
    BarChart3,
    Settings,
    Trash2,
    Play,
    Target,
    Plus,
    Save,
    X,
} from 'lucide-react';
import { getWorkflowExecutionDetails, WorkflowExecutionDetails } from '@/services/workflows';
import {
    InitiativeApiError,
    InitiativeChecklistItem,
    InitiativeOperationalRecord,
    createInitiativeChecklistItem,
    deleteInitiative,
    deleteInitiativeChecklistItem,
    getInitiative,
    listInitiativeChecklistItems,
    listInitiativeChecklistEventsPage,
    startInitiativeJourneyWorkflow,
    updateInitiative,
    updateInitiativeChecklistItem,
} from '@/services/initiatives';
import { InitiativePhaseTracker } from '@/components/dashboard/InitiativePhaseTracker';

type InitiativePhase = 'ideation' | 'validation' | 'prototype' | 'build' | 'scale';
type InitiativeStatus = 'not_started' | 'in_progress' | 'completed' | 'blocked' | 'on_hold';

type Initiative = InitiativeOperationalRecord & {
    status: InitiativeStatus;
    phase: InitiativePhase;
    priority: string;
    phase_progress: Record<string, number>;
    created_at: string;
    template_id: string | null;
    workflow_execution_id: string | null;
    metadata: Record<string, unknown>;
    journey_outcomes_prompt?: string | null;
};

const STATUS_MAP: Record<InitiativeStatus, { label: string; color: string; icon: React.ReactNode }> = {
    not_started: { label: 'Not Started', color: 'bg-slate-100 text-slate-600', icon: <Circle size={14} /> },
    in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-700', icon: <Clock size={14} /> },
    completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700', icon: <CheckCircle2 size={14} /> },
    blocked: { label: 'Blocked', color: 'bg-red-100 text-red-700', icon: <AlertTriangle size={14} /> },
    on_hold: { label: 'On Hold', color: 'bg-amber-100 text-amber-700', icon: <Pause size={14} /> },
};

export default function InitiativeDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;
    const [initiative, setInitiative] = useState<Initiative | null>(null);
    const [loading, setLoading] = useState(true);
    const [updating, setUpdating] = useState(false);
    const [startingWorkflow, setStartingWorkflow] = useState(false);
    const [savingJourneyInputs, setSavingJourneyInputs] = useState(false);
    const [journeyOutcomesPrompt, setJourneyOutcomesPrompt] = useState<string | null>(null);
    const [workflowDetails, setWorkflowDetails] = useState<WorkflowExecutionDetails | null>(null);
    const [loadingWorkflowDetails, setLoadingWorkflowDetails] = useState(false);
    const [missingInputs, setMissingInputs] = useState<string[]>([]);
    const [desiredOutcomesInput, setDesiredOutcomesInput] = useState('');
    const [timelineInput, setTimelineInput] = useState('');
    const [checklistItems, setChecklistItems] = useState<InitiativeChecklistItem[]>([]);
    const [loadingChecklist, setLoadingChecklist] = useState(false);
    const [newChecklistTitle, setNewChecklistTitle] = useState('');
    const [newChecklistOwner, setNewChecklistOwner] = useState('');
    const [newChecklistDueAt, setNewChecklistDueAt] = useState('');
    const [checklistStatusFilter, setChecklistStatusFilter] = useState<'all' | 'pending' | 'in_progress' | 'completed' | 'blocked' | 'skipped'>('all');
    const [checklistSortBy, setChecklistSortBy] = useState<'sort_order' | 'updated_at' | 'due_at'>('sort_order');
    const [checklistSortOrder, setChecklistSortOrder] = useState<'asc' | 'desc'>('asc');
    const [checklistOffset, setChecklistOffset] = useState(0);
    const [checklistHasMore, setChecklistHasMore] = useState(false);
    const [checklistEvents, setChecklistEvents] = useState<Array<{
        id: string;
        event_type: string;
        item_id?: string | null;
        actor_user_id?: string | null;
        created_at: string;
        payload?: Record<string, unknown>;
    }>>([]);
    const [loadingChecklistEvents, setLoadingChecklistEvents] = useState(false);
    const [eventsOffset, setEventsOffset] = useState(0);
    const [eventsHasMore, setEventsHasMore] = useState(false);

    const breadcrumbItems = [
        { label: 'Home', href: '/dashboard' },
        { label: 'Initiatives', href: '/dashboard/initiatives' },
        { label: initiative?.title || 'Loading...' },
    ];

    useEffect(() => {
        if (id) fetchInitiative();
    }, [id]);

    useEffect(() => {
        setJourneyOutcomesPrompt(initiative?.journey_outcomes_prompt ?? null);
    }, [initiative?.journey_outcomes_prompt]);

    async function fetchInitiative() {
        try {
            const data = await getInitiative(id);
            setInitiative(data as Initiative);
            const metadata = (data?.metadata || {}) as { desired_outcomes?: string; timeline?: string };
            setDesiredOutcomesInput(metadata.desired_outcomes || '');
            setTimelineInput(metadata.timeline || '');
            setJourneyOutcomesPrompt(data?.journey_outcomes_prompt ?? null);
        } catch (err) {
            console.error('Error fetching initiative:', err);
        } finally {
            setLoading(false);
        }
    }

    const fetchChecklist = useCallback(async (initiativeId: string, offset = 0, append = false) => {
        setLoadingChecklist(true);
        try {
            const pageSize = 25;
            const items = await listInitiativeChecklistItems(initiativeId, {
                phase: initiative?.phase,
                status: checklistStatusFilter === 'all' ? undefined : checklistStatusFilter,
                limit: pageSize,
                offset,
                sort_by: checklistSortBy,
                sort_order: checklistSortOrder,
            });
            setChecklistItems((prev) => (append ? [...prev, ...items] : items));
            setChecklistOffset(offset + items.length);
            setChecklistHasMore(items.length === pageSize);
        } catch (err) {
            console.error('Error fetching checklist items:', err);
        } finally {
            setLoadingChecklist(false);
        }
    }, [initiative?.phase, checklistStatusFilter, checklistSortBy, checklistSortOrder]);

    const fetchChecklistEvents = useCallback(async (initiativeId: string, offset = 0, append = false) => {
        setLoadingChecklistEvents(true);
        try {
            const pageSize = 10;
            const result = await listInitiativeChecklistEventsPage(initiativeId, {
                limit: pageSize,
                offset,
            });
            setChecklistEvents((prev) => (append ? [...prev, ...result.events] : result.events));
            setEventsOffset(offset + result.events.length);
            setEventsHasMore(result.events.length === pageSize);
        } catch (err) {
            console.error('Error fetching checklist events:', err);
        } finally {
            setLoadingChecklistEvents(false);
        }
    }, []);

    useEffect(() => {
        if (initiative?.id) {
            fetchChecklist(initiative.id, 0, false);
            fetchChecklistEvents(initiative.id, 0, false);
        }
    }, [initiative?.id, fetchChecklist, fetchChecklistEvents]);

    useEffect(() => {
        const executionId = initiative?.workflow_execution_id;
        if (!executionId) {
            setWorkflowDetails(null);
            return;
        }
        let cancelled = false;
        (async () => {
            setLoadingWorkflowDetails(true);
            try {
                const details = await getWorkflowExecutionDetails(executionId);
                if (!cancelled) setWorkflowDetails(details);
            } catch {
                if (!cancelled) setWorkflowDetails(null);
            } finally {
                if (!cancelled) setLoadingWorkflowDetails(false);
            }
        })();
        return () => { cancelled = true; };
    }, [initiative?.workflow_execution_id]);

    const workflowOutcomeSummary = workflowDetails?.execution?.outcome_summary ?? null;
    const workflowOutcomeText = typeof workflowOutcomeSummary?.summary === 'string' ? workflowOutcomeSummary.summary : '';
    const workflowOutcomeTools = Array.isArray(workflowOutcomeSummary?.tools_used) ? workflowOutcomeSummary.tools_used : [];
    const workflowOutcomeStepsCompleted = typeof workflowOutcomeSummary?.steps_completed === 'number' ? workflowOutcomeSummary.steps_completed : null;
    const workflowOutcomeArtifacts = Array.isArray(workflowOutcomeSummary?.artifacts) ? workflowOutcomeSummary.artifacts : [];
    const workflowOutcomeNextActions = Array.isArray(workflowOutcomeSummary?.next_actions) ? workflowOutcomeSummary.next_actions : [];
    const PHASES = [
        'ideation',
        'validation',
        'prototype',
        'build',
        'scale',
    ] as InitiativePhase[];

    const handleAdvancePhase = useCallback(async () => {
        if (!initiative) return;
        setUpdating(true);
        try {
            const currentIdx = PHASES.indexOf(initiative.phase);
            const nextPhase = currentIdx < PHASES.length - 1 ? PHASES[currentIdx + 1] : null;
            const nextMetadata = {
                ...(initiative.metadata || {}),
                manual_override: true,
                manual_override_at: new Date().toISOString(),
            };

            if (nextPhase) {
                const newPhaseProgress = {
                    ...initiative.phase_progress,
                    [initiative.phase]: 100,
                };
                const overallProgress = Math.round(((currentIdx + 1) / 5) * 100);

                const data = await updateInitiative(initiative.id, {
                    phase: nextPhase,
                    phase_progress: newPhaseProgress,
                    progress: overallProgress,
                    status: 'in_progress',
                    metadata: nextMetadata,
                });
                setInitiative(data as Initiative);
            } else {
                const newPhaseProgress = {
                    ...initiative.phase_progress,
                    [initiative.phase]: 100,
                };
                const data = await updateInitiative(initiative.id, {
                    phase_progress: newPhaseProgress,
                    progress: 100,
                    status: 'completed',
                    metadata: nextMetadata,
                });
                setInitiative(data as Initiative);
            }
        } catch (err) {
            console.error('Error advancing phase:', err);
        } finally {
            setUpdating(false);
        }
    }, [initiative]);

    const handleStatusChange = useCallback(async (newStatus: InitiativeStatus) => {
        if (!initiative) return;
        setUpdating(true);
        try {
            const data = await updateInitiative(initiative.id, { status: newStatus });
            setInitiative(data as Initiative);
        } catch (err) {
            console.error('Error updating status:', err);
        } finally {
            setUpdating(false);
        }
    }, [initiative]);

    const handleDelete = useCallback(async () => {
        if (!initiative || !confirm('Are you sure you want to delete this initiative?')) return;
        try {
            await deleteInitiative(initiative.id);
            router.push('/dashboard/initiatives');
        } catch (err) {
            console.error('Error deleting initiative:', err);
        }
    }, [initiative, router]);

    const handleStartJourneyWorkflow = useCallback(async () => {
        if (!initiative?.id || !(initiative.metadata as { journey_id?: string })?.journey_id) return;
        setStartingWorkflow(true);
        setMissingInputs([]);
        try {
            const data = await startInitiativeJourneyWorkflow(initiative.id);
            await fetchInitiative();
            if (data.workflow_execution_id) {
                try {
                    const details = await getWorkflowExecutionDetails(data.workflow_execution_id);
                    setWorkflowDetails(details);
                } catch {
                    // Ignore details fetch errors after successful start.
                }
            }
            router.push(`/dashboard/workspace?context=initiative&initiativeId=${initiative.id}&fromJourney=1`);
        } catch (err) {
            if (err instanceof InitiativeApiError) {
                const detail = err.detail;
                const missing = detail && typeof detail === 'object'
                    ? (detail as { missing_inputs?: unknown[] }).missing_inputs
                    : null;
                if (Array.isArray(missing) && missing.length > 0) {
                    setMissingInputs(missing.filter((value): value is string => typeof value === 'string'));
                }
                alert(err.message || 'Failed to start journey workflow');
            } else {
                const message = err instanceof Error ? err.message : String(err);
                alert(message || 'Failed to start journey workflow');
            }
        } finally {
            setStartingWorkflow(false);
        }
    }, [initiative, router]);

    const handleSaveJourneyInputs = useCallback(async () => {
        if (!initiative?.id) return;
        setSavingJourneyInputs(true);
        try {
            const nextMetadata = {
                ...(initiative.metadata || {}),
                desired_outcomes: desiredOutcomesInput.trim(),
                timeline: timelineInput.trim(),
            };
            const data = await updateInitiative(initiative.id, { metadata: nextMetadata });
            setInitiative(data as Initiative);
            setMissingInputs([]);
        } catch (err) {
            console.error('Error saving journey inputs:', err);
            alert('Failed to save outcomes/timeline');
        } finally {
            setSavingJourneyInputs(false);
        }
    }, [initiative, desiredOutcomesInput, timelineInput]);

    const handleCreateChecklistItem = useCallback(async () => {
        if (!initiative?.id || !newChecklistTitle.trim()) return;
        try {
            const created = await createInitiativeChecklistItem(initiative.id, {
                title: newChecklistTitle.trim(),
                phase: initiative.phase,
                owner_label: newChecklistOwner.trim() || undefined,
                due_at: newChecklistDueAt ? new Date(newChecklistDueAt).toISOString() : undefined,
                status: 'pending',
            });
            setChecklistItems((prev) => [...prev, created]);
            fetchChecklist(initiative.id, 0, false);
            setNewChecklistTitle('');
            setNewChecklistOwner('');
            setNewChecklistDueAt('');
            fetchChecklistEvents(initiative.id, 0, false);
        } catch (err) {
            console.error('Error creating checklist item:', err);
            alert('Failed to create checklist item');
        }
    }, [initiative, newChecklistTitle, newChecklistOwner, newChecklistDueAt, fetchChecklistEvents, fetchChecklist]);

    const handleToggleChecklistItem = useCallback(async (item: InitiativeChecklistItem) => {
        if (!initiative?.id) return;
        const nextStatus = item.status === 'completed' ? 'pending' : 'completed';
        try {
            const updated = await updateInitiativeChecklistItem(initiative.id, item.id, { status: nextStatus });
            setChecklistItems((prev) => prev.map((x) => (x.id === item.id ? updated : x)));
            fetchChecklist(initiative.id, 0, false);
            fetchChecklistEvents(initiative.id, 0, false);
        } catch (err) {
            console.error('Error updating checklist item:', err);
            alert('Failed to update checklist item');
        }
    }, [initiative, fetchChecklistEvents, fetchChecklist]);

    const handleSaveChecklistItem = useCallback(async (item: InitiativeChecklistItem) => {
        if (!initiative?.id) return;
        try {
            const updated = await updateInitiativeChecklistItem(initiative.id, item.id, {
                title: item.title,
                description: item.description || undefined,
                owner_label: item.owner_label || undefined,
                due_at: item.due_at || null,
                evidence: item.evidence || [],
                sort_order: item.sort_order,
            });
            setChecklistItems((prev) => prev.map((x) => (x.id === item.id ? updated : x)));
            fetchChecklist(initiative.id, 0, false);
            fetchChecklistEvents(initiative.id, 0, false);
        } catch (err) {
            console.error('Error saving checklist item:', err);
            alert('Failed to save checklist item');
        }
    }, [initiative, fetchChecklistEvents, fetchChecklist]);

    const handleDeleteChecklistItem = useCallback(async (item: InitiativeChecklistItem) => {
        if (!initiative?.id) return;
        if (!confirm('Delete this checklist item?')) return;
        try {
            await deleteInitiativeChecklistItem(initiative.id, item.id);
            setChecklistItems((prev) => prev.filter((x) => x.id !== item.id));
            fetchChecklist(initiative.id, 0, false);
            fetchChecklistEvents(initiative.id, 0, false);
        } catch (err) {
            console.error('Error deleting checklist item:', err);
            alert('Failed to delete checklist item');
        }
    }, [initiative, fetchChecklistEvents, fetchChecklist]);

    const updateChecklistDraft = useCallback((itemId: string, patch: Partial<InitiativeChecklistItem>) => {
        setChecklistItems((prev) => prev.map((x) => (x.id === itemId ? { ...x, ...patch } : x)));
    }, []);

    if (loading) {
        return (
            <PremiumShell>
                <div className="flex items-center justify-center py-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-2 border-teal-500 border-t-transparent" />
                </div>
            </PremiumShell>
        );
    }

    if (!initiative) {
        return (
            <PremiumShell>
                <div className="text-center py-20">
                    <h2 className="text-xl font-semibold text-slate-700">Initiative not found</h2>
                    <button onClick={() => router.push('/dashboard/initiatives')} className="mt-4 text-teal-600 hover:underline">
                        Back to initiatives
                    </button>
                </div>
            </PremiumShell>
        );
    }

    const currentPhaseIdx = ['ideation', 'validation', 'prototype', 'build', 'scale'].indexOf(initiative.phase);
    const statusInfo = STATUS_MAP[initiative.status] || STATUS_MAP.not_started;
    const templatePhases = (initiative.metadata?.phases as Array<{ name: string; steps: string[] }>) || null;
    const kpis = (initiative.metadata?.kpis as string[]) || [];
    const checklistForPhase = checklistItems.filter((x) => x.phase === initiative.phase);
    const templatePhaseSteps = checklistForPhase.length
        ? checklistForPhase.map((x) => x.title)
        : templatePhases?.[currentPhaseIdx]?.steps;

    return (
        <PremiumShell>
            <div className="mb-6">
                <Breadcrumb items={breadcrumbItems} />
            </div>

            <motion.div
                className="max-w-5xl mx-auto space-y-6"
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                {/* Back button */}
                <button
                    onClick={() => router.push('/dashboard/initiatives')}
                    className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
                >
                    <ArrowLeft size={16} /> All Initiatives
                </button>

                {/* Gradient Icon Header */}
                <div className="flex items-center gap-4 mb-6">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-500 shadow-lg shadow-teal-200">
                        <Target className="h-6 w-6 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 truncate">{initiative.title}</h1>
                        {initiative.description && <p className="mt-0.5 text-sm text-slate-500">{initiative.description}</p>}
                    </div>
                </div>

                {/* Header */}
                <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] sm:p-8">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                        <div className="flex-1">
                            <div className="flex items-center gap-2 flex-wrap mb-2">
                                <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${statusInfo.color}`}>
                                    {statusInfo.icon} {statusInfo.label}
                                </span>
                                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 capitalize border border-blue-100">
                                    {initiative.priority} priority
                                </span>
                            </div>
                            <h1 className="text-2xl sm:text-3xl font-outfit font-bold text-slate-900">{initiative.title}</h1>
                            {initiative.description && (
                                <p className="text-slate-500 mt-2 max-w-2xl">{initiative.description}</p>
                            )}
                            <p className="text-xs text-slate-400 mt-2">
                                Created {new Date(initiative.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                            </p>
                        </div>

                        <div className="flex items-center gap-2">
                            {initiative.status !== 'completed' && (
                                <select
                                    value={initiative.status}
                                    onChange={(e) => handleStatusChange(e.target.value as InitiativeStatus)}
                                    disabled={updating}
                                    className="px-3 py-2 rounded-xl border border-slate-200 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                                >
                                    <option value="not_started">Not Started</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="blocked">Blocked</option>
                                    <option value="on_hold">On Hold</option>
                                    <option value="completed">Completed</option>
                                </select>
                            )}
                            <button
                                onClick={handleDelete}
                                className="p-2 text-slate-400 hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
                                title="Delete initiative"
                            >
                                <Trash2 size={18} />
                            </button>
                        </div>
                    </div>

                    {/* Overall Progress */}
                    <div className="mt-6">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-slate-600">Overall Progress</span>
                            <span className="text-sm font-bold text-slate-700">{initiative.progress}%</span>
                        </div>
                        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                            <motion.div
                                className="h-full bg-gradient-to-r from-teal-400 to-emerald-500 rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${initiative.progress}%` }}
                                transition={{ duration: 0.8, ease: 'easeOut' }}
                            />
                        </div>
                    </div>
                </div>

                {initiative.workflow_execution_id && (
                    <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] sm:p-8">
                        <div className="flex items-start justify-between gap-4 mb-4">
                            <div>
                                <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Workflow Execution</h2>
                                <p className="text-xs text-slate-500 mt-1">
                                    Review the linked run, its outputs, and the clearest next move for this initiative.
                                </p>
                            </div>
                        </div>
                        {loadingWorkflowDetails ? (
                            <p className="text-sm text-slate-500">Loading workflow status...</p>
                        ) : workflowDetails ? (
                            <div className="space-y-4 text-sm">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                                        <p className="text-xs uppercase tracking-wide text-slate-500">Template</p>
                                        <p className="mt-1 font-medium text-slate-800">{workflowDetails.template_name}</p>
                                    </div>
                                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                                        <p className="text-xs uppercase tracking-wide text-slate-500">Status</p>
                                        <p className="mt-1 font-medium capitalize text-slate-800">{workflowDetails.execution.status.replace('_', ' ')}</p>
                                    </div>
                                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                                        <p className="text-xs uppercase tracking-wide text-slate-500">Current phase index</p>
                                        <p className="mt-1 font-medium text-slate-800">{workflowDetails.current_phase_index}</p>
                                    </div>
                                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                                        <p className="text-xs uppercase tracking-wide text-slate-500">Current step index</p>
                                        <p className="mt-1 font-medium text-slate-800">{workflowDetails.current_step_index}</p>
                                    </div>
                                </div>

                                {workflowOutcomeSummary && (
                                    <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                                        <h3 className="text-sm font-semibold text-emerald-900">Outcome summary</h3>
                                        <p className="mt-2 whitespace-pre-wrap text-sm text-emerald-800">{workflowOutcomeText}</p>
                                        {workflowOutcomeTools.length > 0 && (
                                            <p className="mt-2 text-xs text-emerald-700">
                                                Tools: {workflowOutcomeTools.join(', ')}
                                                {workflowOutcomeStepsCompleted != null && <> · {workflowOutcomeStepsCompleted} step(s) completed</>}
                                            </p>
                                        )}
                                        {workflowOutcomeArtifacts.length > 0 && (
                                            <div className="mt-3">
                                                <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-900/80">Artifacts</h4>
                                                <ul className="mt-2 space-y-2 text-xs text-emerald-800">
                                                    {workflowOutcomeArtifacts.map((artifact, index) => (
                                                        <li key={`${artifact.type}-${artifact.label}-${index}`} className="rounded-lg border border-emerald-100 bg-white/70 px-3 py-2">
                                                            <span className="font-medium">{artifact.label}</span>
                                                            {artifact.value ? <> · {artifact.value}</> : null}
                                                            {artifact.href ? (
                                                                <a href={artifact.href} target="_blank" rel="noreferrer" className="ml-2 text-emerald-700 underline underline-offset-2">
                                                                    Open
                                                                </a>
                                                            ) : null}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {workflowOutcomeNextActions.length > 0 && (
                                            <div className="mt-3">
                                                <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-900/80">Next actions</h4>
                                                <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-emerald-800">
                                                    {workflowOutcomeNextActions.map((action, index) => (
                                                        <li key={`${action}-${index}`}>{action}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ) : (
                            <p className="text-sm text-slate-500">Workflow is linked but current execution details are unavailable.</p>
                        )}
                    </div>
                )}
                {/* Phase Tracker Pipeline */}
                <InitiativePhaseTracker
                    phase={initiative.phase}
                    phaseProgress={initiative.phase_progress}
                    status={initiative.status}
                    onAdvancePhase={handleAdvancePhase}
                    updating={updating}
                    templatePhaseSteps={templatePhaseSteps}
                />

                <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] sm:p-8">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Stage Checklist</h2>
                            <p className="text-xs text-slate-500 mt-1">
                                Trackable, persisted checklist for current stage: <span className="font-medium capitalize">{initiative.phase}</span>
                            </p>
                        </div>
                        <div className="text-sm text-slate-600">
                            {checklistForPhase.filter((i) => i.status === 'completed').length}/{checklistForPhase.length} completed
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-2 mb-4">
                        <select
                            value={checklistStatusFilter}
                            onChange={(e) => setChecklistStatusFilter(e.target.value as typeof checklistStatusFilter)}
                            className="sm:col-span-4 rounded-xl border border-slate-200 p-2.5 text-sm"
                        >
                            <option value="all">All statuses</option>
                            <option value="pending">Pending</option>
                            <option value="in_progress">In Progress</option>
                            <option value="completed">Completed</option>
                            <option value="blocked">Blocked</option>
                            <option value="skipped">Skipped</option>
                        </select>
                        <select
                            value={checklistSortBy}
                            onChange={(e) => setChecklistSortBy(e.target.value as typeof checklistSortBy)}
                            className="sm:col-span-4 rounded-xl border border-slate-200 p-2.5 text-sm"
                        >
                            <option value="sort_order">Sort: Manual</option>
                            <option value="updated_at">Sort: Updated Time</option>
                            <option value="due_at">Sort: Due Date</option>
                        </select>
                        <select
                            value={checklistSortOrder}
                            onChange={(e) => setChecklistSortOrder(e.target.value as typeof checklistSortOrder)}
                            className="sm:col-span-4 rounded-xl border border-slate-200 p-2.5 text-sm"
                        >
                            <option value="asc">Ascending</option>
                            <option value="desc">Descending</option>
                        </select>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-2 mb-4">
                        <input
                            value={newChecklistTitle}
                            onChange={(e) => setNewChecklistTitle(e.target.value)}
                            placeholder="Add checklist item title"
                            className="sm:col-span-5 rounded-xl border border-slate-200 p-2.5 text-sm"
                        />
                        <input
                            value={newChecklistOwner}
                            onChange={(e) => setNewChecklistOwner(e.target.value)}
                            placeholder="Owner"
                            className="sm:col-span-3 rounded-xl border border-slate-200 p-2.5 text-sm"
                        />
                        <input
                            type="date"
                            value={newChecklistDueAt}
                            onChange={(e) => setNewChecklistDueAt(e.target.value)}
                            className="sm:col-span-2 rounded-xl border border-slate-200 p-2.5 text-sm"
                        />
                        <button
                            onClick={handleCreateChecklistItem}
                            className="sm:col-span-2 inline-flex items-center justify-center gap-1 rounded-xl bg-teal-600 text-white text-sm font-medium px-3 py-2.5 hover:bg-teal-700"
                        >
                            <Plus size={14} />
                            Add
                        </button>
                    </div>

                    {loadingChecklist ? (
                        <p className="text-sm text-slate-500">Loading checklist...</p>
                    ) : checklistForPhase.length === 0 ? (
                        <p className="text-sm text-slate-500">No checklist items for this phase yet.</p>
                    ) : (
                        <div className="space-y-2">
                            {checklistForPhase.map((item) => (
                                <div key={item.id} className="border border-slate-100 rounded-xl p-3">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex items-start gap-2 flex-1">
                                            <input
                                                type="checkbox"
                                                checked={item.status === 'completed'}
                                                onChange={() => handleToggleChecklistItem(item)}
                                                className="mt-1"
                                            />
                                            <input
                                                value={item.title}
                                                onChange={(e) => updateChecklistDraft(item.id, { title: e.target.value })}
                                                className="w-full text-sm font-medium text-slate-800 rounded-lg border border-slate-200 px-2 py-1.5"
                                            />
                                        </div>
                                        <button
                                            onClick={() => handleDeleteChecklistItem(item)}
                                            className="text-xs text-red-600 inline-flex items-center gap-1"
                                        >
                                            <X size={14} />
                                            Delete
                                        </button>
                                    </div>
                                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-2 mt-2">
                                        <input
                                            value={item.owner_label || ''}
                                            onChange={(e) => updateChecklistDraft(item.id, { owner_label: e.target.value })}
                                            placeholder="Owner"
                                            className="sm:col-span-3 rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
                                        />
                                        <input
                                            type="date"
                                            value={item.due_at ? new Date(item.due_at).toISOString().slice(0, 10) : ''}
                                            onChange={(e) => {
                                                const iso = e.target.value ? new Date(`${e.target.value}T00:00:00`).toISOString() : null;
                                                updateChecklistDraft(item.id, { due_at: iso });
                                            }}
                                            className="sm:col-span-3 rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
                                        />
                                        <input
                                            value={Array.isArray(item.evidence) ? item.evidence.join(', ') : ''}
                                            onChange={(e) => {
                                                const values = e.target.value
                                                    .split(',')
                                                    .map((x) => x.trim())
                                                    .filter(Boolean);
                                                updateChecklistDraft(item.id, { evidence: values });
                                            }}
                                            placeholder="Evidence links (comma-separated)"
                                            className="sm:col-span-5 rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
                                        />
                                        <button
                                            onClick={() => handleSaveChecklistItem(item)}
                                            className="sm:col-span-1 inline-flex items-center justify-center rounded-lg bg-slate-900 text-white px-2 py-1.5"
                                            title="Save checklist item"
                                        >
                                            <Save size={12} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                            {checklistHasMore && (
                                <button
                                    onClick={() => initiative?.id && fetchChecklist(initiative.id, checklistOffset, true)}
                                    disabled={loadingChecklist}
                                    className="mt-2 inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                                >
                                    {loadingChecklist ? 'Loading...' : 'Load more items'}
                                </button>
                            )}
                        </div>
                    )}
                </div>

                <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] sm:p-8">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Checklist Activity Feed</h2>
                            <p className="text-xs text-slate-500 mt-1">
                                Audited changes across checklist items for this initiative.
                            </p>
                        </div>
                    </div>
                    {loadingChecklistEvents && checklistEvents.length === 0 ? (
                        <p className="text-sm text-slate-500">Loading activity...</p>
                    ) : checklistEvents.length === 0 ? (
                        <p className="text-sm text-slate-500">No checklist activity yet.</p>
                    ) : (
                        <div className="space-y-2">
                            {checklistEvents.map((evt) => (
                                <div key={evt.id} className="rounded-xl border border-slate-100 p-3 text-sm">
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-700 font-medium">
                                            {evt.event_type.replace('_', ' ')}
                                        </span>
                                        <span className="text-xs text-slate-400">
                                            {new Date(evt.created_at).toLocaleString()}
                                        </span>
                                    </div>
                                    {evt.item_id && (
                                        <p className="text-xs text-slate-500 mt-1">
                                            Item: <span className="font-mono">{evt.item_id}</span>
                                        </p>
                                    )}
                                    {evt.actor_user_id && (
                                        <p className="text-xs text-slate-500 mt-0.5">
                                            Actor: <span className="font-mono">{evt.actor_user_id}</span>
                                        </p>
                                    )}
                                </div>
                            ))}
                            {eventsHasMore && (
                                <button
                                    onClick={() => initiative?.id && fetchChecklistEvents(initiative.id, eventsOffset, true)}
                                    disabled={loadingChecklistEvents}
                                    className="mt-2 inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                                >
                                    {loadingChecklistEvents ? 'Loading...' : 'Load more'}
                                </button>
                            )}
                        </div>
                    )}
                </div>

                {/* Desired outcomes & timeline (journey-sourced initiatives) */}
                {(initiative.metadata?.journey_id || initiative.metadata?.desired_outcomes != null) && (
                    <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] sm:p-8">
                        <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-4 flex items-center gap-2">
                            <CheckCircle2 size={20} className="text-teal-600" />
                            Desired outcomes
                        </h2>
                        <div className="space-y-3">
                            <textarea
                                value={desiredOutcomesInput}
                                onChange={(e) => setDesiredOutcomesInput(e.target.value)}
                                rows={4}
                                placeholder={journeyOutcomesPrompt || 'What does success look like for this initiative?'}
                                className="w-full rounded-xl border border-slate-200 p-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                            />
                            <input
                                value={timelineInput}
                                onChange={(e) => setTimelineInput(e.target.value)}
                                placeholder="Timeline or key milestones"
                                className="w-full rounded-xl border border-slate-200 p-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                            />
                            {missingInputs.length > 0 && (
                                <p className="text-sm text-amber-700">
                                    Missing required inputs: {missingInputs.join(', ')}
                                </p>
                            )}
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handleSaveJourneyInputs}
                                    disabled={savingJourneyInputs}
                                    className="inline-flex items-center gap-2 px-3 py-2 bg-teal-50 text-teal-700 rounded-xl text-sm font-medium hover:bg-teal-100 transition-colors border border-teal-100 disabled:opacity-60"
                                >
                                    <Target size={16} />
                                    {savingJourneyInputs ? 'Saving...' : 'Save outcomes & timeline'}
                                </button>
                                <button
                                    onClick={() => {
                                        const params = new URLSearchParams({
                                            context: 'initiative',
                                            initiativeId: initiative.id,
                                            title: initiative.title?.slice(0, 200) || initiative.id,
                                            fromJourney: '1',
                                        });
                                        if (journeyOutcomesPrompt?.trim()) params.set('outcomesPrompt', journeyOutcomesPrompt.trim());
                                        router.push(`/dashboard/workspace?${params.toString()}`);
                                    }}
                                    className="inline-flex items-center gap-2 px-3 py-2 bg-white text-slate-700 rounded-xl text-sm font-medium border border-slate-200 hover:bg-slate-50 transition-colors"
                                >
                                    Discuss with Agent
                                </button>
                            </div>
                        </div>
                        {/* Run journey workflow (only when from journey) */}
                        {(initiative.metadata as { journey_id?: string })?.journey_id && (
                            <div className="mt-4 pt-4 border-t border-slate-100">
                                <button
                                    onClick={handleStartJourneyWorkflow}
                                    disabled={startingWorkflow}
                                    className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 text-white rounded-xl text-sm font-semibold hover:bg-teal-700 transition-colors disabled:opacity-50"
                                >
                                    {startingWorkflow ? (
                                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                                    ) : (
                                        <Play size={16} />
                                    )}
                                    Run journey workflow
                                </button>
                                <p className="text-xs text-slate-400 mt-1.5">
                                    Starts the journey&apos;s primary workflow for this initiative. You can also do this from &quot;Discuss with Agent&quot; after setting outcomes.
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* KPIs Section (if from template) */}
                {kpis.length > 0 && (
                    <div className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] sm:p-8">
                        <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-4 flex items-center gap-2">
                            <BarChart3 size={20} className="text-teal-600" />
                            Key Performance Indicators
                        </h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {kpis.map((kpi, i) => (
                                <div key={i} className="rounded-xl border border-slate-100 p-4 bg-slate-50">
                                    <p className="text-sm font-medium text-slate-600">{kpi}</p>
                                    <p className="text-lg font-bold text-slate-400 mt-1">--</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Quick Actions */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <button
                        onClick={() => {
                            const params = new URLSearchParams({
                                context: 'initiative',
                                initiativeId: initiative.id,
                                title: initiative.title?.slice(0, 200) || initiative.id,
                            });
                            if (initiative.metadata?.journey_id) {
                                params.set('fromJourney', '1');
                                if (journeyOutcomesPrompt?.trim()) params.set('outcomesPrompt', journeyOutcomesPrompt.trim());
                            }
                            router.push(`/dashboard/workspace?${params.toString()}`);
                        }}
                        className="flex items-center gap-3 p-4 bg-white rounded-[28px] border border-slate-100/80 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] hover:-translate-y-0.5 transition-all text-left"
                    >
                        <MessageSquare size={20} className="text-teal-600" />
                        <div>
                            <p className="text-sm font-semibold text-slate-700">Discuss with Agent</p>
                            <p className="text-xs text-slate-400">
                                {initiative.metadata?.journey_id ? 'Set outcomes and run journey workflow' : 'Get AI guidance on this initiative'}
                            </p>
                        </div>
                    </button>
                    <button
                        onClick={() => router.push('/dashboard/workflows/templates')}
                        className="flex items-center gap-3 p-4 bg-white rounded-[28px] border border-slate-100/80 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] hover:-translate-y-0.5 transition-all text-left"
                    >
                        <Settings size={20} className="text-indigo-600" />
                        <div>
                            <p className="text-sm font-semibold text-slate-700">Run Workflow</p>
                            <p className="text-xs text-slate-400">Execute a related workflow</p>
                        </div>
                    </button>
                    <button
                        onClick={() => router.push('/dashboard/initiatives')}
                        className="flex items-center gap-3 p-4 bg-white rounded-[28px] border border-slate-100/80 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] hover:-translate-y-0.5 transition-all text-left"
                    >
                        <BarChart3 size={20} className="text-amber-600" />
                        <div>
                            <p className="text-sm font-semibold text-slate-700">All Initiatives</p>
                            <p className="text-xs text-slate-400">View all your initiatives</p>
                        </div>
                    </button>
                </div>
            </motion.div>
        </PremiumShell>
    );
}
