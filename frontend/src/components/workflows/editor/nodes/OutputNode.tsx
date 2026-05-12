'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow custom node for the "output" node kind.
 *
 * Phase 1 of Spec B (read-only viewer) — distinct visual treatment from
 * TriggerNode and AgentActionNode so the user can see the end of the
 * workflow at a glance. Output nodes only have an incoming edge, so they
 * expose only a `target` Handle.
 */

import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { CheckCircle2 } from 'lucide-react';

import {
    getNodeRunStateClasses,
    type NodeRunState,
} from '../runStateStyles';

export interface OutputNodeData {
    label: string;
    runState?: NodeRunState;
    [key: string]: unknown;
}

export function OutputNode({ data }: NodeProps) {
    const typed = (data ?? {}) as OutputNodeData;
    const label = typeof typed.label === 'string' ? typed.label : 'Done';
    const runStateClasses = getNodeRunStateClasses(typed.runState);
    return (
        <div className={`flex flex-col items-center gap-2 ${runStateClasses}`}>
            <Handle
                type="target"
                position={Position.Left}
                className="!h-2 !w-2 !border-none !bg-emerald-500"
            />
            <div className="flex h-14 w-14 items-center justify-center rounded-full border-2 border-emerald-300 bg-emerald-50 shadow-sm">
                <CheckCircle2 className="h-6 w-6 text-emerald-700" aria-hidden="true" />
            </div>
            <p className="max-w-[140px] truncate text-center text-xs font-medium text-slate-700">
                {label}
            </p>
        </div>
    );
}

export default OutputNode;
