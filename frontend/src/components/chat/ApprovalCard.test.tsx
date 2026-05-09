// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('sonner', () => ({
    toast: { success: vi.fn(), error: vi.fn() },
}));

import { toast } from 'sonner';
import { ApprovalCard } from './ApprovalCard';
import type { WidgetDefinition } from '@/types/widgets';

const baseDefinition: WidgetDefinition = {
    type: 'approval',
    title: 'Post launch tweet',
    dismissible: true,
    data: {
        token: 'tok-abc',
        action_type: 'POST_TWEET',
        decision_endpoint: 'http://api.test/approvals/tok-abc/decision',
        requires_response_by: '2030-01-01T00:00:00.000Z',
    } as Record<string, unknown>,
};

function mockFetchOk() {
    const fetchMock = vi.fn(() =>
        Promise.resolve(new Response(JSON.stringify({ success: true }), { status: 200 })),
    );
    // @ts-expect-error - assign to global for jsdom
    global.fetch = fetchMock;
    return fetchMock;
}

function mockFetchFail() {
    const fetchMock = vi.fn(() =>
        Promise.resolve(new Response('boom', { status: 500 })),
    );
    // @ts-expect-error - assign to global for jsdom
    global.fetch = fetchMock;
    return fetchMock;
}

describe('ApprovalCard', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders title, action type, and Approve/Reject buttons', () => {
        mockFetchOk();
        render(<ApprovalCard definition={baseDefinition} />);

        expect(screen.getByText(/Post launch tweet/i)).toBeTruthy();
        expect(screen.getByText(/POST TWEET/i)).toBeTruthy();
        expect(screen.getByTestId('approval-approve')).toBeTruthy();
        expect(screen.getByTestId('approval-reject')).toBeTruthy();
    });

    it('Approve click POSTs {decision: "approve"} to decision_endpoint', async () => {
        const fetchMock = mockFetchOk();
        render(<ApprovalCard definition={baseDefinition} />);

        fireEvent.click(screen.getByTestId('approval-approve'));

        await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toBe('http://api.test/approvals/tok-abc/decision');
        expect(init?.method).toBe('POST');
        const body = JSON.parse((init?.body as string) || '{}');
        expect(body).toEqual({ token: 'tok-abc', decision: 'approve' });
    });

    it('Reject click POSTs {decision: "reject"} to decision_endpoint', async () => {
        const fetchMock = mockFetchOk();
        render(<ApprovalCard definition={baseDefinition} />);

        fireEvent.click(screen.getByTestId('approval-reject'));

        await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
        const body = JSON.parse((fetchMock.mock.calls[0][1]?.body as string) || '{}');
        expect(body).toEqual({ token: 'tok-abc', decision: 'reject' });
    });

    it('disables both buttons after a click', async () => {
        mockFetchOk();
        render(<ApprovalCard definition={baseDefinition} />);

        const approve = screen.getByTestId('approval-approve') as HTMLButtonElement;
        const reject = screen.getByTestId('approval-reject') as HTMLButtonElement;

        fireEvent.click(approve);

        await waitFor(() => expect(approve.disabled).toBe(true));
        expect(reject.disabled).toBe(true);
    });

    it('shows toast.success on a 2xx response', async () => {
        mockFetchOk();
        render(<ApprovalCard definition={baseDefinition} />);

        fireEvent.click(screen.getByTestId('approval-approve'));

        await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Decision recorded.'));
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('shows toast.error when the request fails', async () => {
        mockFetchFail();
        render(<ApprovalCard definition={baseDefinition} />);

        fireEvent.click(screen.getByTestId('approval-reject'));

        await waitFor(() => expect(toast.error).toHaveBeenCalled());
        expect(toast.success).not.toHaveBeenCalled();
    });
});
