'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Phase 111 Plan 05 — WorkflowGraphRunWidget (stub).
 *
 * The full implementation lands in Task 05-03 (RED + GREEN). Task 05-02
 * ships this STUB component so:
 *   1. The dynamic import inside WidgetRegistry.tsx resolves.
 *   2. The routing helper resolveWorkflowRunWidget can hand-off to a
 *      registered component.
 *   3. The registry test `WIDGET_MAP_has_workflow_graph_run` passes by
 *      proving resolveWidget('workflow_graph_run') returns a registered
 *      component (not UnknownWidget).
 *
 * Task 05-03 replaces the body with the real live-state React Flow widget.
 */

import React from 'react';
import { WidgetProps } from './WidgetRegistry';

export default function WorkflowGraphRunWidget(_: WidgetProps) {
    return (
        <div
            data-testid="workflow-graph-run-widget-stub"
            className="p-4 text-sm text-slate-500"
        >
            Loading branched run...
        </div>
    );
}
