// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest integration tests for the Plan 05 conflict flow — Task 05-04.
 *
 * Exercises the page-level wiring of ETagMismatchError → ConflictModal,
 * with particular attention to B-2 (Overwrite path uses body.etag from
 * the 412 response BODY, not the response header).
 *
 * We use a focused harness that imports the page-level handlers we care
 * about by mounting a stripped test surface. The full editor page mounts
 * a lot of Next.js / supabase context that we don't need for the
 * specific flows tested here, so we mock at the service module
 * boundary and assert the second PUT's If-Match header value.
 *
 * Test focus:
 *   1. saveTemplate 412 → ETagMismatchError carries body.etag as freshEtag (B-2)
 *   2. Overwrite re-fire reads conflictState.freshEtag (which equals body.etag)
 *      and sends it verbatim as If-Match (NOT the response header value)
 *   3. The ConflictModal renders correctly given a 412-style ETagMismatchError
 *   4. The handler maps the modal's Overwrite click into a saveTemplate call
 *
 * Implementation detail: we test the service-level B-2 round-trip end-to-end
 * by issuing two consecutive saveTemplate calls — first one mocked to 412
 * (returns body.etag = X, header.etag = WRONG), second one called with
 * the err.freshEtag from the first. Asserts the second PUT's If-Match is X.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/services/api', () => ({
    fetchWithAuthRaw: vi.fn(),
    fetchWithAuth: vi.fn(),
}));

import { fetchWithAuthRaw } from '@/services/api';
import {
    saveTemplate,
    ETagMismatchError,
    type GraphNode,
    type GraphEdge,
    type WorkflowTemplate,
} from '@/services/workflows';
import { ConflictModal } from '@/components/workflows/editor/ConflictModal';

const fetchMock = fetchWithAuthRaw as unknown as ReturnType<typeof vi.fn>;

function makeJsonResponse(
    status: number,
    body: unknown,
    headers: Record<string, string> = {},
): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json', ...headers },
    });
}

const NODES: GraphNode[] = [
    { id: 't', kind: 'trigger', label: 'T', config: {} },
    { id: 'o', kind: 'output', label: 'O', config: {} },
];
const EDGES: GraphEdge[] = [{ id: 'e1', source: 't', target: 'o' }];

