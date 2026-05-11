'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview VersionSelector — Phase 110 Plan 05 Task 05-02.
 *
 * Toolbar dropdown listing recent versions. Top entry is the current
 * version (badge); clicking a non-current version fires `onSelectVersion`
 * (parent decides whether to preview, scope-reduced per I-2 to a disabled
 * editor pill — see page.tsx handlePreviewVersion). "View full history"
 * link at the bottom opens the HistoryPane via `onOpenHistory` prop.
 *
 * Controlled component: parent owns history + currentVersionId state.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ChevronDown, History as HistoryIcon } from 'lucide-react';
import type { HistoryItem } from '@/services/workflows';

const MAX_RECENT = 5;

export interface VersionSelectorProps {
    history: HistoryItem[];
    currentVersionId: string | null;
    onSelectVersion: (versionId: string) => void;
    onOpenHistory: () => void;
}

export function VersionSelector({
    history,
    currentVersionId,
    onSelectVersion,
    onOpenHistory,
}: VersionSelectorProps) {
    const [open, setOpen] = useState(false);
    const wrapperRef = useRef<HTMLDivElement>(null);

    // History is already sorted newest-first by the server (version_number DESC).
    const current = history.find((v) => v.version_id === currentVersionId);
    const triggerLabel = current ? `v${current.version_number}` : 'v1';

    // Click-outside to close
    const handleClickOutside = useCallback((event: MouseEvent) => {
        if (
            wrapperRef.current &&
            !wrapperRef.current.contains(event.target as Node)
        ) {
            setOpen(false);
        }
    }, []);

    useEffect(() => {
        if (!open) return;
        document.addEventListener('mousedown', handleClickOutside);
        return () =>
            document.removeEventListener('mousedown', handleClickOutside);
    }, [open, handleClickOutside]);

    return (
        <div
            ref={wrapperRef}
            className="relative"
            data-testid="version-selector"
        >
            <button
                type="button"
                onClick={() => setOpen(!open)}
                className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50"
                data-testid="version-selector-trigger"
                aria-haspopup="listbox"
                aria-expanded={open}
            >
                <span>{triggerLabel}</span>
                <span className="rounded bg-emerald-100 px-1 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-800">
                    current
                </span>
                <ChevronDown size={12} aria-hidden="true" />
            </button>
            {open && (
                <div
                    className="absolute right-0 z-20 mt-1 w-72 overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg"
                    role="listbox"
                    data-testid="version-selector-dropdown"
                >
                    {history.length === 0 && (
                        <div className="px-3 py-2 text-xs text-slate-500">
                            Just saved v1 — no other versions yet.
                        </div>
                    )}
                    {history.slice(0, MAX_RECENT).map((v) => {
                        const isCurrent = v.version_id === currentVersionId;
                        return (
                            <button
                                type="button"
                                key={v.version_id}
                                onClick={() => {
                                    onSelectVersion(v.version_id);
                                    setOpen(false);
                                }}
                                className="block w-full border-b border-slate-100 px-3 py-2 text-left text-xs hover:bg-slate-50"
                                data-testid={`version-item-${v.version_id}`}
                                role="option"
                                aria-selected={isCurrent}
                            >
                                <div className="flex items-center justify-between">
                                    <span className="font-medium text-slate-800">
                                        v{v.version_number}
                                    </span>
                                    {isCurrent && (
                                        <span className="rounded bg-emerald-100 px-1 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-800">
                                            current
                                        </span>
                                    )}
                                </div>
                                <div className="mt-0.5 text-[10px] text-slate-500">
                                    {v.saved_at}
                                    {' · '}
                                    {v.saved_by_user_name ?? 'unknown'}
                                </div>
                                {v.comment && (
                                    <div className="mt-0.5 truncate text-[11px] text-slate-600">
                                        {v.comment}
                                    </div>
                                )}
                            </button>
                        );
                    })}
                    <button
                        type="button"
                        onClick={() => {
                            onOpenHistory();
                            setOpen(false);
                        }}
                        className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-xs font-medium text-indigo-700 hover:bg-indigo-50"
                        data-testid="version-selector-open-history"
                    >
                        <HistoryIcon size={12} aria-hidden="true" />
                        <span>View full history</span>
                    </button>
                </div>
            )}
        </div>
    );
}
