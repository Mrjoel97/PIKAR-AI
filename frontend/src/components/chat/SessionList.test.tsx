// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest'
import { SessionList } from './SessionList'
import * as useSessionHistoryModule from '@/hooks/useSessionHistory'

// Mock the hook
vi.mock('@/hooks/useSessionHistory', () => ({
    useSessionHistory: vi.fn()
}))

describe('SessionList', () => {
    const mockDeleteSession = vi.fn()
    const mockOnSelectSession = vi.fn()

    const mockSessions = [
        {
            app_name: 'pikar_ai',
            user_id: 'user123',
            session_id: 'session-1',
            state: { title: 'First Session' },
            created_at: '2025-01-01T10:00:00Z',
            updated_at: '2025-01-01T12:00:00Z'
        },
        {
            app_name: 'pikar_ai',
            user_id: 'user123',
            session_id: 'session-2',
            state: {}, // No title
            created_at: '2025-01-02T10:00:00Z',
            updated_at: '2025-01-02T11:00:00Z'
        }
    ]

    beforeEach(() => {
        vi.mocked(useSessionHistoryModule.useSessionHistory).mockReturnValue({
            sessions: mockSessions,
            isLoading: false,
            error: null,
            refresh: vi.fn(),
            deleteSession: mockDeleteSession
        })

        // Mock window.confirm
        window.confirm = vi.fn(() => true)
    })

    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    it('renders loading state', () => {
        vi.mocked(useSessionHistoryModule.useSessionHistory).mockReturnValue({
            sessions: [],
            isLoading: true,
            error: null,
            refresh: vi.fn(),
            deleteSession: mockDeleteSession
        })

        render(<SessionList onSelectSession={mockOnSelectSession} />)
        expect(screen.getByText('Loading history...')).toBeTruthy()
    })

    it('renders empty state', () => {
        vi.mocked(useSessionHistoryModule.useSessionHistory).mockReturnValue({
            sessions: [],
            isLoading: false,
            error: null,
            refresh: vi.fn(),
            deleteSession: mockDeleteSession
        })

        render(<SessionList onSelectSession={mockOnSelectSession} />)
        expect(screen.getByText('No past conversations')).toBeTruthy()
    })

    it('renders sessions list', () => {
        render(<SessionList onSelectSession={mockOnSelectSession} />)

        expect(screen.getByText('Recent Sessions')).toBeTruthy()
        expect(screen.getByText('First Session')).toBeTruthy()
        // Check fallback title
        expect(screen.getByText(/Session session-/)).toBeTruthy()
    })

    it('calls onSelectSession when clicking a session', () => {
        render(<SessionList onSelectSession={mockOnSelectSession} />)

        fireEvent.click(screen.getByText('First Session'))
        expect(mockOnSelectSession).toHaveBeenCalledWith('session-1')
    })

    it('highlights current session', () => {
        render(<SessionList onSelectSession={mockOnSelectSession} currentSessionId="session-1" />)

        const session1Title = screen.getByText('First Session')
        // Tailwind classes are hard to test directly without checking classList, but we can verify presence
        expect(session1Title.className).toContain('text-indigo-700')
    })

    it('deletes session on trash click', () => {
        render(<SessionList onSelectSession={mockOnSelectSession} />)

        const deleteButtons = screen.getAllByTitle('Delete session')
        fireEvent.click(deleteButtons[0])

        expect(window.confirm).toHaveBeenCalled()
        expect(mockDeleteSession).toHaveBeenCalledWith('session-1')
    })
})
