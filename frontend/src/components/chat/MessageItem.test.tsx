// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { MessageItem } from './MessageItem';

vi.mock('@/components/widgets/WidgetRegistry', () => ({
    WidgetContainer: () => <div data-testid="widget-container" />,
}));

vi.mock('@/components/chat/ThoughtProcess', () => ({
    ThoughtProcess: () => <div data-testid="thought-process" />,
}));

const pushMock = vi.fn();
vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: pushMock }),
}));

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
    toast: {
        success: (...args: unknown[]) => toastSuccessMock(...args),
        error: (...args: unknown[]) => toastErrorMock(...args),
    },
}));

const fetchMock = vi.fn();

beforeEach(() => {
    pushMock.mockReset();
    toastSuccessMock.mockReset();
    toastErrorMock.mockReset();
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('MessageItem — Save to Vault', () => {
    it('renders Save-to-Vault button on agent text messages', () => {
        render(
            <MessageItem
                msg={{ role: 'agent', text: 'Hello world.', agentName: 'ExecutiveAgent' }}
                index={0}
                onToggleWidgetMinimized={() => undefined}
                onWidgetAction={() => undefined}
                onWidgetDismiss={() => undefined}
            />,
        );
        const btn = screen.getByTestId('save-to-vault');
        expect(btn).toBeTruthy();
        expect(btn.getAttribute('aria-label')).toBe('Save to Vault');
    });

    it('does not render Save-to-Vault button on user messages', () => {
        render(
            <MessageItem
                msg={{ role: 'user', text: 'Hi.' }}
                index={0}
                onToggleWidgetMinimized={() => undefined}
                onWidgetAction={() => undefined}
                onWidgetDismiss={() => undefined}
            />,
        );
        expect(screen.queryByTestId('save-to-vault')).toBeNull();
    });

    it('POSTs to /api/vault/save with message content + sessionId on click', async () => {
        fetchMock.mockResolvedValueOnce(
            new Response(JSON.stringify({ ok: true, id: 'doc-1' }), { status: 200 }),
        );

        render(
            <MessageItem
                msg={{ role: 'agent', text: 'Save this insight.' }}
                index={0}
                sessionId="sess-42"
                onToggleWidgetMinimized={() => undefined}
                onWidgetAction={() => undefined}
                onWidgetDismiss={() => undefined}
            />,
        );

        fireEvent.click(screen.getByTestId('save-to-vault'));

        await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
        const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
        expect(url).toBe('/api/vault/save');
        expect(init.method).toBe('POST');
        const body = JSON.parse(init.body as string);
        expect(body.content).toBe('Save this insight.');
        expect(body.type).toBe('note');
        expect(body.session_id).toBe('sess-42');
        await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Saved to Vault'));
    });

    it('shows an error toast when the save endpoint fails', async () => {
        fetchMock.mockResolvedValueOnce(new Response('boom', { status: 500 }));

        render(
            <MessageItem
                msg={{ role: 'agent', text: 'This will fail.' }}
                index={0}
                onToggleWidgetMinimized={() => undefined}
                onWidgetAction={() => undefined}
                onWidgetDismiss={() => undefined}
            />,
        );

        fireEvent.click(screen.getByTestId('save-to-vault'));

        await waitFor(() =>
            expect(toastErrorMock).toHaveBeenCalledWith("Couldn't save — try again"),
        );
    });
});

describe('MessageItem — Find in Vault deep-link', () => {
    it('renders the Find-in-Vault chip when the widget exposes workspace_item_id', () => {
        render(
            <MessageItem
                msg={{
                    role: 'agent',
                    text: 'Here is your image.',
                    widget: {
                        type: 'image',
                        title: 'Hero',
                        data: { imageUrl: 'https://x/y.png', workspace_item_id: 'wi-7' },
                    },
                }}
                index={0}
                onToggleWidgetMinimized={() => undefined}
                onWidgetAction={() => undefined}
                onWidgetDismiss={() => undefined}
            />,
        );
        expect(screen.getByTestId('find-in-vault')).toBeTruthy();
    });

    it('navigates to /dashboard/vault?item=<id> on click', () => {
        render(
            <MessageItem
                msg={{
                    role: 'agent',
                    text: 'Here is your video.',
                    widget: {
                        type: 'video',
                        title: 'Promo',
                        data: { videoUrl: 'https://x/y.mp4' },
                        workspace: { workspaceItemId: 'wi-99', mode: 'focus' },
                    },
                }}
                index={0}
                onToggleWidgetMinimized={() => undefined}
                onWidgetAction={() => undefined}
                onWidgetDismiss={() => undefined}
            />,
        );

        fireEvent.click(screen.getByTestId('find-in-vault'));
        expect(pushMock).toHaveBeenCalledWith('/dashboard/vault?item=wi-99');
    });

    it('does not render the Find-in-Vault chip when no workspace_item_id is present', () => {
        render(
            <MessageItem
                msg={{
                    role: 'agent',
                    text: 'Here is your image.',
                    widget: {
                        type: 'image',
                        title: 'Hero',
                        data: { imageUrl: 'https://x/y.png' },
                    },
                }}
                index={0}
                onToggleWidgetMinimized={() => undefined}
                onWidgetAction={() => undefined}
                onWidgetDismiss={() => undefined}
            />,
        );
        expect(screen.queryByTestId('find-in-vault')).toBeNull();
    });
});
