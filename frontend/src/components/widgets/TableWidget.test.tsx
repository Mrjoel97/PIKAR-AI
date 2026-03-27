// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
/**
 * Unit tests for TableWidget
 */

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import React from 'react'
import TableWidget from './TableWidget'
import { WidgetDefinition } from '@/types/widgets'

describe('TableWidget', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    const createDefinition = (data: Record<string, unknown>, title = 'Test Table'): WidgetDefinition => ({
        type: 'table',
        title,
        data
    })

    // Mock data matching the spec
    // columns: Array<{ key, label, sortable }>
    // data: Array<Object>
    // actions: Array<{ name, label, icon }>
    const mockColumns = [
        { key: 'name', label: 'Name' },
        { key: 'status', label: 'Status' },
        { key: 'amount', label: 'Amount' }
    ]

    const mockRows = [
        { id: '1', name: 'Deal A', status: 'Open', amount: '$5000' },
        { id: '2', name: 'Deal B', status: 'Closed', amount: '$12000' }
    ]

    const mockActions = [
        { name: 'view', label: 'View Details' },
        { name: 'delete', label: 'Delete' }
    ]

    describe('rendering', () => {
        it('renders table title', () => {
            const definition = createDefinition({ columns: [], rows: [] }, 'Sales Pipeline')
            render(<TableWidget definition={definition} />)
            expect(screen.getByText('Sales Pipeline')).toBeTruthy()
        })

        it('renders column headers', () => {
            const definition = createDefinition({ columns: mockColumns, rows: [] })
            render(<TableWidget definition={definition} />)

            expect(screen.getByText('Name')).toBeTruthy()
            expect(screen.getByText('Status')).toBeTruthy()
            expect(screen.getByText('Amount')).toBeTruthy()
        })

        it('renders row data', () => {
            const definition = createDefinition({ columns: mockColumns, rows: mockRows })
            render(<TableWidget definition={definition} />)

            expect(screen.getByText('Deal A')).toBeTruthy()
            expect(screen.getByText('$12000')).toBeTruthy()
            expect(screen.getByText('Closed')).toBeTruthy()
        })

        it('renders empty state when no rows', () => {
            const definition = createDefinition({ columns: mockColumns, rows: [] })
            render(<TableWidget definition={definition} />)

            expect(screen.getByText(/no records found/i)).toBeTruthy()
        })

        it('renders action buttons for each row', () => {
            const definition = createDefinition({ columns: mockColumns, rows: mockRows, actions: mockActions })
            render(<TableWidget definition={definition} />)

            // Should find action buttons
            expect(screen.getAllByText('View Details').length).toBe(2)
            expect(screen.getAllByText('Delete').length).toBe(2)
        })
    })

    describe('interactions', () => {
        it('calls onAction when clicking row action', () => {
            const onAction = vi.fn()
            const definition = createDefinition({ columns: mockColumns, rows: mockRows, actions: mockActions })
            render(<TableWidget definition={definition} onAction={onAction} />)

            // Click 'View Details' on first row
            const viewButtons = screen.getAllByText('View Details')
            fireEvent.click(viewButtons[0])

            expect(onAction).toHaveBeenCalledWith('table_action', {
                action: 'view',
                rowId: '1',
                row: mockRows[0]
            })
        })

        it('calls onAction when clicking a different action', () => {
            const onAction = vi.fn()
            const definition = createDefinition({ columns: mockColumns, rows: mockRows, actions: mockActions })
            render(<TableWidget definition={definition} onAction={onAction} />)

            // Click 'Delete' on second row
            const deleteButtons = screen.getAllByText('Delete')
            fireEvent.click(deleteButtons[1])

            expect(onAction).toHaveBeenCalledWith('table_action', {
                action: 'delete',
                rowId: '2',
                row: mockRows[1]
            })
        })
    })

    describe('default values', () => {
        it('handles missing actions gracefully', () => {
            const definition = createDefinition({ columns: mockColumns, rows: mockRows })
            render(<TableWidget definition={definition} />)

            // Should render rows but no action columns
            expect(screen.getByText('Deal A')).toBeTruthy()
            // We assume no extra buttons, strict check might depend on implementation
        })
    })
})
