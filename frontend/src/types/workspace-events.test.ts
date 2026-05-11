// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect } from 'vitest';
import type {
    WorkspaceEvent,
    WorkspaceProgressEvent,
    WorkspaceArtifactEvent,
} from './workspace-events';

describe('WorkspaceEvent discriminated union', () => {
    it('narrows on kind === "progress"', () => {
        const event: WorkspaceEvent = {
            kind: 'progress',
            agent_id: 'FIN',
            contract_id: '00000000-0000-0000-0000-000000000001',
            item: 'Pull 12 months of revenue',
            status: 'in_progress',
        };
        if (event.kind === 'progress') {
            const narrowed: WorkspaceProgressEvent = event;
            expect(narrowed.status).toBe('in_progress');
        }
    });

    it('narrows on kind === "artifact"', () => {
        const event: WorkspaceEvent = {
            kind: 'artifact',
            agent_id: 'FIN',
            contract_id: null,
            artifact_kind: 'report',
            ref: 'vault://doc/123',
            summary: 'FY26 forecast',
            preview_url: null,
        };
        if (event.kind === 'artifact') {
            const narrowed: WorkspaceArtifactEvent = event;
            expect(narrowed.artifact_kind).toBe('report');
        }
    });
});
