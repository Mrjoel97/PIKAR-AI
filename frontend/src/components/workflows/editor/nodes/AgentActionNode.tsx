'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow custom node for the "agent-action" node kind.
 *
 * Phase 1 of Spec B (read-only viewer) — the bread-and-butter node type
 * representing a single agent tool invocation in the workflow. Renders the
 * node label and the underlying tool name from config. Exposes both
 * `target` (left) and `source` (right) Handles since agent-action nodes
 * sit in the middle of the linear chain.
 */

import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';

import {
    getNodeRunStateClasses,
    type NodeRunState,
} from '../runStateStyles';

export interface AgentActionNodeData {
    label: string;
    tool_name?: string;
    runState?: NodeRunState;
    [key: string]: unknown;
}

export function AgentActionNode({ data }: NodeProps) {
    const typed = (data ?? {}) as AgentActionNodeData;
    const label = typeof typed.label === 'string' ? typed.label : 'Agent Action';
    const toolName = typeof typed.tool_name === 'string' ? typed.tool_name : null;
    const runStateClasses = getNodeRunStateClasses(typed.runState);
    return (
        <div
            className={`min-w-[180px] rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm ${runStateClasses}`}
        >
            <Handle
                type="target"
                position={Position.Left}
                className="!h-2 !w-2 !border-none !bg-slate-400"
            />
            <p className="text-sm font-medium text-slate-900">{label}</p>
            {toolName && (
                <p className="mt-1 truncate font-mono text-[11px] text-slate-500">
                    {toolName}
                </p>
            )}
            <Handle
                type="source"
                position={Position.Right}
                className="!h-2 !w-2 !border-none !bg-slate-400"
            />
        </div>
    );
}

export default AgentActionNode;
