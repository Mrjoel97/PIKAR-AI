// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
/**
 * Unit tests for InitiativeDashboard widget
 */

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import React from 'react'
import InitiativeDashboard from './InitiativeDashboard'
import { WidgetDefinition } from '@/types/widgets'

describe('InitiativeDashboard', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    const createDefinition = (data: Record<string, unknown>): WidgetDefinition => ({
        type: 'initiative_dashboard',
        title: 'Test Initiatives',
        data
    })

    describe('rendering', () => {
        it('renders metrics summary cards', () => {
            const definition = createDefinition({
                initiatives: [],
                metrics: { total: 5, completed: 3, in_progress: 1, blocked: 1 }
            })

            render(<InitiativeDashboard definition={definition} />)

            expect(screen.getByText('5')).toBeTruthy() // Total
            expect(screen.getByText('3')).toBeTruthy() // Completed
            expect(screen.getAllByText('1')).toHaveLength(2) // In Progress + Blocked
        })

        it('renders empty state when no initiatives', () => {
            const definition = createDefinition({
                initiatives: [],
                metrics: { total: 0, completed: 0, in_progress: 0, blocked: 0 }
            })

            render(<InitiativeDashboard definition={definition} />)

            expect(screen.getByText(/no initiatives found/i)).toBeTruthy()
        })

        it('renders initiative list with names', () => {
            const definition = createDefinition({
                initiatives: [
                    { id: '1', name: 'Product Launch', status: 'in_progress', progress: 65 },
                    { id: '2', name: 'Marketing Campaign', status: 'completed', progress: 100 }
                ],
                metrics: { total: 2, completed: 1, in_progress: 1, blocked: 0 }
            })

            render(<InitiativeDashboard definition={definition} />)

            expect(screen.getByText('Product Launch')).toBeTruthy()
            expect(screen.getByText('Marketing Campaign')).toBeTruthy()
        })

        it('displays status badges correctly', () => {
            const definition = createDefinition({
                initiatives: [
                    { id: '1', name: 'Blocked Task', status: 'blocked', progress: 30 }
                ],
                metrics: { total: 1, completed: 0, in_progress: 0, blocked: 1 }
            })

            render(<InitiativeDashboard definition={definition} />)

            expect(screen.getAllByText('Blocked').length).toBeGreaterThanOrEqual(1)
        })

        it('shows progress percentages', () => {
            const definition = createDefinition({
                initiatives: [
                    { id: '1', name: 'Test', status: 'in_progress', progress: 75 }
                ],
                metrics: { total: 1, completed: 0, in_progress: 1, blocked: 0 }
            })

            render(<InitiativeDashboard definition={definition} />)

            expect(screen.getByText('75% complete')).toBeTruthy()
        })
        it('renders trust and operational metadata when present', () => {
            const definition = createDefinition({
                initiatives: [
                    {
                        id: '1',
                        name: 'Launch Ops',
                        status: 'in_progress',
                        progress: 60,
                        goal: 'Ship the launch workflow',
                        currentPhase: 'validation',
                        verificationStatus: 'pending',
                        trustSummary: { approval_state: 'pending' },
                        blockers: [{ message: 'Awaiting approval' }],
                        evidence: [{ type: 'url', value: 'https://example.com' }],
                        nextActions: ['Get final sign-off'],
                    }
                ],
                metrics: { total: 1, completed: 0, in_progress: 1, blocked: 0 }
            })

            render(<InitiativeDashboard definition={definition} />)

            expect(screen.getByText(/phase: validation/i)).toBeTruthy()
            expect(screen.getByText(/verification: pending/i)).toBeTruthy()
            expect(screen.getByText(/approval: pending/i)).toBeTruthy()
            expect(screen.getByText('Ship the launch workflow')).toBeTruthy()
            expect(screen.getByText(/blockers: 1/i)).toBeTruthy()
            expect(screen.getByText(/evidence: 1/i)).toBeTruthy()
            expect(screen.getByText(/next actions: 1/i)).toBeTruthy()
        })
    })

    describe('interactions', () => {
        it('calls onAction with view_initiative when clicking an initiative', () => {
            const onAction = vi.fn()
            const definition = createDefinition({
                initiatives: [
                    { id: 'init-1', name: 'Click Me', status: 'in_progress', progress: 50 }
                ],
                metrics: { total: 1, completed: 0, in_progress: 1, blocked: 0 }
            })

            render(<InitiativeDashboard definition={definition} onAction={onAction} />)

            fireEvent.click(screen.getByText('Click Me'))

            expect(onAction).toHaveBeenCalledWith('view_initiative', { id: 'init-1', name: 'Click Me' })
        })

        it('calls onAction with mark_complete when clicking Mark Complete button', () => {
            const onAction = vi.fn()
            const definition = createDefinition({
                initiatives: [
                    { id: 'init-2', name: 'Incomplete', status: 'in_progress', progress: 80 }
                ],
                metrics: { total: 1, completed: 0, in_progress: 1, blocked: 0 }
            })

            render(<InitiativeDashboard definition={definition} onAction={onAction} />)

            fireEvent.click(screen.getByText('Mark Complete'))

            expect(onAction).toHaveBeenCalledWith('mark_complete', { id: 'init-2' })
        })
    })

    describe('default values', () => {
        it('handles missing data gracefully', () => {
            const definition = createDefinition({})

            render(<InitiativeDashboard definition={definition} />)

            // Should render without crashing and show empty state
            expect(screen.getByText(/no initiatives found/i)).toBeTruthy()
        })

        it('computes metrics from initiatives if not provided', () => {
            const definition = createDefinition({
                initiatives: [
                    { id: '1', name: 'A', status: 'completed', progress: 100 },
                    { id: '2', name: 'B', status: 'in_progress', progress: 50 }
                ]
            })

            render(<InitiativeDashboard definition={definition} />)

            // Should compute total=2
            expect(screen.getByText('2')).toBeTruthy()
        })
    })
})





