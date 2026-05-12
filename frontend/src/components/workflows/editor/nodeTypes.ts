// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Shared NODE_TYPES map for React Flow.
 *
 * Extracted from `NodeCanvas.tsx` (Phase 109 + 110) so it can be reused by
 * the Phase 111 `WorkflowGraphRunWidget` without re-implementing the 7
 * visual node components. NodeCanvas re-imports this map; the
 * WorkflowGraphRunWidget imports it for live-run rendering.
 *
 * Phase 111 Plan 05 — Discretion #6: workspace widget reuses the editor's
 * node components by importing NODE_TYPES from this shared module.
 */

import { TriggerNode } from './nodes/TriggerNode';
import { AgentActionNode } from './nodes/AgentActionNode';
import { OutputNode } from './nodes/OutputNode';
import { ConditionNode } from './nodes/ConditionNode';
import { ParallelNode } from './nodes/ParallelNode';
import { MergeNode } from './nodes/MergeNode';
import { HumanApprovalNode } from './nodes/HumanApprovalNode';

/**
 * React Flow nodeTypes map. Must be defined at module scope (not inline) so
 * React Flow does not warn about "It looks like you have created a new
 * nodeTypes object" on every render.
 *
 * Keys match the `kind` field on `GraphNode` (see api.generated.ts).
 */
export const NODE_TYPES = {
    trigger: TriggerNode,
    'agent-action': AgentActionNode,
    output: OutputNode,
    condition: ConditionNode,
    parallel: ParallelNode,
    merge: MergeNode,
    'human-approval': HumanApprovalNode,
} as const;

export default NODE_TYPES;
