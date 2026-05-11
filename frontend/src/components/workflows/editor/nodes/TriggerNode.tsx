'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow custom node for the "trigger" node kind.
 *
 * Phase 1 of Spec B (read-only viewer) — distinct visual treatment from
 * AgentActionNode and OutputNode so the user can see the start of the
 * workflow at a glance. Trigger nodes only have an outgoing edge, so they
 * expose only a `source` Handle.
 */

import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Play } from 'lucide-react';

export interface TriggerNodeData {
    label: string;
    [key: string]: unknown;
}

export function TriggerNode({ data }: NodeProps) {
    const label =
        (data && typeof (data as TriggerNodeData).label === 'string'
            ? (data as TriggerNodeData).label
            : 'Start') as string;
    return (
        <div className="flex flex-col items-center gap-2">
            <div className="flex h-14 w-14 items-center justify-center rounded-full border-2 border-teal-300 bg-teal-50 shadow-sm">
                <Play className="h-6 w-6 text-teal-700" aria-hidden="true" />
            </div>
            <p className="max-w-[140px] truncate text-center text-xs font-medium text-slate-700">
                {label}
            </p>
            <Handle
                type="source"
                position={Position.Right}
                className="!h-2 !w-2 !border-none !bg-teal-500"
            />
        </div>
    );
}

export default TriggerNode;
