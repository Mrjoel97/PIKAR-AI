// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for getTemplateHistory + revertTemplate service methods
 * (Phase 110 Plan 05 Task 05-01).
 *
 * Covers:
 *   - getTemplateHistory: GET /workflows/templates/{id}/history → list[HistoryItem]
 *   - getTemplateHistory: 404/403 → throws Error
 *   - revertTemplate: POST /workflows/templates/{id}/revert/{version_id} with If-Match
 *   - revertTemplate: 200 → SaveTemplateSuccessResponse with body.etag (B-2 parity)
 *   - revertTemplate: 412 → ETagMismatchError with body.etag as freshEtag (B-2)
 *
 * Mocking strategy: vi.mock the './api' module so we can intercept
 * fetchWithAuthRaw without touching the real network or supabase session.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock './api' BEFORE importing the service.
vi.mock('@/services/api', () => ({
    fetchWithAuthRaw: vi.fn(),
    fetchWithAuth: vi.fn(),
}));

import { fetchWithAuthRaw, fetchWithAuth } from '@/services/api';
import {
    getTemplateHistory,
    revertTemplate,
    ETagMismatchError,
} from '@/services/workflows';

const rawMock = fetchWithAuthRaw as unknown as ReturnType<typeof vi.fn>;
const authMock = fetchWithAuth as unknown as ReturnType<typeof vi.fn>;

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

const SAMPLE_HISTORY = [
    {
        version_id: 'v3',
        version_number: 3,
        saved_at: '2026-05-11T20:00:00Z',
        saved_by_user_id: 'u1',
        saved_by_user_name: 'Alice',
        comment: 'Added approval step',
    },
    {
        version_id: 'v2',
        version_number: 2,
        saved_at: '2026-05-11T19:00:00Z',
        saved_by_user_id: 'u1',
        saved_by_user_name: 'Alice',
        comment: null,
    },
    {
        version_id: 'v1',
        version_number: 1,
        saved_at: '2026-05-11T18:00:00Z',
        saved_by_user_id: 'u2',
        saved_by_user_name: 'Bob',
        comment: 'Initial save',
    },
];

describe('getTemplateHistory', () => {
    beforeEach(() => {
        rawMock.mockReset();
        authMock.mockReset();
    });

    it('returns array of HistoryItem from GET /history', async () => {
        rawMock.mockResolvedValueOnce(
            makeJsonResponse(200, SAMPLE_HISTORY),
        );
        const history = await getTemplateHistory('tpl-1');
        expect(history).toHaveLength(3);
        expect(history[0].version_number).toBe(3);
        expect(history[0].saved_by_user_name).toBe('Alice');
        expect(history[2].comment).toBe('Initial save');
    });

    it('issues GET against /workflows/templates/{id}/history', async () => {
        rawMock.mockResolvedValueOnce(makeJsonResponse(200, []));
        await getTemplateHistory('tpl-abc');
        expect(rawMock).toHaveBeenCalled();
        const callArgs = rawMock.mock.calls[0];
        expect(callArgs[0]).toBe('/workflows/templates/tpl-abc/history');
        const opts = callArgs[1] as RequestInit | undefined;
        // GET — no method or method='GET' both acceptable
        if (opts?.method) expect(opts.method).toBe('GET');
    });

    it('rejects on 404 (template not found)', async () => {
        rawMock.mockResolvedValueOnce(
            makeJsonResponse(404, { detail: 'Not found' }),
        );
        await expect(getTemplateHistory('missing')).rejects.toThrow(
            /not found|404/i,
        );
    });

    it('rejects on 403 (forbidden)', async () => {
        rawMock.mockResolvedValueOnce(
            makeJsonResponse(403, { detail: 'Forbidden' }),
        );
        await expect(getTemplateHistory('forbidden')).rejects.toThrow(
            /forbidden|403/i,
        );
    });

    it('returns empty array when template has no versions', async () => {
        rawMock.mockResolvedValueOnce(makeJsonResponse(200, []));
        const history = await getTemplateHistory('tpl-1');
        expect(history).toEqual([]);
    });
});

describe('revertTemplate', () => {
    beforeEach(() => {
        rawMock.mockReset();
        authMock.mockReset();
    });

    const FRESH_VERSION = {
        id: 'v4',
        template_id: 'tpl-1',
        version_number: 4,
        parent_version_id: 'v2',
        graph_nodes: [],
        graph_edges: [],
        saved_by_user_id: 'u1',
        saved_at: '2026-05-11T21:00:00Z',
    };

    it('sends POST with If-Match header verbatim', async () => {
        rawMock.mockResolvedValueOnce(
            makeJsonResponse(200, {
                version: FRESH_VERSION,
                etag: '"2026-05-11T21:00:00Z"',
            }),
        );
        const SENT_ETAG = '"2026-05-11T20:00:00Z"';
        await revertTemplate('tpl-1', 'v2', SENT_ETAG);
        const callArgs = rawMock.mock.calls[0];
        expect(callArgs[0]).toBe('/workflows/templates/tpl-1/revert/v2');
        const opts = callArgs[1] as RequestInit;
        expect(opts.method).toBe('POST');
        const headers = opts.headers as Record<string, string>;
        expect(headers['If-Match']).toBe(SENT_ETAG);
    });

    it('200 returns SaveTemplateSuccessResponse-shaped {version, etag} — B-2 parity', async () => {
        rawMock.mockResolvedValueOnce(
            makeJsonResponse(
                200,
                {
                    version: FRESH_VERSION,
                    etag: '"2026-05-11T21:00:00Z"',
                },
                // Deliberately wrong header value to assert we read body.etag
                { etag: '"WRONG-FROM-HEADER"' },
            ),
        );
        const result = await revertTemplate('tpl-1', 'v2', '"any"');
        // body.etag is canonical (B-2)
        expect(result.etag).toBe('"2026-05-11T21:00:00Z"');
        expect(result.version.version_number).toBe(4);
        expect(result.version.parent_version_id).toBe('v2');
    });

    it('412 throws ETagMismatchError with body.etag as freshEtag — B-2', async () => {
        rawMock.mockResolvedValueOnce(
            makeJsonResponse(
                412,
                {
                    id: 'tpl-1',
                    name: 'Test',
                    graph_nodes: [],
                    graph_edges: [],
                    etag: '"FRESH-FROM-BODY"',
                },
                { etag: '"WRONG-FROM-HEADER"' },
            ),
        );
        try {
            await revertTemplate('tpl-1', 'v2', '"stale"');
            throw new Error('expected throw');
        } catch (err) {
            expect(err).toBeInstanceOf(ETagMismatchError);
            const e = err as ETagMismatchError;
            expect(e.freshEtag).toBe('"FRESH-FROM-BODY"');
        }
    });

    it('non-2xx (500) throws a generic Error with status code', async () => {
        rawMock.mockResolvedValueOnce(
            makeJsonResponse(500, { detail: 'server error' }),
        );
        await expect(
            revertTemplate('tpl-1', 'v2', '"any"'),
        ).rejects.toThrow(/500|revert failed/i);
    });
});
