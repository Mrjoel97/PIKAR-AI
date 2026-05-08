// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// sonner mock — must be hoisted before component import
vi.mock('sonner', () => ({
    toast: { success: vi.fn(), error: vi.fn() },
}));

import { toast } from 'sonner';
import ApprovalCard from '@/components/chat/ApprovalCard';
import type { WidgetDefinition } from '@/types/widgets';

const TOKEN = 'tok-abc-123';

function makeDefinition(): WidgetDefinition {
    return {
        type: 'approval',
        title: 'Approve a tweet about the launch',
        dismissible: true,
        data: {
            token: TOKEN,
            action_type: 'POST_TWEET',
            requires_response_by: '2099-01-01T12:00:00Z',
            decision_endpoint: `/approvals/${TOKEN}/decision`,
        },
    };
}

const fetchMock = vi.fn();

beforeEach(() => {
    vi.clearAllMocks();
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    // global fetch stub
    (globalThis as { fetch?: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;
});

afterEach(() => {
    delete (globalThis as { fetch?: typeof fetch }).fetch;
});

describe('ApprovalCard', () => {
    it('renders title and Approve / Reject buttons', () => {
        render(<ApprovalCard definition={makeDefinition()} />);
        expect(screen.getByText(/Approve a tweet about the launch/i)).toBeTruthy();
        expect(screen.getByRole('button', { name: /approve/i })).toBeTruthy();
        expect(screen.getByRole('button', { name: /reject/i })).toBeTruthy();
    });

    it('clicking Approve POSTs {decision: "approve"} to decision_endpoint', async () => {
        render(<ApprovalCard definition={makeDefinition()} />);
        fireEvent.click(screen.getByRole('button', { name: /approve/i }));

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledTimes(1);
        });
        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toBe(`/approvals/${TOKEN}/decision`);
        expect(init.method).toBe('POST');
        const body = JSON.parse(init.body as string);
        expect(body).toEqual({ token: TOKEN, decision: 'approve' });
    });

    it('clicking Reject POSTs {decision: "reject"} to decision_endpoint', async () => {
        render(<ApprovalCard definition={makeDefinition()} />);
        fireEvent.click(screen.getByRole('button', { name: /reject/i }));

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledTimes(1);
        });
        const [, init] = fetchMock.mock.calls[0];
        const body = JSON.parse(init.body as string);
        expect(body).toEqual({ token: TOKEN, decision: 'reject' });
    });

    it('disables both buttons after a click', async () => {
        render(<ApprovalCard definition={makeDefinition()} />);
        const approveBtn = screen.getByRole('button', { name: /approve/i });
        const rejectBtn = screen.getByRole('button', { name: /reject/i });

        fireEvent.click(approveBtn);

        await waitFor(() => {
            expect((approveBtn as HTMLButtonElement).disabled).toBe(true);
            expect((rejectBtn as HTMLButtonElement).disabled).toBe(true);
        });
    });

    it('shows toast.success on a 2xx response', async () => {
        render(<ApprovalCard definition={makeDefinition()} />);
        fireEvent.click(screen.getByRole('button', { name: /approve/i }));

        await waitFor(() => {
            expect(toast.success).toHaveBeenCalled();
        });
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('shows toast.error when the POST fails', async () => {
        fetchMock.mockResolvedValueOnce(
            new Response('boom', { status: 500 }),
        );
        render(<ApprovalCard definition={makeDefinition()} />);
        fireEvent.click(screen.getByRole('button', { name: /reject/i }));

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalled();
        });
        expect(toast.success).not.toHaveBeenCalled();
    });
});
