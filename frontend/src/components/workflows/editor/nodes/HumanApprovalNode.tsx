'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow custom node for the "human-approval" node kind.
 *
 * Phase 110 of Spec B (editable canvas) ships this node VISUALLY only.
 * Phase 4 will wire it to Spec A's approval endpoint — saving works
 * (placeholder Zod schema) but execution ignores it for now.
 *
 * Shape: purple rounded-rect with a "user-check" icon. ONE target handle
 * (left) and ONE source handle (right).
 */

import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { UserCheck } from 'lucide-react';

import type { ValidationError } from '@/services/workflows';
import {
    getNodeRunStateClasses,
    type NodeRunState,
} from '../runStateStyles';

export interface HumanApprovalNodeData {
    label: string;
    validationErrors?: ValidationError[];
    runState?: NodeRunState;
    [key: string]: unknown;
}

export function HumanApprovalNode({ data }: NodeProps) {
    const typed = (data ?? {}) as HumanApprovalNodeData;
    const label =
        typeof typed.label === 'string' ? typed.label : 'Human approval';
    const errors = Array.isArray(typed.validationErrors)
        ? typed.validationErrors
        : [];
    const runStateClasses = getNodeRunStateClasses(typed.runState);
    return (
        <div
            className={`relative min-w-[180px] rounded-2xl border border-purple-200 bg-purple-50 px-4 py-3 shadow-sm ${runStateClasses}`}
            data-testid="node-human-approval"
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
                className="!h-2 !w-2 !border-none !bg-purple-500"
            />
            <div className="flex items-center gap-2">
                <UserCheck
                    className="h-4 w-4 text-purple-700"
                    aria-hidden="true"
                />
                <p className="text-sm font-medium text-slate-900">{label}</p>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">Human approval</p>
            <Handle
                id="out"
                type="source"
                position={Position.Right}
                className="!h-2 !w-2 !border-none !bg-purple-500"
            />
        </div>
    );
}

export default HumanApprovalNode;
