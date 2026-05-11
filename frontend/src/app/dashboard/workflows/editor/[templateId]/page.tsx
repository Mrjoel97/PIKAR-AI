'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Workflow node editor page — Phase 110 Plan 04 (editable).
 *
 * Replaces Phase 109's read-only viewer with the full editable canvas:
 *   - Left rail: NodePalette (7 draggable kinds, Trigger/Actions/Logic/Output)
 *   - Center: NodeCanvas in edit mode (drag, connect, select, drop)
 *   - Right rail: NodePropertiesDrawer (per-kind Zod-validated form)
 *   - Top-right toolbar: validation badge count + Save button
 *   - Comment modal on Save (optional, defaults blank per Claude's Discretion #5)
 *
 * Save flow:
 *   1. Click Save → comment modal opens
 *   2. Confirm → saveTemplate() PUT with If-Match header
 *   3. 200 → toast 'Saved as v{N}'; update local etag from body.etag (B-2)
 *   4. 412 → toast 'Conflict' (Plan 05 replaces with three-button modal)
 *   5. 409 → toast 'Created your private copy' + router.push (W-4 seed fork)
 *   6. 400 → toast with validation error count (Plan 03 PUT-time enforcement)
 *
 * Routing notes (inherited from Phase 109):
 *   - Route param is [templateId], NOT [id] (Phase 109 deviation #1)
 *   - templateId === 'new' shows a Phase 3+ placeholder (creating new
 *     templates from scratch is deferred)
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ReactFlowProvider } from '@xyflow/react';
import { motion } from 'framer-motion';
import { Workflow } from 'lucide-react';
import { toast } from 'sonner';

import PremiumShell from '@/components/layout/PremiumShell';
import { GatedPage } from '@/components/dashboard/GatedPage';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { NodeCanvas } from '@/components/workflows/editor/NodeCanvas';
import { NodePalette } from '@/components/workflows/editor/NodePalette';
import { NodePropertiesDrawer } from '@/components/workflows/editor/NodePropertiesDrawer';
import { validateGraph } from '@/components/workflows/editor/useGraphValidation';
import {
    getWorkflowTemplateWithEtag,
    saveTemplate,
    ETagMismatchError,
    CopyForkError,
    ValidationFailedError,
    type WorkflowTemplateWithEtag,
    type GraphNode,
    type GraphEdge,
    type NodePosition,
} from '@/services/workflows';

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

    // ---------- Validation (client-side, every render) ----------
    const validationErrors = useMemo(
        () => validateGraph(nodes, edges),
        [nodes, edges],
    );
    const canSave = dirty && validationErrors.length === 0 && !saving;

    // ---------- Edit handlers ----------
    const handleCanvasChange = useCallback(
        (change: {
            nodes: GraphNode[];
            edges: GraphEdge[];
            layout: Record<string, NodePosition>;
        }) => {
            setNodes(change.nodes);
            setEdges(change.edges);
            setLayout(change.layout);
            setDirty(true);
        },
        [],
    );

    const handleUpdateNode = useCallback(
        (id: string, updates: Partial<GraphNode>) => {
            setNodes((prev) =>
                prev.map((n) => (n.id === id ? { ...n, ...updates } : n)),
            );
            setDirty(true);
        },
        [],
    );

    const handleCloseDrawer = useCallback(() => {
        setSelectedNodeId(null);
    }, []);

    const selectedNode = useMemo(
        () => nodes.find((n) => n.id === selectedNodeId) ?? null,
        [nodes, selectedNodeId],
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
            setDirty(false);
            setShowCommentModal(false);
            setComment('');
        } catch (err) {
            if (err instanceof ETagMismatchError) {
                // Plan 05 will replace this toast with the three-button conflict modal.
                // The fresh ETag is stashed on the error (body.etag) for that path.
                toast.error(
                    'Conflict — refresh and try again. (Conflict modal coming in next plan)',
                );
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
                // Defence-in-depth: client validator should have caught this.
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
    }, [templateId, nodes, edges, layout, comment, etag, router]);

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
                                            {dirty && (
                                                <span
                                                    className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700"
                                                    data-testid="editor-dirty-indicator"
                                                >
                                                    Unsaved
                                                </span>
                                            )}
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
                                            editable
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
                                />
                            </div>
                        )}

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
