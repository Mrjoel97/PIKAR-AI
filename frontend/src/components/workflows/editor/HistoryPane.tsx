'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview HistoryPane — Phase 110 Plan 05 Task 05-02.
 *
 * Slide-in right-side pane listing the full version history for a
 * workflow template. Each row shows version_number, saved_at,
 * saved_by_user_name, and the optional comment. Non-current versions
 * have a "Revert to this version" button which opens a confirmation
 * dialog; confirming fires `onRevert(versionId)` so the parent can call
 * the revertTemplate service method.
 *
 * Controlled component: parent owns the open/close state and the
 * history list (refreshed after every save via getTemplateHistory).
 */

import React, { useState } from 'react';
import { X, RotateCcw, History as HistoryIcon } from 'lucide-react';
import type { HistoryItem } from '@/services/workflows';

export interface HistoryPaneProps {
    history: HistoryItem[];
    currentVersionId: string | null;
    onRevert: (versionId: string) => void;
    onClose: () => void;
}

export function HistoryPane({
    history,
    currentVersionId,
    onRevert,
    onClose,
}: HistoryPaneProps) {
    const [confirmRevertId, setConfirmRevertId] = useState<string | null>(
        null,
    );

    const confirmTarget = confirmRevertId
        ? history.find((v) => v.version_id === confirmRevertId)
        : null;

    return (
        <aside
            className="fixed right-0 top-0 z-30 flex h-full w-96 flex-col overflow-y-auto border-l border-slate-200 bg-white shadow-xl"
            data-testid="history-pane"
            role="complementary"
            aria-label="Version history"
        >
            <header className="flex items-center justify-between border-b border-slate-200 p-4">
                <div className="flex items-center gap-2">
                    <HistoryIcon
                        size={16}
                        className="text-slate-500"
                        aria-hidden="true"
                    />
                    <h2 className="text-base font-semibold text-slate-900">
                        Version history
                    </h2>
                </div>
                <button
                    type="button"
                    onClick={onClose}
                    className="rounded-md p-1 text-slate-500 hover:bg-slate-100"
                    data-testid="history-pane-close"
                    aria-label="Close history pane"
                >
                    <X size={16} aria-hidden="true" />
                </button>
            </header>
            <ol className="flex-1 divide-y divide-slate-100">
                {history.length === 0 && (
                    <li className="p-4 text-sm text-slate-500">
                        No version history yet.
                    </li>
                )}
                {history.map((v) => {
                    const isCurrent = v.version_id === currentVersionId;
                    return (
                        <li
                            key={v.version_id}
                            className="space-y-1 p-4"
                            data-testid={`history-item-${v.version_id}`}
                        >
                            <div className="flex items-baseline justify-between">
                                <strong className="text-sm text-slate-900">
                                    v{v.version_number}
                                </strong>
                                {isCurrent && (
                                    <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-800">
                                        current
                                    </span>
                                )}
                            </div>
                            <div className="text-xs text-slate-500">
                                {v.saved_at}
                                {' · '}
                                {v.saved_by_user_name ?? 'unknown'}
                            </div>
                            {v.comment && (
                                <div className="text-sm text-slate-700">
                                    {v.comment}
                                </div>
                            )}
                            {!isCurrent && (
                                <button
                                    type="button"
                                    onClick={() =>
                                        setConfirmRevertId(v.version_id)
                                    }
                                    className="mt-1 flex items-center gap-1 text-xs font-medium text-indigo-700 hover:underline"
                                    data-testid={`revert-button-${v.version_id}`}
                                >
                                    <RotateCcw
                                        size={11}
                                        aria-hidden="true"
                                    />
                                    <span>Revert to this version</span>
                                </button>
                            )}
                        </li>
                    );
                })}
            </ol>
            {confirmRevertId && confirmTarget && (
                <div
                    className="fixed inset-0 z-40 flex items-center justify-center bg-black/40"
                    role="dialog"
                    aria-modal="true"
                    data-testid="history-revert-confirm"
                >
                    <div className="w-96 space-y-3 rounded-2xl bg-white p-6 shadow-xl">
                        <h3 className="text-base font-semibold text-slate-900">
                            Revert to v{confirmTarget.version_number}?
                        </h3>
                        <p className="text-sm text-slate-600">
                            A new version will be created with v
                            {confirmTarget.version_number}'s content; your
                            current version stays in history. This action
                            never deletes any version row.
                        </p>
                        <div className="flex justify-end gap-2">
                            <button
                                type="button"
                                onClick={() => setConfirmRevertId(null)}
                                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                                data-testid="history-revert-confirm-cancel"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    onRevert(confirmRevertId);
                                    setConfirmRevertId(null);
                                }}
                                className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
                                data-testid="history-revert-confirm-yes"
                            >
                                Revert
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </aside>
    );
}
