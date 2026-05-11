// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Frontend mirror of the Pydantic `WorkspaceEvent` union shipped from the
 * FastAPI workspace SSE bus (`app/agents/runtime/types.py`).
 *
 * Keep the field names in lockstep with the server payload — the SSE channel
 * carries the raw JSON `model_dump()` output, so any drift here will surface
 * as silent dropped events in `useWorkspaceEvents`.
 */

export type WorkspaceProgressEvent = {
    kind: 'progress';
    agent_id: string;
    contract_id: string | null;
    item: string;
    status: 'started' | 'in_progress' | 'blocked';
};

export type WorkspaceArtifactEvent = {
    kind: 'artifact';
    agent_id: string;
    contract_id: string | null;
    artifact_kind: string;
    ref: string;
    summary: string;
    preview_url: string | null;
};

export type WorkspaceEvent = WorkspaceProgressEvent | WorkspaceArtifactEvent;
