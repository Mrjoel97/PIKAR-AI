'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview ConflictModal — Phase 110 Plan 05 Task 05-03.
 *
 * Three-button modal surfaced when PUT /workflows/templates/{id} returns
 * 412 Precondition Failed (saveTemplate throws ETagMismatchError). Mirrors
 * the three actions defined by Spec B decision 6:
 *
 *   1. **View their changes** — discards local edits and loads the fresh
 *      template body from the 412 response into the editor canvas.
 *   2. **Overwrite** — shows a secondary confirm; on yes, re-fires PUT
 *      with the fresh ETag from `body.etag` (B-2 wire format — NOT the
 *      response header, NOT a re-fetched GET).
 *   3. **Cancel** — closes the modal, local editor state stays intact so
 *      the user can copy work elsewhere before reloading.
 *
 * Controlled component: the page owns `open` + `freshTemplate` state.
 * Escape key fires onCancel for keyboard accessibility.
 */

import React, { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import type { WorkflowTemplate } from '@/services/workflows';

export interface ConflictModalProps {
    open: boolean;
    freshTemplate: WorkflowTemplate | null;
    onViewTheirChanges: () => void;
    onOverwrite: () => void;
    onCancel: () => void;
}

export function ConflictModal({
    open,
    freshTemplate,
    onViewTheirChanges,
    onOverwrite,
    onCancel,
}: ConflictModalProps) {
    const [showOverwriteConfirm, setShowOverwriteConfirm] = useState(false);

    // Escape-key handler — fires onCancel for keyboard a11y.
    useEffect(() => {
        if (!open) return;
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onCancel();
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [open, onCancel]);

    // Reset the secondary-confirm state when the modal closes.
    useEffect(() => {
        if (!open) setShowOverwriteConfirm(false);
    }, [open]);

    if (!open) return null;

    // The conflicting saver's identity is best-effort: prefer
    // last_saved_by/last_saved_by_name if the fresh body carries it, fall
    // back to "another user". The Plan 02 body shape doesn't currently
    // surface a friendly name for the conflicting saver, so the fallback
    // is the common case.
    const conflictingSaver =
        (freshTemplate as unknown as { last_saved_by_name?: string } | null)
            ?.last_saved_by_name ?? 'another user';

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            role="dialog"
            aria-modal="true"
            aria-labelledby="conflict-modal-title"
            data-testid="conflict-modal"
        >
            <div className="w-[480px] space-y-3 rounded-2xl bg-white p-6 shadow-xl">
                <header className="flex items-start gap-2">
                    <AlertTriangle
                        className="mt-0.5 flex-shrink-0 text-amber-500"
                        size={20}
                        aria-hidden="true"
                    />
                    <div className="flex-1">
                        <h2
                            id="conflict-modal-title"
                            className="text-base font-semibold text-slate-900"
                        >
                            Save conflict
                        </h2>
                        <p className="mt-0.5 text-sm text-slate-500">
                            {conflictingSaver} saved this template after you
                            opened it. How do you want to resolve it?
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={onCancel}
                        className="rounded-md p-1 text-slate-500 hover:bg-slate-100"
                        aria-label="Close conflict modal"
                    >
                        <X size={16} aria-hidden="true" />
                    </button>
                </header>

                {!showOverwriteConfirm && (
                    <div className="flex flex-wrap justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={onCancel}
                            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                            data-testid="conflict-cancel"
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            onClick={() => setShowOverwriteConfirm(true)}
                            className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
                            data-testid="conflict-overwrite"
                        >
                            Overwrite
                        </button>
                        <button
                            type="button"
                            onClick={onViewTheirChanges}
                            className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
                            data-testid="conflict-view"
                        >
                            View their changes
                        </button>
                    </div>
                )}

                {showOverwriteConfirm && (
                    <div className="space-y-2 border-t border-slate-200 pt-3">
                        <p className="text-sm font-medium text-red-700">
                            This will permanently replace {conflictingSaver}'s
                            saved changes with your local edits. Continue?
                        </p>
                        <p className="text-xs text-slate-500">
                            (Their version will remain in the version history
                            — nothing is deleted — but the live template
                            will reflect your changes.)
                        </p>
                        <div className="flex justify-end gap-2">
                            <button
                                type="button"
                                onClick={() =>
                                    setShowOverwriteConfirm(false)
                                }
                                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                                data-testid="conflict-overwrite-back"
                            >
                                Back
                            </button>
                            <button
                                type="button"
                                onClick={onOverwrite}
                                className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                                data-testid="conflict-overwrite-confirm"
                            >
                                Yes, overwrite
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
