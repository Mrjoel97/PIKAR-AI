'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Left-rail drag-source palette for the workflow node editor.
 *
 * Phase 110 Plan 04. Renders 7 draggable items categorized into
 * Trigger / Actions / Logic / Output (Claude's Discretion #1 from
 * 110-CONTEXT.md). Each item, on dragstart, writes a JSON payload
 * {kind, label} to ``dataTransfer.setData('application/reactflow', ...)``
 * which NodeCanvas's onDrop handler consumes (Task 04-04).
 *
 * Phase 3/4 kinds (condition / parallel / merge / human-approval) carry a
 * "Phase 3+" badge but stay draggable — saving them works (placeholder
 * config) but execution is deferred to Phase 3/4. Per Option C from the
 * decisions section.
 */

import React from 'react';
import {
    Play,
    Wand2,
    GitBranch,
    GitFork,
    GitMerge,
    UserCheck,
    CheckCircle2,
    type LucideIcon,
} from 'lucide-react';

import type { NodeKind } from '@/services/workflows';

interface PaletteItem {
    kind: NodeKind;
    label: string;
    icon: LucideIcon;
    comingSoon: boolean;
}

interface PaletteGroup {
    category: string;
    items: PaletteItem[];
}

const PALETTE: PaletteGroup[] = [
    {
        category: 'Trigger',
        items: [
            {
                kind: 'trigger',
                label: 'Trigger',
                icon: Play,
                comingSoon: false,
            },
        ],
    },
    {
        category: 'Actions',
        items: [
            {
                kind: 'agent-action',
                label: 'Agent action',
                icon: Wand2,
                comingSoon: false,
            },
        ],
    },
    {
        category: 'Logic',
        items: [
            {
                kind: 'condition',
                label: 'Condition',
                icon: GitBranch,
                comingSoon: true,
            },
            {
                kind: 'parallel',
                label: 'Parallel',
                icon: GitFork,
                comingSoon: true,
            },
            {
                kind: 'merge',
                label: 'Merge',
                icon: GitMerge,
                comingSoon: true,
            },
            {
                kind: 'human-approval',
                label: 'Human approval',
                icon: UserCheck,
                comingSoon: true,
            },
        ],
    },
    {
        category: 'Output',
        items: [
            {
                kind: 'output',
                label: 'Output',
                icon: CheckCircle2,
                comingSoon: false,
            },
        ],
    },
];

export function NodePalette() {
    const onDragStart = (
        event: React.DragEvent<HTMLLIElement>,
        kind: NodeKind,
        label: string,
    ) => {
        // Plan 04 contract: NodeCanvas reads this payload in its onDrop handler.
        event.dataTransfer.setData(
            'application/reactflow',
            JSON.stringify({ kind, label }),
        );
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <aside
            className="w-56 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-3 space-y-4"
            data-testid="node-palette"
            aria-label="Node palette"
        >
            <p className="text-xs font-medium text-slate-500">
                Drag a node onto the canvas
            </p>
            {PALETTE.map((group) => (
                <section key={group.category}>
                    <h3 className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                        {group.category}
                    </h3>
                    <ul className="space-y-1">
                        {group.items.map((item) => (
                            <li
                                key={item.kind}
                                draggable
                                onDragStart={(e) =>
                                    onDragStart(e, item.kind, item.label)
                                }
                                className="group flex cursor-grab items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-sm text-slate-700 transition-colors hover:border-indigo-300 hover:bg-indigo-50 active:cursor-grabbing"
                                data-testid={`palette-item-${item.kind}`}
                            >
                                <item.icon
                                    className="h-3.5 w-3.5 shrink-0 text-slate-500"
                                    aria-hidden="true"
                                />
                                <span className="flex-1 truncate">
                                    {item.label}
                                </span>
                                {item.comingSoon && (
                                    <span className="rounded-md bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                                        Phase 3+
                                    </span>
                                )}
                            </li>
                        ))}
                    </ul>
                </section>
            ))}
        </aside>
    );
}

export default NodePalette;
