// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
/**
 * Unit tests for CalendarWidget
 */

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import React from 'react'
import CalendarWidget from './CalendarWidget'
import { WidgetDefinition } from '@/types/widgets'

describe('CalendarWidget', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    // Calendar Data Structure:
    // events: Array<{ id, title, start, end, color? }>
    // view: 'month' | 'week' | 'day' (default 'month')

    const createDefinition = (data: Record<string, unknown>, title = 'Schedule'): WidgetDefinition => ({
        type: 'calendar',
        title,
        data
    })

    const mockEvents = [
        { id: 'e1', title: 'Team Meeting', start: '2023-10-15T10:00:00', end: '2023-10-15T11:00:00', color: 'bg-blue-100' },
        { id: 'e2', title: 'Project Launch', start: '2023-10-20T09:00:00', end: '2023-10-20T17:00:00', color: 'bg-green-100' }
    ]

    describe('rendering', () => {
        it('renders calendar title', () => {
            const definition = createDefinition({ events: [] }, 'Content Calendar')
            render(<CalendarWidget definition={definition} />)
            expect(screen.getByText('Content Calendar')).toBeTruthy()
        })

        it('renders month view by default', () => {
            const definition = createDefinition({ events: [] })
            render(<CalendarWidget definition={definition} />)
            // Should see days of week
            expect(screen.getByText(/Mon/i)).toBeTruthy()
            expect(screen.getByText(/Sun/i)).toBeTruthy()
        })

        it('displays events on the calendar', () => {
            // For testing, we might need to mock the current date to ensure events show up
            // Or use a library that we can control.
            // Simplified approach: Render a list of upcoming events for now if full calendar logic is complex to test without sub-components
            // OR checks for presence of event titles
            const definition = createDefinition({ events: mockEvents })
            render(<CalendarWidget definition={definition} />)

            // Assuming list view or day view matches
            // If month view, we might need navigation.
            // Let's assume the widget calculates identifying current month from events or uses today.
            // For robust test, we would check if 'Team Meeting' is in the document.
            // We'll implement a simple list sidebar or agenda view for this test verification.
            expect(screen.getByText('Team Meeting')).toBeTruthy()
            expect(screen.getByText('Project Launch')).toBeTruthy()
        })
    })

    describe('interactions', () => {
        it('calls onAction when clicking an event', () => {
            const onAction = vi.fn()
            const definition = createDefinition({ events: mockEvents })
            render(<CalendarWidget definition={definition} onAction={onAction} />)

            const eventEl = screen.getByText('Team Meeting')
            fireEvent.click(eventEl)

            expect(onAction).toHaveBeenCalledWith('view_event', {
                eventId: 'e1',
                event: mockEvents[0]
            })
        })

        it('calls onAction when clicking adding event', () => {
            const onAction = vi.fn()
            const definition = createDefinition({ events: [] })
            render(<CalendarWidget definition={definition} onAction={onAction} />)

            const addBtn = screen.getByLabelText(/add event/i)
            fireEvent.click(addBtn)

            expect(onAction).toHaveBeenCalledWith('add_event', {})
        })
    })
})
