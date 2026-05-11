'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow custom node for the "merge" node kind.
 *
 * Phase 110 of Spec B (editable canvas) ships this node VISUALLY only.
 * The asyncio.wait-based merge executor is Phase 4 — saving works (
 * placeholder Zod schema) but execution ignores it.
 *
 * Shape: blue rounded-rect with a "merge" icon. TWO target handles (left,
 * Phase 110 visual = 2 default) and ONE source handle (right). Phase 4
 * will support N target handles dynamically.
 */

import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { GitMerge } from 'lucide-react';

import type { ValidationError } from '@/services/workflows';

export interface MergeNodeData {
    label: string;
    validationErrors?: ValidationError[];
    [key: string]: unknown;
}

export function MergeNode({ data }: NodeProps) {
    const typed = (data ?? {}) as MergeNodeData;
    const label = typeof typed.label === 'string' ? typed.label : 'Merge';
    const errors = Array.isArray(typed.validationErrors)
        ? typed.validationErrors
        : [];
    return (
        <div
            className="relative min-w-[180px] rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 shadow-sm"
            data-testid="node-merge"
        >
            {errors.length > 0 && (
                <div
                    className="absolute -right-2 -top-2 z-10 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-semibold text-white shadow-sm"
                    title={errors
                        .map((e) => `Rule ${e.rule}: ${e.message}`)
                        .join('\n')}
                >
                    {errors.length}
                </div>
            )}
            <Handle
                id="in-1"
                type="target"
                position={Position.Left}
                style={{ top: '35%' }}
                className="!h-2 !w-2 !border-none !bg-blue-500"
            />
            <Handle
                id="in-2"
                type="target"
                position={Position.Left}
                style={{ top: '65%' }}
                className="!h-2 !w-2 !border-none !bg-blue-500"
            />
            <div className="flex items-center gap-2">
                <GitMerge className="h-4 w-4 text-blue-700" aria-hidden="true" />
                <p className="text-sm font-medium text-slate-900">{label}</p>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">Merge branches</p>
            <Handle
                id="out"
                type="source"
                position={Position.Right}
                className="!h-2 !w-2 !border-none !bg-blue-500"
            />
        </div>
    );
}

export default MergeNode;
