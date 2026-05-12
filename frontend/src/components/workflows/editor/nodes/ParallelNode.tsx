'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow custom node for the "parallel" node kind.
 *
 * Phase 110 of Spec B (editable canvas) ships this node VISUALLY only.
 * The asyncio.gather-backed parallel executor is Phase 4 — for now,
 * saving a parallel node works (placeholder Zod schema) but execution
 * ignores it.
 *
 * Shape: blue rounded-rect with a "fork" icon. ONE target handle (left)
 * and TWO source handles (right) labeled "branch-1"/"branch-2". Phase 4
 * will support N source handles dynamically.
 */

import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { GitFork } from 'lucide-react';

import type { ValidationError } from '@/services/workflows';
import {
    getNodeRunStateClasses,
    type NodeRunState,
} from '../runStateStyles';

export interface ParallelNodeData {
    label: string;
    validationErrors?: ValidationError[];
    runState?: NodeRunState;
    [key: string]: unknown;
}

export function ParallelNode({ data }: NodeProps) {
    const typed = (data ?? {}) as ParallelNodeData;
    const label = typeof typed.label === 'string' ? typed.label : 'Parallel';
    const errors = Array.isArray(typed.validationErrors)
        ? typed.validationErrors
        : [];
    const runStateClasses = getNodeRunStateClasses(typed.runState);
    return (
        <div
            className={`relative min-w-[180px] rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 shadow-sm ${runStateClasses}`}
            data-testid="node-parallel"
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
                id="in"
                type="target"
                position={Position.Left}
                className="!h-2 !w-2 !border-none !bg-blue-500"
            />
            <div className="flex items-center gap-2">
                <GitFork className="h-4 w-4 text-blue-700" aria-hidden="true" />
                <p className="text-sm font-medium text-slate-900">{label}</p>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">Parallel fork</p>
            <Handle
                id="branch-1"
                type="source"
                position={Position.Right}
                style={{ top: '35%' }}
                className="!h-2 !w-2 !border-none !bg-blue-500"
            />
            <Handle
                id="branch-2"
                type="source"
                position={Position.Right}
                style={{ top: '65%' }}
                className="!h-2 !w-2 !border-none !bg-blue-500"
            />
        </div>
    );
}

export default ParallelNode;
