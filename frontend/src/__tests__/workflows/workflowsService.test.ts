// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for frontend/src/services/workflows.ts — Phase 110 Plan 04.
 *
 * Covers the new saveTemplate / validateTemplate / getWorkflowTemplateWithEtag
 * service methods + three typed error classes (ETagMismatchError, CopyForkError,
 * ValidationFailedError) wired to Plan 02's PUT contract:
 *   - 200 → SaveTemplateSuccessResponse; body.etag is the canonical next-write ETag (B-2)
 *   - 412 → ETagMismatchError with body.etag as freshEtag (B-2)
 *   - 409 → CopyForkError with body.copied_template_id + body.seed_name (W-4)
 *   - 400 → ValidationFailedError from Plan 03's wired validate_workflow_graph
 *   - 428 → generic Error('If-Match required')
 *
 * Mocking strategy: vi.mock the './api' module so we can intercept
 * fetchWithAuthRaw without touching the real network or supabase session.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock './api' BEFORE importing the service. We use a per-test mockResolvedValue
// to return whatever Response shape the test needs.
vi.mock('@/services/api', () => ({
    fetchWithAuthRaw: vi.fn(),
    fetchWithAuth: vi.fn(),
}));

import { fetchWithAuthRaw } from '@/services/api';
import {
    saveTemplate,
    validateTemplate,
    getWorkflowTemplateWithEtag,
    ETagMismatchError,
    CopyForkError,
    ValidationFailedError,
    type GraphNode,
    type GraphEdge,
} from '@/services/workflows';

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

const SAMPLE_NODES: GraphNode[] = [
    { id: 't', kind: 'trigger', label: 'T', config: {} },
    { id: 'o', kind: 'output', label: 'O', config: {} },
];
const SAMPLE_EDGES: GraphEdge[] = [{ id: 'e1', source: 't', target: 'o' }];

describe('saveTemplate (B-2 wire format)', () => {
    beforeEach(() => {
        fetchMock.mockReset();
    });

    it('200 returns etag from response BODY (not response header) — B-2', async () => {
        // Deliberately put different etag values in body vs header to prove
        // the implementation reads body, not header.
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(
                200,
                {
                    version: {
                        id: 'v2',
                        template_id: 'tpl-1',
                        version_number: 2,
                        parent_version_id: 'v1',
                        graph_nodes: SAMPLE_NODES,
                        graph_edges: SAMPLE_EDGES,
                        saved_by_user_id: 'u1',
                        saved_at: '2026-05-11T20:00:00Z',
                    },
                    etag: '"2026-05-11T20:00:00Z"',
                },
                { etag: '"WRONG-FROM-HEADER"' },
            ),
        );
        const result = await saveTemplate(
            'tpl-1',
            {
                graph_nodes: SAMPLE_NODES,
                graph_edges: SAMPLE_EDGES,
                graph_layout: {},
            },
            '"2026-05-11T19:00:00Z"',
        );
        expect(result.etag).toBe('"2026-05-11T20:00:00Z"');
        expect(result.version.version_number).toBe(2);
    });

    it('sends If-Match header verbatim (no requote, no strip)', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(200, {
                version: {
                    id: 'v2',
                    template_id: 'tpl-1',
                    version_number: 2,
                    parent_version_id: null,
                    graph_nodes: SAMPLE_NODES,
                    graph_edges: SAMPLE_EDGES,
                    saved_by_user_id: 'u1',
                    saved_at: '2026-05-11T20:00:00Z',
                },
                etag: '"new"',
            }),
        );
        const SENT_ETAG = '"2026-05-11T19:30:00.000Z"';
        await saveTemplate(
            'tpl-1',
            {
                graph_nodes: SAMPLE_NODES,
                graph_edges: SAMPLE_EDGES,
                graph_layout: {},
            },
            SENT_ETAG,
        );
        const callArgs = fetchMock.mock.calls[0];
        const opts = callArgs[1] as RequestInit;
        const headers = opts.headers as Record<string, string>;
        // If-Match must be sent EXACTLY as provided (with quotes).
        expect(headers['If-Match']).toBe(SENT_ETAG);
    });

    it('412 throws ETagMismatchError with body.etag as freshEtag — B-2', async () => {
        // Different etag values in body vs header — assert reader picks body.
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(
                412,
                {
                    id: 'tpl-1',
                    name: 'Test',
                    graph_nodes: SAMPLE_NODES,
                    graph_edges: SAMPLE_EDGES,
                    etag: '"FRESH-FROM-BODY"',
                },
                { etag: '"WRONG-FROM-HEADER"' },
            ),
        );
        await expect(
            saveTemplate(
                'tpl-1',
                {
                    graph_nodes: SAMPLE_NODES,
                    graph_edges: SAMPLE_EDGES,
                    graph_layout: {},
                },
                '"stale"',
            ),
        ).rejects.toBeInstanceOf(ETagMismatchError);
        // Run again to assert the carried freshEtag
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(412, {
                id: 'tpl-1',
                name: 'Test',
                etag: '"X"',
            }),
        );
        try {
            await saveTemplate(
                'tpl-1',
                {
                    graph_nodes: SAMPLE_NODES,
                    graph_edges: SAMPLE_EDGES,
                    graph_layout: {},
                },
                '"stale"',
            );
            throw new Error('expected throw');
        } catch (err) {
            expect(err).toBeInstanceOf(ETagMismatchError);
            expect((err as ETagMismatchError).freshEtag).toBe('"X"');
        }
    });

    it('409 throws CopyForkError reading body.copied_template_id AND body.seed_name — W-4', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(409, {
                error: 'seed_template_immutable',
                copied_template_id: 'tpl-copy-xyz',
                seed_name: 'Sales Workflow',
                message: 'Created a private copy',
            }),
        );
        try {
            await saveTemplate(
                'tpl-seed',
                {
                    graph_nodes: SAMPLE_NODES,
                    graph_edges: SAMPLE_EDGES,
                    graph_layout: {},
                },
                '"any"',
            );
            throw new Error('expected throw');
        } catch (err) {
            expect(err).toBeInstanceOf(CopyForkError);
            const e = err as CopyForkError;
            expect(e.copiedTemplateId).toBe('tpl-copy-xyz');
            expect(e.seedName).toBe('Sales Workflow');
        }
    });

    it('400 throws ValidationFailedError with body errors list — Plan 03 wire-in', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(400, {
                detail: {
                    error: 'validation_failed',
                    errors: [
                        {
                            node_id: null,
                            rule: 1,
                            message: 'No trigger node found',
                        },
                        {
                            node_id: 'a1',
                            rule: 7,
                            message: 'Config invalid for agent-action: tool_name',
                        },
                    ],
                },
            }),
        );
        try {
            await saveTemplate(
                'tpl-1',
                {
                    graph_nodes: [],
                    graph_edges: [],
                    graph_layout: {},
                },
                '"any"',
            );
            throw new Error('expected throw');
        } catch (err) {
            expect(err).toBeInstanceOf(ValidationFailedError);
            const e = err as ValidationFailedError;
            expect(e.errors.length).toBe(2);
            expect(e.errors[0].rule).toBe(1);
            expect(e.errors[1].node_id).toBe('a1');
        }
    });

    it('428 throws a generic Error mentioning If-Match', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(428, {
                detail: 'If-Match header required',
            }),
        );
        try {
            await saveTemplate(
                'tpl-1',
                {
                    graph_nodes: SAMPLE_NODES,
                    graph_edges: SAMPLE_EDGES,
                    graph_layout: {},
                },
                '',
            );
            throw new Error('expected throw');
        } catch (err) {
            expect(err).toBeInstanceOf(Error);
            expect(/if-match/i.test((err as Error).message)).toBe(true);
            expect(err).not.toBeInstanceOf(ETagMismatchError);
            expect(err).not.toBeInstanceOf(CopyForkError);
        }
    });

    it('sends PUT with the right URL + JSON body', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(200, {
                version: {
                    id: 'v2',
                    template_id: 'tpl-1',
                    version_number: 2,
                    parent_version_id: null,
                    graph_nodes: SAMPLE_NODES,
                    graph_edges: SAMPLE_EDGES,
                    saved_by_user_id: 'u1',
                    saved_at: '2026-05-11T20:00:00Z',
                },
                etag: '"e"',
            }),
        );
        await saveTemplate(
            'tpl-1',
            {
                graph_nodes: SAMPLE_NODES,
                graph_edges: SAMPLE_EDGES,
                graph_layout: { t: { x: 0, y: 0 } },
                comment: 'first save',
            },
            '"old"',
        );
        const callArgs = fetchMock.mock.calls[0];
        expect(callArgs[0]).toBe('/workflows/templates/tpl-1');
        const opts = callArgs[1] as RequestInit;
        expect(opts.method).toBe('PUT');
        const body = JSON.parse(opts.body as string);
        expect(body.graph_nodes).toEqual(SAMPLE_NODES);
        expect(body.comment).toBe('first save');
    });
});

