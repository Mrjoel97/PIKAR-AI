// @vitest-environment jsdom
/**
 * Unit tests for KanbanWidget
 */

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import React from 'react'
import KanbanWidget from './KanbanWidget'
import { WidgetDefinition } from '@/types/widgets'

describe('KanbanWidget', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    // Kanban Data Structure:
    // columns: Array<{ id, title, color? }>
    // cards: Array<{ id, columnId, title, description?, tags? }>

    const createDefinition = (data: Record<string, unknown>, title = 'Project Board'): WidgetDefinition => ({
        type: 'kanban_board',
        title,
        data
    })

    const mockColumns = [
        { id: 'todo', title: 'To Do', color: 'bg-slate-100' },
        { id: 'in-progress', title: 'In Progress', color: 'bg-blue-100' },
        { id: 'done', title: 'Done', color: 'bg-green-100' }
    ]

    const mockCards = [
        { id: 'c1', columnId: 'todo', title: 'Task 1', description: 'Fix bug' },
        { id: 'c2', columnId: 'in-progress', title: 'Task 2', description: 'Develop feature', tags: ['High'] },
        { id: 'c3', columnId: 'done', title: 'Task 3', description: 'Deploy', tags: ['DevOps'] }
    ]

    describe('rendering', () => {
        it('renders board title', () => {
            const definition = createDefinition({ columns: [], cards: [] }, 'Sales Pipeline')
            render(<KanbanWidget definition={definition} />)
            expect(screen.getByText('Sales Pipeline')).toBeTruthy()
        })

        it('renders all columns', () => {
            const definition = createDefinition({ columns: mockColumns, cards: [] })
            render(<KanbanWidget definition={definition} />)

            expect(screen.getByText('To Do')).toBeTruthy()
            expect(screen.getByText('In Progress')).toBeTruthy()
            expect(screen.getByText('Done')).toBeTruthy()
        })

        it('renders cards in correct columns', () => {
            const definition = createDefinition({ columns: mockColumns, cards: mockCards })
            render(<KanbanWidget definition={definition} />)

            expect(screen.getByText('Task 1')).toBeTruthy() // In Todo
            expect(screen.getByText('Task 2')).toBeTruthy() // In In-Progress
            expect(screen.getByText('Task 3')).toBeTruthy() // In Done
        })

        it('displays card details', () => {
            const definition = createDefinition({ columns: mockColumns, cards: mockCards })
            render(<KanbanWidget definition={definition} />)

            expect(screen.getByText('Fix bug')).toBeTruthy()
            expect(screen.getByText('High')).toBeTruthy() // Tag
        })

        it('shows empty state message if no columns', () => {
            const definition = createDefinition({ columns: [], cards: [] })
            render(<KanbanWidget definition={definition} />)
            expect(screen.getByText(/no columns/i)).toBeTruthy()
        })
    })

    describe('interactions', () => {
        it('calls onAction when clicking a card', () => {
            const onAction = vi.fn()
            const definition = createDefinition({ columns: mockColumns, cards: mockCards })
            render(<KanbanWidget definition={definition} onAction={onAction} />)

            fireEvent.click(screen.getByText('Task 1'))

            expect(onAction).toHaveBeenCalledWith('view_card', {
                cardId: 'c1',
                card: mockCards[0]
            })
        })

        it('calls onAction when clicking add button in a column', () => {
            const onAction = vi.fn()
            const definition = createDefinition({ columns: mockColumns, cards: [] })
            render(<KanbanWidget definition={definition} onAction={onAction} />)

            // Assume each column has an "Add" button/icon
            // We act on the first one (To Do)
            const addButtons = screen.getAllByLabelText(/add card/i)
            fireEvent.click(addButtons[0])

            expect(onAction).toHaveBeenCalledWith('add_card', {
                columnId: 'todo'
            })
        })
    })

    describe('default values', () => {
        it('handles missing cards gracefully', () => {
            const definition = createDefinition({ columns: mockColumns })
            render(<KanbanWidget definition={definition} />)

            expect(screen.getByText('To Do')).toBeTruthy()
            // Should not crash
        })
    })
})
