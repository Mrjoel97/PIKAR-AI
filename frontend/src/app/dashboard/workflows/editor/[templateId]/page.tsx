'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Workflow node editor page — Phase 110 Plan 05.
 *
 * Builds on Plan 04's editable canvas by wiring in the three versioning
 * surfaces:
 *
 *   - **VersionSelector** (toolbar dropdown, top-right) — lists recent
 *     versions; clicking a non-current entry enters a "v3 preview" pill
 *     mode that DISABLES editing without rendering v3's graph content
 *     (I-2 scope reduction — full per-version preview would require a
 *     new GET /templates/{id}/versions/{vid} endpoint that Plan 02 did
 *     not ship).
 *   - **HistoryPane** (right slide-in, toggled via toolbar) — lists all
 *     versions with revert buttons. Confirmed revert calls revertTemplate
 *     which creates a NEW version (parent_version_id = target.id).
 *   - **ConflictModal** (overlay, on 412 save response) — three-button
 *     resolution per Spec B decision 6 (View their changes / Overwrite
 *     / Cancel). Overwrite re-fires PUT with body.etag from the 412
 *     response (B-2 wire format — NOT a header value, NOT a re-fetched
 *     GET).
 *
 * Save flow stays the same as Plan 04 except the 412 path no longer
 * toasts; it sets conflictState which renders the ConflictModal.
 *
 * Routing notes (inherited from Phase 109):
 *   - Route param is [templateId], NOT [id] (Phase 109 deviation #1)
 *   - templateId === 'new' shows a Phase 3+ placeholder
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ReactFlowProvider } from '@xyflow/react';
import { motion } from 'framer-motion';
import { Workflow, History as HistoryIcon } from 'lucide-react';
import { toast } from 'sonner';

import PremiumShell from '@/components/layout/PremiumShell';
import { GatedPage } from '@/components/dashboard/GatedPage';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { NodeCanvas } from '@/components/workflows/editor/NodeCanvas';
import { NodePalette } from '@/components/workflows/editor/NodePalette';
import { NodePropertiesDrawer } from '@/components/workflows/editor/NodePropertiesDrawer';
import { VersionSelector } from '@/components/workflows/editor/VersionSelector';
import { HistoryPane } from '@/components/workflows/editor/HistoryPane';
import { ConflictModal } from '@/components/workflows/editor/ConflictModal';
import { validateGraph } from '@/components/workflows/editor/useGraphValidation';
import {
    getWorkflowTemplateWithEtag,
    saveTemplate,
    getTemplateHistory,
    revertTemplate,
    ETagMismatchError,
    CopyForkError,
    ValidationFailedError,
    type WorkflowTemplate,
    type WorkflowTemplateWithEtag,
    type GraphNode,
    type GraphEdge,
    type NodePosition,
    type HistoryItem,
} from '@/services/workflows';

interface ConflictState {
    freshTemplate: WorkflowTemplate;
    freshEtag: string;
}

function EditorSkeleton() {
    return (
        <div className="animate-pulse space-y-6">
            <div className="h-8 w-64 rounded-xl bg-slate-100" />
            <div className="h-[70vh] rounded-2xl bg-slate-100" />
        </div>
    );
}

