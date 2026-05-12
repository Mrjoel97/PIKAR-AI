'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow custom node for the "condition" node kind.
 *
 * Phase 110 of Spec B (editable canvas) ships this node VISUALLY only. The
 * branching engine is Phase 3 — saving a condition node works (placeholder
 * Zod schema accepts empty config) but the workflow engine ignores it
 * during execution. The properties drawer shows a "Coming in Phase 3"
 * placeholder body when this node is selected.
 *
 * Shape: a yellow/amber square rotated 45° (diamond) with one target handle
 * (left) and two source handles (right-top labeled "true", right-bottom
 * labeled "false"). Phase 3 will wire the `true`/`false` source handles to
 * the JSONLogic-evaluated outgoing edges.
 */

import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { GitBranch } from 'lucide-react';

import type { ValidationError } from '@/services/workflows';
import {
    getNodeRunStateClasses,
    type NodeRunState,
} from '../runStateStyles';

export interface ConditionNodeData {
    label: string;
    validationErrors?: ValidationError[];
    runState?: NodeRunState;
    [key: string]: unknown;
}

export function ConditionNode({ data }: NodeProps) {
    const typed = (data ?? {}) as ConditionNodeData;
    const label = typeof typed.label === 'string' ? typed.label : 'Condition';
    const errors = Array.isArray(typed.validationErrors)
        ? typed.validationErrors
        : [];
    const runStateClasses = getNodeRunStateClasses(typed.runState);
    return (
        <div
            className={`relative flex flex-col items-center gap-2 ${runStateClasses}`}
            data-testid="node-condition"
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
            <div className="relative h-16 w-16">
                <div className="absolute inset-0 rotate-45 transform rounded-md border-2 border-amber-300 bg-amber-50 shadow-sm" />
                <div className="absolute inset-0 flex items-center justify-center">
                    <GitBranch
                        className="h-5 w-5 text-amber-700"
                        aria-hidden="true"
                    />
                </div>
            </div>
            <p className="max-w-[140px] truncate text-center text-xs font-medium text-slate-700">
                {label}
            </p>
            <p className="-mt-1 text-[10px] uppercase tracking-wide text-slate-400">
                Condition
            </p>
            <Handle
                id="in"
                type="target"
                position={Position.Left}
                className="!h-2 !w-2 !border-none !bg-amber-500"
            />
            <Handle
                id="true"
                type="source"
                position={Position.Right}
                style={{ top: '35%' }}
                className="!h-2 !w-2 !border-none !bg-emerald-500"
            />
            <Handle
                id="false"
                type="source"
                position={Position.Right}
                style={{ top: '65%' }}
                className="!h-2 !w-2 !border-none !bg-rose-500"
            />
        </div>
    );
}

export default ConditionNode;