describe('validateTemplate', () => {
    beforeEach(() => {
        fetchMock.mockReset();
    });

    it('POSTs to /validate with body and returns errors[]', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(200, {
                errors: [
                    {
                        node_id: null,
                        rule: 1,
                        message: 'No trigger node found',
                    },
                ],
            }),
        );
        const errors = await validateTemplate('tpl-1', {
            graph_nodes: [],
            graph_edges: [],
        });
        expect(errors.length).toBe(1);
        expect(errors[0].rule).toBe(1);
        const callArgs = fetchMock.mock.calls[0];
        expect(callArgs[0]).toBe('/workflows/templates/tpl-1/validate');
        const opts = callArgs[1] as RequestInit;
        expect(opts.method).toBe('POST');
    });

    it('returns empty array when graph is valid', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(200, { errors: [] }),
        );
        const errors = await validateTemplate('tpl-1', {
            graph_nodes: SAMPLE_NODES,
            graph_edges: SAMPLE_EDGES,
        });
        expect(errors).toEqual([]);
    });
});

describe('getWorkflowTemplateWithEtag', () => {
    beforeEach(() => {
        fetchMock.mockReset();
    });

    it('captures ETag from response HEADERS (canonical for GET) and stores on _etag', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(
                200,
                {
                    id: 'tpl-1',
                    name: 'Test',
                    graph_nodes: SAMPLE_NODES,
                    graph_edges: SAMPLE_EDGES,
                },
                { etag: '"2026-05-11T18:00:00Z"' },
            ),
        );
        const result = await getWorkflowTemplateWithEtag('tpl-1');
        expect(result._etag).toBe('"2026-05-11T18:00:00Z"');
        expect(result.id).toBe('tpl-1');
    });

    it('returns undefined _etag when header is missing (graceful degradation)', async () => {
        fetchMock.mockResolvedValueOnce(
            makeJsonResponse(200, {
                id: 'tpl-1',
                name: 'Test',
            }),
        );
        const result = await getWorkflowTemplateWithEtag('tpl-1');
        // Header absent → undefined (so callers can detect missing ETag)
        expect(result._etag).toBeUndefined();
    });
});
