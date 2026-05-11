'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Workflow node editor page — Phase 1 of Spec B (read-only viewer).
 *
 * Fetches a WorkflowTemplate via getWorkflowTemplate(id) and hands it to
 * NodeCanvas, which renders a React Flow graph (pan/zoom only, no editing).
 *
 * Routing notes (deviation from plan):
 *
 * - The plan's must_haves listed `frontend/src/app/dashboard/workflows/editor/[id]/page.tsx`
 *   but a legacy phase-editor at `[templateId]/page.tsx` was already on disk.
 *   Two dynamic [...] segments at the same path-level would conflict in
 *   Next.js, so we replaced the contents of `[templateId]/page.tsx` instead
 *   of creating a parallel `[id]` route. The functional contract (a single
 *   dynamic segment under /dashboard/workflows/editor/) is preserved — the
 *   param name change is internal-only and templates/page.tsx's
 *   `router.push(`/dashboard/workflows/editor/${template.id}`)` is unaffected.
 * - The legacy phase-editor was an editable form, which conflicts with Spec
 *   B Phase 1's read-only mandate. Phase 2-4 will re-introduce editing.
 *
 * The `new` slug is intentionally not supported in Phase 1 — visiting
 * /dashboard/workflows/editor/new shows a friendly "Phase 2" placeholder.
 */

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Workflow } from 'lucide-react';

import PremiumShell from '@/components/layout/PremiumShell';
import { GatedPage } from '@/components/dashboard/GatedPage';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { NodeCanvas } from '@/components/workflows/editor/NodeCanvas';
import { getWorkflowTemplate, type WorkflowTemplate } from '@/services/workflows';

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
    const rawParam = params?.templateId;
    const templateId = Array.isArray(rawParam) ? rawParam[0] : rawParam;

    const [template, setTemplate] = useState<WorkflowTemplate | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!templateId) {
            setError('Missing template id in URL.');
            setLoading(false);
            return;
        }
        if (templateId === 'new') {
            // Phase 1 does not implement /editor/new — show a friendly
            // placeholder so the "Create Draft" button on /templates does
            // not 404 or crash.
            setError(
                'Creating new templates from this view will be available in Phase 2 of the workflow node editor.',
            );
            setLoading(false);
            return;
        }

        let cancelled = false;
        setLoading(true);
        setError(null);

        (async () => {
            try {
                const result = await getWorkflowTemplate(templateId);
                if (cancelled) return;
                // getWorkflowTemplate currently returns `any` (legacy
                // signature). Cast to the typed WorkflowTemplate alias.
                setTemplate(result as WorkflowTemplate);
            } catch (e: unknown) {
                if (cancelled) return;
                const message =
                    e instanceof Error ? e.message : 'Failed to load workflow template';
                setError(message);
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [templateId]);

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
                                    { label: 'Workflows', href: '/dashboard/workflows/templates' },
                                    { label: 'Templates', href: '/dashboard/workflows/templates' },
                                    { label: template?.name ?? 'Editor' },
                                ]}
                            />
                        </div>

                        <div className="mb-6 flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-400 to-blue-500 shadow-lg shadow-indigo-200">
                                <Workflow className="h-6 w-6 text-white" aria-hidden="true" />
                            </div>
                            <div>
                                <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                                    {template?.name ?? 'Workflow Editor'}
                                </h1>
                                <p className="mt-0.5 text-sm text-slate-500">
                                    {template?.description ??
                                        'Read-only view of the workflow graph (Phase 1 of Spec B).'}
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
                            <NodeCanvas template={template} />
                        )}
                    </motion.div>
                </PremiumShell>
            </DashboardErrorBoundary>
        </GatedPage>
    );
}
