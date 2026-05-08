/**
 * @vitest-environment jsdom
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, act } from '@testing-library/react'
import '@testing-library/jest-dom'

// ---------------------------------------------------------------------------
// Mocks for heavy dependencies that ConfigurationPage pulls in transitively.
// These are not the subject of the WORKSPACE-01 tests; we just need the page
// to render so we can exercise the Google Workspace branch.
// ---------------------------------------------------------------------------

vi.mock('@/components/layout/PremiumShell', () => ({
    PremiumShell: ({ children }: { children: any }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/DashboardErrorBoundary', () => ({
    default: ({ children }: { children: any }) => <div>{children}</div>,
}))

vi.mock('framer-motion', () => ({
    motion: new Proxy(
        {},
        {
            get:
                () =>
                ({ children, ...props }: any) =>
                    <div {...props}>{children}</div>,
        },
    ),
    AnimatePresence: ({ children }: { children: any }) => <>{children}</>,
}))

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}))

vi.mock('@/services/integrations', () => ({
    fetchProviders: vi.fn().mockResolvedValue([]),
    fetchIntegrationStatus: vi.fn().mockResolvedValue([]),
    disconnectProvider: vi.fn().mockResolvedValue({ disconnected: true, provider: 'noop' }),
    // disconnectGoogleWorkspace will be added in Task 2; mock a placeholder so
    // ConfigurationPage's import resolves either before or after that change.
    disconnectGoogleWorkspace: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@/services/api', () => ({
    API_BASE_URL: '',
    fetchWithAuth: vi.fn(async () => new Response('{}', { status: 200 })),
    fetchWithAuthRaw: vi.fn(async () => new Response('{}', { status: 200 })),
}))

vi.mock('@/services/builtInResearchProviders', () => ({
    BUILT_IN_RESEARCH_PROVIDER_FALLBACKS: [],
    normalizeBuiltInResearchProviders: (x?: any) => x || [],
}))

// ---------------------------------------------------------------------------
// Helpers — fetch mock with per-URL routing for the endpoints this card uses.
// ---------------------------------------------------------------------------

interface FetchScript {
    googleWorkspaceStatus?: any
    googleWorkspaceStatusAfter?: any
    disconnectStatus?: number
}

function installFetchMock(script: FetchScript = {}) {
    const calls: Array<{ url: string; init?: RequestInit }> = []
    let workspaceFetchCount = 0

    const fetchSpy = vi.fn(async (url: any, init?: RequestInit) => {
        const u = typeof url === 'string' ? url : url?.url ?? String(url)
        calls.push({ url: u, init })

        if (u.includes('/api/configuration/google-workspace-status')) {
            workspaceFetchCount += 1
            const payload =
                workspaceFetchCount > 1 && script.googleWorkspaceStatusAfter !== undefined
                    ? script.googleWorkspaceStatusAfter
                    : script.googleWorkspaceStatus ?? {
                          connected: false,
                          features: [],
                          message: '',
                      }
            return new Response(JSON.stringify(payload), {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            })
        }

        if (u.includes('/api/configuration/google-workspace') && init?.method === 'DELETE') {
            return new Response('{}', { status: script.disconnectStatus ?? 200 })
        }

        // Default: return empty success for any other endpoint the page touches
        return new Response('{}', {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
        })
    })

    // @ts-expect-error - test override
    global.fetch = fetchSpy
    return { fetchSpy, calls }
}

async function flushAsync() {
    await act(async () => {
        await Promise.resolve()
        await Promise.resolve()
        await Promise.resolve()
    })
}

describe('Google Workspace integration card (WORKSPACE-01)', () => {
    let originalFetch: typeof fetch
    let originalConfirm: typeof window.confirm
    let originalAlert: typeof window.alert

    beforeEach(() => {
        // Use clearAllMocks (not resetAllMocks) so the `vi.mock()` factory
        // implementations from `@/services/integrations` and `@/services/api`
        // remain wired across tests.
        vi.clearAllMocks()
        originalFetch = global.fetch
        originalConfirm = window.confirm
        originalAlert = window.alert
        window.confirm = vi.fn(() => true)
        window.alert = vi.fn()
    })

    afterEach(() => {
        cleanup()
        global.fetch = originalFetch
        window.confirm = originalConfirm
        window.alert = originalAlert
    })

    it('shows Connect button (and no legacy "sign out" copy) when disconnected', async () => {
        installFetchMock({
            googleWorkspaceStatus: {
                connected: false,
                features: [],
                message: '',
            },
        })

        const { default: ConfigurationPage } = await import('../page')
        render(<ConfigurationPage />)
        await flushAsync()

        await waitFor(
            () => {
                expect(
                    screen.getByRole('button', { name: /connect google workspace/i }),
                ).toBeInTheDocument()
            },
            { timeout: 2500 },
        )

        expect(screen.queryByText(/sign out and sign back in/i)).not.toBeInTheDocument()
    })

    it('clicking Connect opens popup at /api/integrations/google_workspace/authorize', async () => {
        installFetchMock({
            googleWorkspaceStatus: { connected: false, features: [], message: '' },
        })
        const openSpy = vi
            .spyOn(window, 'open')
            .mockReturnValue({ focus: vi.fn(), closed: false } as any)

        const { default: ConfigurationPage } = await import('../page')
        render(<ConfigurationPage />)
        await flushAsync()

        const btn = await screen.findByRole(
            'button',
            { name: /connect google workspace/i },
            { timeout: 2500 },
        )
        fireEvent.click(btn)

        expect(openSpy).toHaveBeenCalledTimes(1)
        const args = openSpy.mock.calls[0]
        expect(args[0]).toMatch(/\/api\/integrations\/google_workspace\/authorize/)
        expect(args[1]).toBe('oauth-popup')
        expect(String(args[2])).toContain('width=600')
        expect(String(args[2])).toContain('height=700')
    })

    it('postMessage triggers re-fetch of workspace status and flips UI to connected', async () => {
        installFetchMock({
            googleWorkspaceStatus: {
                connected: false,
                features: [],
                message: '',
            },
            googleWorkspaceStatusAfter: {
                connected: true,
                email: 'user@example.com',
                features: ['Docs', 'Sheets'],
                message: '',
            },
        })

        const { default: ConfigurationPage } = await import('../page')
        render(<ConfigurationPage />)
        await flushAsync()

        // Confirm initial disconnected state
        await screen.findByRole(
            'button',
            { name: /connect google workspace/i },
            { timeout: 2500 },
        )

        // Dispatch the OAuth callback postMessage as the popup would
        await act(async () => {
            window.dispatchEvent(
                new MessageEvent('message', {
                    data: {
                        type: 'oauth-callback',
                        provider: 'google_workspace',
                        success: true,
                    },
                }),
            )
        })

        await waitFor(
            () => {
                expect(screen.getByText(/user@example.com/i)).toBeInTheDocument()
            },
            { timeout: 2500 },
        )
    })

    it('shows Disconnect button when connected (and no Connect button)', async () => {
        installFetchMock({
            googleWorkspaceStatus: {
                connected: true,
                email: 'user@example.com',
                features: ['Docs'],
                message: '',
            },
        })

        const { default: ConfigurationPage } = await import('../page')
        render(<ConfigurationPage />)
        await flushAsync()

        await waitFor(
            () => {
                expect(screen.getByText(/user@example.com/i)).toBeInTheDocument()
            },
            { timeout: 2500 },
        )

        expect(
            screen.getByRole('button', { name: /disconnect/i }),
        ).toBeInTheDocument()
        expect(
            screen.queryByRole('button', { name: /connect google workspace/i }),
        ).not.toBeInTheDocument()
    })

    it('clicking Disconnect calls DELETE /api/configuration/google-workspace and flips UI back', async () => {
        const { fetchSpy } = installFetchMock({
            googleWorkspaceStatus: {
                connected: true,
                email: 'user@example.com',
                features: ['Docs'],
                message: '',
            },
            googleWorkspaceStatusAfter: {
                connected: false,
                features: [],
                message: '',
            },
            disconnectStatus: 200,
        })

        const { default: ConfigurationPage } = await import('../page')
        render(<ConfigurationPage />)
        await flushAsync()

        const disconnectBtn = await screen.findByRole(
            'button',
            { name: /disconnect/i },
            { timeout: 2500 },
        )
        fireEvent.click(disconnectBtn)

        await waitFor(
            () => {
                const deleteCall = fetchSpy.mock.calls.find((call) => {
                    const u = typeof call[0] === 'string' ? call[0] : String(call[0])
                    const init = call[1] as RequestInit | undefined
                    return (
                        u.includes('/api/configuration/google-workspace') &&
                        !u.includes('google-workspace-status') &&
                        init?.method === 'DELETE'
                    )
                })
                expect(deleteCall).toBeDefined()
            },
            { timeout: 2500 },
        )

        // It must NOT call the generic /api/integrations/google_workspace path
        const wrongCall = fetchSpy.mock.calls.find((call) => {
            const u = typeof call[0] === 'string' ? call[0] : String(call[0])
            const init = call[1] as RequestInit | undefined
            return (
                u.includes('/api/integrations/google_workspace') &&
                init?.method === 'DELETE'
            )
        })
        expect(wrongCall).toBeUndefined()

        // UI flips back to disconnected branch
        await waitFor(
            () => {
                expect(
                    screen.getByRole('button', { name: /connect google workspace/i }),
                ).toBeInTheDocument()
            },
            { timeout: 2500 },
        )
    })
})