export default function WorkflowEditorPage() {
    const params = useParams<{ templateId: string | string[] }>();
    const router = useRouter();
    const rawParam = params?.templateId;
    const templateId = Array.isArray(rawParam) ? rawParam[0] : rawParam;

    const [template, setTemplate] = useState<WorkflowTemplateWithEtag | null>(
        null,
    );
    const [etag, setEtag] = useState<string>('');
    const [nodes, setNodes] = useState<GraphNode[]>([]);
    const [edges, setEdges] = useState<GraphEdge[]>([]);
    const [layout, setLayout] = useState<Record<string, NodePosition>>({});
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [dirty, setDirty] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [showCommentModal, setShowCommentModal] = useState(false);
    const [comment, setComment] = useState('');

    // Plan 05: versioning + conflict resolution state.
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [historyOpen, setHistoryOpen] = useState(false);
    const [previewVersionId, setPreviewVersionId] = useState<string | null>(
        null,
    );
    const [conflictState, setConflictState] = useState<ConflictState | null>(
        null,
    );

    // ---------- Load template + ETag on mount ----------
    useEffect(() => {
        if (!templateId) {
            setError('Missing template id in URL.');
            setLoading(false);
            return;
        }
        if (templateId === 'new') {
            setError(
                'Creating new templates from this view is coming in a future phase. For now, pick a template from /dashboard/workflows/templates and edit it.',
            );
            setLoading(false);
            return;
        }

        let cancelled = false;
        setLoading(true);
        setError(null);

        (async () => {
            try {
                const t = await getWorkflowTemplateWithEtag(templateId);
                if (cancelled) return;
                setTemplate(t);
                setEtag(t._etag ?? '');
                setNodes((t.graph_nodes ?? []) as GraphNode[]);
                setEdges((t.graph_edges ?? []) as GraphEdge[]);
                setLayout(
                    (t.graph_layout ?? {}) as Record<string, NodePosition>,
                );
                setDirty(false);
            } catch (e: unknown) {
                if (cancelled) return;
                const message =
                    e instanceof Error
                        ? e.message
                        : 'Failed to load workflow template';
                setError(message);
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [templateId]);

    // ---------- Load history on mount + after every save ----------
    const refreshHistory = useCallback(async () => {
        if (!templateId || templateId === 'new') return;
        try {
            const items = await getTemplateHistory(templateId);
            setHistory(items);
        } catch (err) {
            // Non-fatal — log to console; the editor still works without history.
            // eslint-disable-next-line no-console
            console.warn('Failed to load template history:', err);
        }
    }, [templateId]);

    useEffect(() => {
        if (!loading && !error && template) {
            refreshHistory();
        }
    }, [loading, error, template, refreshHistory]);

    // ---------- Validation (client-side, every render) ----------
    const validationErrors = useMemo(
        () => validateGraph(nodes, edges),
        [nodes, edges],
    );
    const previewing = previewVersionId !== null;
    const canSave =
        dirty && validationErrors.length === 0 && !saving && !previewing;

    // ---------- Edit handlers ----------
    const handleCanvasChange = useCallback(
        (change: {
            nodes: GraphNode[];
            edges: GraphEdge[];
            layout: Record<string, NodePosition>;
        }) => {
            if (previewing) return; // ignore changes while previewing
            setNodes(change.nodes);
            setEdges(change.edges);
            setLayout(change.layout);
            setDirty(true);
        },
        [previewing],
    );

    const handleUpdateNode = useCallback(
        (id: string, updates: Partial<GraphNode>) => {
            if (previewing) return;
            setNodes((prev) =>
                prev.map((n) => (n.id === id ? { ...n, ...updates } : n)),
            );
            setDirty(true);
        },
        [previewing],
    );

    const handleCloseDrawer = useCallback(() => {
        setSelectedNodeId(null);
    }, []);

    const selectedNode = useMemo(
        () => nodes.find((n) => n.id === selectedNodeId) ?? null,
        [nodes, selectedNodeId],
    );

    // ---------- VersionSelector + preview pill (I-2 scope reduction) ----------
    const handlePreviewVersion = useCallback(
        (versionId: string) => {
            // If the user picked the current version, exit preview mode.
            if (versionId === template?.current_version_id) {
                setPreviewVersionId(null);
                return;
            }
            // I-2: do NOT fetch v3's graph content. We only flag the editor
            // as in-preview so Save is disabled and the canvas is non-editable
            // without rendering v3's content. Full per-version graph preview
            // would require a new GET /templates/{id}/versions/{vid} endpoint
            // that Plan 02 did not ship — deferred to a follow-up.
            setPreviewVersionId(versionId);
        },
        [template?.current_version_id],
    );

    const previewVersion = useMemo(
        () =>
            previewVersionId
                ? history.find((v) => v.version_id === previewVersionId)
                : null,
        [previewVersionId, history],
    );

    // ---------- Revert flow ----------
    const handleRevert = useCallback(
        async (versionId: string) => {
            if (!templateId) return;
            const target = history.find((v) => v.version_id === versionId);
            try {
                const result = await revertTemplate(
                    templateId,
                    versionId,
                    etag,
                );
                // The new version replaces our local state.
                const v = result.version;
                setNodes((v.graph_nodes ?? []) as GraphNode[]);
                setEdges((v.graph_edges ?? []) as GraphEdge[]);
                setLayout(
                    (v.graph_layout ?? {}) as Record<string, NodePosition>,
                );
                // B-2: next ETag comes from body.etag (already what revertTemplate returns).
                setEtag(result.etag ?? '');
                setDirty(false);
                // Update template's current_version_id pointer in local state.
                setTemplate((prev) =>
                    prev
                        ? ({ ...prev, current_version_id: v.id } as
                              | WorkflowTemplateWithEtag
                              | null)
                        : prev,
                );
                setPreviewVersionId(null);
                await refreshHistory();
                const targetLabel = target
                    ? `v${target.version_number}`
                    : 'older version';
                toast.success(
                    `Reverted to ${targetLabel} — new v${
                        v.version_number ?? '?'
                    } created`,
                );
            } catch (err) {
                if (err instanceof ETagMismatchError) {
                    // Race: someone else saved between our load and our revert.
                    // Surface the conflict modal so the user can choose.
                    setConflictState({
                        freshTemplate: err.currentTemplate,
                        freshEtag: err.freshEtag,
                    });
                } else {
                    const msg =
                        err instanceof Error ? err.message : 'Unknown error';
                    toast.error(`Revert failed: ${msg}`);
                }
            }
        },
        [templateId, history, etag, refreshHistory],
    );

    // ---------- Save flow ----------
    const openSaveModal = useCallback(() => {
        if (!canSave) return;
        setComment('');
        setShowCommentModal(true);
    }, [canSave]);

    const confirmSave = useCallback(async () => {
        if (!templateId) return;
        setSaving(true);
        try {
            const result = await saveTemplate(
                templateId,
                {
                    graph_nodes: nodes,
                    graph_edges: edges,
                    graph_layout: layout,
                    comment: comment.trim() || undefined,
                },
                etag,
            );
            toast.success(
                `Saved as version ${result.version.version_number ?? '?'}`,
            );
            // B-2: PUT 200 BODY carries the next-write ETag canonically.
            setEtag(result.etag ?? '');
            // Update local current_version_id pointer.
            setTemplate((prev) =>
                prev
                    ? ({
                          ...prev,
                          current_version_id: result.version.id,
                      } as WorkflowTemplateWithEtag | null)
                    : prev,
            );
            setDirty(false);
            setShowCommentModal(false);
            setComment('');
            await refreshHistory();
        } catch (err) {
            if (err instanceof ETagMismatchError) {
                // Plan 05: surface the three-button conflict modal instead of
                // the Plan 04 toast placeholder. freshEtag is body.etag (B-2).
                setShowCommentModal(false);
                setConflictState({
                    freshTemplate: err.currentTemplate,
                    freshEtag: err.freshEtag,
                });
            } else if (err instanceof CopyForkError) {
                // W-4: seed-fork-on-Edit. Toast + redirect to the new private copy.
                toast.success(
                    `Created your private copy of "${err.seedName}"`,
                );
                setShowCommentModal(false);
                router.push(
                    `/dashboard/workflows/editor/${err.copiedTemplateId}`,
                );
            } else if (err instanceof ValidationFailedError) {
                toast.error(
                    `Save blocked: ${err.errors.length} validation error(s). Fix the red badges and retry.`,
                );
            } else {
                const msg = err instanceof Error ? err.message : 'Unknown error';
                toast.error(`Save failed: ${msg}`);
            }
        } finally {
            setSaving(false);
        }
    }, [templateId, nodes, edges, layout, comment, etag, router, refreshHistory]);

    // ---------- ConflictModal handlers ----------
    const handleViewTheirChanges = useCallback(() => {
        if (!conflictState) return;
        const fresh = conflictState.freshTemplate;
        // Replace local canvas state with the server's current graph.
        setTemplate((prev) =>
            prev
                ? ({ ...prev, ...fresh } as WorkflowTemplateWithEtag | null)
                : (fresh as unknown as WorkflowTemplateWithEtag),
        );
        // B-2: freshEtag came from body.etag of the 412 response.
        setEtag(conflictState.freshEtag);
        setNodes((fresh.graph_nodes ?? []) as GraphNode[]);
        setEdges((fresh.graph_edges ?? []) as GraphEdge[]);
        setLayout(
            (fresh.graph_layout ?? {}) as Record<string, NodePosition>,
        );
        setDirty(false);
        setConflictState(null);
        toast.warning(
            'Loaded latest version — your unsaved edits were discarded',
        );
        // Refresh history so the user sees the new version row.
        refreshHistory();
    }, [conflictState, refreshHistory]);

    const handleOverwrite = useCallback(async () => {
        if (!conflictState || !templateId) return;
        setSaving(true);
        try {
            // B-2: Overwrite re-sends PUT with the fresh ETag stashed from
            // the 412 response BODY (NOT header). conflictState.freshEtag
            // was originally err.freshEtag which saveTemplate read from
            // body.etag — pass it through verbatim.
            const result = await saveTemplate(
                templateId,
                {
                    graph_nodes: nodes,
                    graph_edges: edges,
                    graph_layout: layout,
                    comment: comment.trim() || undefined,
                },
                conflictState.freshEtag,
            );
            // B-2: next ETag from result.etag (body).
            setEtag(result.etag ?? '');
            setTemplate((prev) =>
                prev
                    ? ({
                          ...prev,
                          current_version_id: result.version.id,
                      } as WorkflowTemplateWithEtag | null)
                    : prev,
            );
            setDirty(false);
            setConflictState(null);
            toast.success(
                `Overwritten — saved as v${result.version.version_number ?? '?'}`,
            );
            await refreshHistory();
        } catch (err) {
            if (err instanceof ETagMismatchError) {
                // Race continued — update the conflict state with the newer body+etag.
                setConflictState({
                    freshTemplate: err.currentTemplate,
                    freshEtag: err.freshEtag,
                });
            } else if (err instanceof ValidationFailedError) {
                toast.error(
                    `Overwrite blocked: ${err.errors.length} validation error(s).`,
                );
                setConflictState(null);
            } else {
                const msg = err instanceof Error ? err.message : 'Unknown error';
                toast.error(`Overwrite failed: ${msg}`);
                setConflictState(null);
            }
        } finally {
            setSaving(false);
        }
    }, [
        conflictState,
        templateId,
        nodes,
        edges,
        layout,
        comment,
        refreshHistory,
    ]);

    const handleCancelConflict = useCallback(() => {
        setConflictState(null);
    }, []);

    // ---------- Render ----------
    return (
        <GatedPage featureKey="workflows">
            <DashboardErrorBoundary fallbackTitle="Workflow Editor Error">
                <PremiumShell>
                    <motion.div
                        className="mx-auto max-w-7xl p-6"
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4 }}
                    >
                        <div className="mb-4">
                            <Breadcrumb
                                items={[
                                    { label: 'Home', href: '/dashboard' },
                                    {
                                        label: 'Workflows',
                                        href: '/dashboard/workflows/templates',
                                    },
                                    {
                                        label: 'Templates',
                                        href: '/dashboard/workflows/templates',
                                    },
                                    {
                                        label: template?.name ?? 'Editor',
                                    },
                                ]}
                            />
                        </div>

                        <div className="mb-6 flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-400 to-blue-500 shadow-lg shadow-indigo-200">
                                <Workflow
                                    className="h-6 w-6 text-white"
                                    aria-hidden="true"
                                />
                            </div>
                            <div className="flex-1">
                                <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                                    {template?.name ?? 'Workflow Editor'}
                                </h1>
                                <p className="mt-0.5 text-sm text-slate-500">
                                    {template?.description ??
                                        'Edit the workflow graph. Drag nodes from the palette, connect handles, and click Save to create a new version.'}
                                </p>
                            </div>
                        </div>

                        {loading && <EditorSkeleton />}

                        {!loading && error && (
                            <div
                                className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
                                role="alert"
                            >
                                {error}
                            </div>
                        )}

                        {!loading && !error && template && (
                            <div
                                className="flex h-[70vh] overflow-hidden rounded-2xl border border-slate-200 bg-white"
                                data-testid="editor-shell"
                            >
                                <NodePalette />
                                <ReactFlowProvider>
                                    <main
                                        className="relative flex-1"
                                        data-testid="editor-canvas-container"
                                    >
                                        <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
                                            {previewing && previewVersion && (
                                                <span
                                                    className="rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700"
                                                    data-testid="editor-preview-pill"
                                                >
                                                    v{previewVersion.version_number}{' '}
                                                    preview
                                                </span>
                                            )}
                                            {previewing && (
                                                <button
                                                    type="button"
                                                    onClick={() =>
                                                        setPreviewVersionId(
                                                            null,
                                                        )
                                                    }
                                                    className="rounded-md border border-indigo-200 bg-white px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
                                                    data-testid="editor-back-to-edits"
                                                >
                                                    Back to my edits
                                                </button>
                                            )}
                                            {validationErrors.length > 0 && (
                                                <span
                                                    className="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700"
                                                    data-testid="editor-validation-summary"
                                                >
                                                    {validationErrors.length}{' '}
                                                    validation error
                                                    {validationErrors.length ===
                                                    1
                                                        ? ''
                                                        : 's'}
                                                </span>
                                            )}
                                            {dirty && !previewing && (
                                                <span
                                                    className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700"
                                                    data-testid="editor-dirty-indicator"
                                                >
                                                    Unsaved
                                                </span>
                                            )}
                                            <VersionSelector
                                                history={history}
                                                currentVersionId={
                                                    template.current_version_id ??
                                                    null
                                                }
                                                onSelectVersion={
                                                    handlePreviewVersion
                                                }
                                                onOpenHistory={() =>
                                                    setHistoryOpen(true)
                                                }
                                            />
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    setHistoryOpen(true)
                                                }
                                                className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                                                data-testid="editor-open-history"
                                                aria-label="Open version history"
                                            >
                                                <HistoryIcon
                                                    size={12}
                                                    aria-hidden="true"
                                                />
                                                <span>History</span>
                                            </button>
                                            <button
                                                type="button"
                                                onClick={openSaveModal}
                                                disabled={!canSave}
                                                className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-opacity hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                                                data-testid="editor-save-button"
                                            >
                                                {saving ? 'Saving…' : 'Save'}
                                            </button>
                                        </div>
                                        <NodeCanvas
                                            template={template}
                                            editable={!previewing}
                                            onChange={handleCanvasChange}
                                            selectedNodeId={selectedNodeId}
                                            onSelectNode={setSelectedNodeId}
                                            validationErrors={validationErrors}
                                        />
                                    </main>
                                </ReactFlowProvider>
                                <NodePropertiesDrawer
                                    node={selectedNode}
                                    onUpdate={handleUpdateNode}
                                    onClose={handleCloseDrawer}
                                    nodes={nodes}
                                    edges={edges}
                                />
                            </div>
                        )}

                        {historyOpen && (
                            <HistoryPane
                                history={history}
                                currentVersionId={
                                    template?.current_version_id ?? null
                                }
                                onRevert={handleRevert}
                                onClose={() => setHistoryOpen(false)}
                            />
                        )}

                        <ConflictModal
                            open={conflictState !== null}
                            freshTemplate={
                                conflictState?.freshTemplate ?? null
                            }
                            onViewTheirChanges={handleViewTheirChanges}
                            onOverwrite={handleOverwrite}
                            onCancel={handleCancelConflict}
                        />

                        {showCommentModal && (
                            <div
                                className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
                                data-testid="comment-modal"
                                role="dialog"
                                aria-modal="true"
                                aria-labelledby="comment-modal-title"
                            >
                                <div className="w-96 space-y-3 rounded-2xl bg-white p-6 shadow-xl">
                                    <h2
                                        id="comment-modal-title"
                                        className="text-base font-semibold text-slate-900"
                                    >
                                        Save changes
                                    </h2>
                                    <p className="text-sm text-slate-500">
                                        Optional: describe what changed in this
                                        version. You can leave it blank.
                                    </p>
                                    <textarea
                                        value={comment}
                                        onChange={(e) =>
                                            setComment(e.target.value)
                                        }
                                        placeholder="e.g. Added approval step before publish"
                                        rows={3}
                                        className="w-full rounded-md border border-slate-200 p-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                                        data-testid="comment-modal-textarea"
                                    />
                                    <div className="flex justify-end gap-2">
                                        <button
                                            type="button"
                                            onClick={() =>
                                                setShowCommentModal(false)
                                            }
                                            disabled={saving}
                                            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                                            data-testid="comment-modal-cancel"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="button"
                                            onClick={confirmSave}
                                            disabled={saving}
                                            className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                                            data-testid="comment-modal-confirm"
                                        >
                                            {saving ? 'Saving…' : 'Save'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </motion.div>
                </PremiumShell>
            </DashboardErrorBoundary>
        </GatedPage>
    );
}