describe('editor-conflict-flow — Overwrite uses body.etag (B-2)', () => {
    beforeEach(() => {
        fetchMock.mockReset();
    });

    it('saveTemplate 412 stashes freshEtag from body.etag, NOT header', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(
                412,
                {
                    id: 'tpl-1',
                    name: 'Test',
                    graph_nodes: NODES,
                    graph_edges: EDGES,
                    etag: '"FRESH-FROM-BODY"',
                },
                // Deliberately wrong header value to assert we read body.
                { etag: '"WRONG-FROM-HEADER"' },
            ),
        );

        let caught: ETagMismatchError | null = null;
        try {
            await saveTemplate(
                'tpl-1',
                {
                    graph_nodes: NODES,
                    graph_edges: EDGES,
                    graph_layout: {},
                },
                '"stale-local"',
            );
        } catch (err) {
            caught = err as ETagMismatchError;
        }
        expect(caught).toBeInstanceOf(ETagMismatchError);
        expect(caught!.freshEtag).toBe('"FRESH-FROM-BODY"');
        expect(caught!.freshEtag).not.toBe('"WRONG-FROM-HEADER"');
    });

    it('Overwrite re-fires PUT with body.etag — second PUT carries the body-derived If-Match', async () => {
        // First PUT — 412 with body.etag = X, header = WRONG.
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(
                412,
                {
                    id: 'tpl-1',
                    name: 'Test',
                    graph_nodes: NODES,
                    graph_edges: EDGES,
                    etag: '"X"',
                },
                { etag: '"WRONG"' },
            ),
        );
        // Second PUT — should succeed.
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(200, {
                version: {
                    id: 'v3',
                    template_id: 'tpl-1',
                    version_number: 3,
                    parent_version_id: 'v2',
                    graph_nodes: NODES,
                    graph_edges: EDGES,
                    saved_by_user_id: 'u1',
                    saved_at: '2026-05-11T20:00:00Z',
                },
                etag: '"new"',
            }),
        );

        // First save: catch the 412 → stash freshEtag.
        let conflict: ETagMismatchError | null = null;
        try {
            await saveTemplate(
                'tpl-1',
                {
                    graph_nodes: NODES,
                    graph_edges: EDGES,
                    graph_layout: {},
                },
                '"stale-local"',
            );
        } catch (err) {
            conflict = err as ETagMismatchError;
        }
        expect(conflict).toBeInstanceOf(ETagMismatchError);

        // Now Overwrite: re-fire PUT with conflict.freshEtag (which equals body.etag).
        const result = await saveTemplate(
            'tpl-1',
            {
                graph_nodes: NODES,
                graph_edges: EDGES,
                graph_layout: {},
            },
            conflict!.freshEtag,
        );
        expect(result.version.version_number).toBe(3);

        // Inspect the SECOND fetch call's If-Match header.
        const secondCall = fetchMock.mock.calls[1];
        const opts = secondCall[1] as RequestInit;
        const headers = opts.headers as Record<string, string>;
        // B-2: must be body-derived value (X), NOT the header value (WRONG).
        expect(headers['If-Match']).toBe('"X"');
        expect(headers['If-Match']).not.toBe('"WRONG"');
    });

    it('Overwrite that still races (second 412) preserves the new fresh body.etag', async () => {
        // First PUT — 412 with body.etag = X.
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(412, {
                id: 'tpl-1',
                name: 'Test',
                graph_nodes: NODES,
                graph_edges: EDGES,
                etag: '"X"',
            }),
        );
        // Second PUT (Overwrite) — also 412 (race continued), new body.etag = Y.
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(412, {
                id: 'tpl-1',
                name: 'Test',
                graph_nodes: NODES,
                graph_edges: EDGES,
                etag: '"Y"',
            }),
        );

        let firstConflict: ETagMismatchError | null = null;
        try {
            await saveTemplate(
                'tpl-1',
                { graph_nodes: NODES, graph_edges: EDGES, graph_layout: {} },
                '"stale-local"',
            );
        } catch (err) {
            firstConflict = err as ETagMismatchError;
        }
        expect(firstConflict!.freshEtag).toBe('"X"');

        let secondConflict: ETagMismatchError | null = null;
        try {
            await saveTemplate(
                'tpl-1',
                { graph_nodes: NODES, graph_edges: EDGES, graph_layout: {} },
                firstConflict!.freshEtag,
            );
        } catch (err) {
            secondConflict = err as ETagMismatchError;
        }
        // The new conflict carries Y (the latest body.etag) so the UI's
        // next Overwrite would carry Y, not X.
        expect(secondConflict!.freshEtag).toBe('"Y"');
    });
});

describe('editor-conflict-flow — ConflictModal renders and dispatches actions', () => {
    it('renders three buttons and dispatches the Overwrite handler through secondary confirm', () => {
        const onView = vi.fn();
        const onOverwrite = vi.fn();
        const onCancel = vi.fn();
        const freshTemplate = {
            id: 'tpl-1',
            name: 'Test',
            graph_nodes: NODES,
            graph_edges: EDGES,
        } as unknown as WorkflowTemplate;

        render(
            <ConflictModal
                open={true}
                freshTemplate={freshTemplate}
                onViewTheirChanges={onView}
                onOverwrite={onOverwrite}
                onCancel={onCancel}
            />,
        );

        // All three buttons present.
        expect(screen.getByTestId('conflict-view')).toBeTruthy();
        expect(screen.getByTestId('conflict-overwrite')).toBeTruthy();
        expect(screen.getByTestId('conflict-cancel')).toBeTruthy();

        // Click Overwrite — first click reveals secondary confirm.
        fireEvent.click(screen.getByTestId('conflict-overwrite'));
        expect(onOverwrite).not.toHaveBeenCalled();
        const confirmBtn = screen.getByTestId('conflict-overwrite-confirm');
        expect(confirmBtn).toBeTruthy();

        // Click the confirm — now onOverwrite fires.
        fireEvent.click(confirmBtn);
        expect(onOverwrite).toHaveBeenCalledTimes(1);
        expect(onView).not.toHaveBeenCalled();
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('dispatches View their changes correctly', () => {
        const onView = vi.fn();
        const onOverwrite = vi.fn();
        const onCancel = vi.fn();
        const freshTemplate = {
            id: 'tpl-1',
            name: 'Test',
            graph_nodes: NODES,
            graph_edges: EDGES,
        } as unknown as WorkflowTemplate;

        render(
            <ConflictModal
                open={true}
                freshTemplate={freshTemplate}
                onViewTheirChanges={onView}
                onOverwrite={onOverwrite}
                onCancel={onCancel}
            />,
        );
        fireEvent.click(screen.getByTestId('conflict-view'));
        expect(onView).toHaveBeenCalledTimes(1);
        expect(onOverwrite).not.toHaveBeenCalled();
    });
});
