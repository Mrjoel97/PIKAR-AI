// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
/**
 * Unit tests for ProductLaunchWidget
 */

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import React from 'react'
import ProductLaunchWidget from './ProductLaunchWidget'
import { WidgetDefinition } from '@/types/widgets'

describe('ProductLaunchWidget', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    const createDefinition = (data: Record<string, unknown>): WidgetDefinition => ({
        type: 'product_launch',
        title: 'Test Launch',
        data
    })

    describe('rendering', () => {
        it('renders launch status indicator', () => {
            const definition = createDefinition({
                milestones: [],
                status: 'on_track'
            })

            render(<ProductLaunchWidget definition={definition} />)

            expect(screen.getByText('On Track')).toBeTruthy()
        })

        it('renders empty state when no milestones', () => {
            const definition = createDefinition({
                milestones: [],
                status: 'on_track'
            })

            render(<ProductLaunchWidget definition={definition} />)

            expect(screen.getByText('No milestones defined')).toBeTruthy()
        })

        it('renders milestone list with names and dates', () => {
            const definition = createDefinition({
                milestones: [
                    { name: 'Alpha Release', date: '2023-01-01', status: 'completed' },
                    { name: 'Beta Release', date: '2023-02-01', status: 'pending' }
                ]
            })

            render(<ProductLaunchWidget definition={definition} />)

            expect(screen.getByText('Alpha Release')).toBeTruthy()
            expect(screen.getByText('Beta Release')).toBeTruthy()
            // Check for formatted dates (Jan 1, 2023)
            expect(screen.getByText('Jan 1')).toBeTruthy()
            expect(screen.getByText('Feb 1')).toBeTruthy()
        })

        it('displays milestone status badges correctly', () => {
            const definition = createDefinition({
                milestones: [
                    { name: 'Task 1', date: '2023-01-01', status: 'completed' },
                    { name: 'Task 2', date: '2023-01-01', status: 'in_progress' },
                    { name: 'Task 3', date: '2023-01-01', status: 'delayed' }
                ]
            })

            render(<ProductLaunchWidget definition={definition} />)

            expect(screen.getByText('Completed')).toBeTruthy()
            expect(screen.getByText('In Progress')).toBeTruthy()
            expect(screen.getByText('Delayed')).toBeTruthy()
        })

        it('shows completion percentage', () => {
            const definition = createDefinition({
                milestones: [
                    { name: 'A', date: '2023-01-01', status: 'completed' },
                    { name: 'B', date: '2023-01-01', status: 'pending' },
                    { name: 'C', date: '2023-01-01', status: 'pending' },
                    { name: 'D', date: '2023-01-01', status: 'pending' }
                ]
            })

            render(<ProductLaunchWidget definition={definition} />)

            // 1/4 = 25%
            expect(screen.getByText('25%')).toBeTruthy()
            expect(screen.getByText('(1/4)')).toBeTruthy()
        })

        it('renders timeline connectors between milestones', () => {
            const definition = createDefinition({
                milestones: [
                    { name: 'A', date: '2023-01-01', status: 'completed' },
                    { name: 'B', date: '2023-01-02', status: 'pending' }
                ]
            })

            const { container } = render(<ProductLaunchWidget definition={definition} />)

            // Check for the timeline connector div
            // We can identify it by the class 'absolute left-6 top-10 bottom-0 w-0.5'
            const connectors = container.querySelectorAll('.absolute.left-6.top-10')
            expect(connectors.length).toBeGreaterThan(0)
        })
    })

    describe('status indicators', () => {
        it('shows on_track status with green indicator', () => {
            const definition = createDefinition({ status: 'on_track' })
            render(<ProductLaunchWidget definition={definition} />)

            const indicator = screen.getByText('On Track').parentElement
            expect(indicator?.className).toContain('text-emerald-600')
        })

        it('shows at_risk status with yellow indicator', () => {
            const definition = createDefinition({ status: 'at_risk' })
            render(<ProductLaunchWidget definition={definition} />)

            const indicator = screen.getByText('At Risk').parentElement
            expect(indicator?.className).toContain('text-amber-600')
        })

        it('shows delayed status with red indicator', () => {
            const definition = createDefinition({ status: 'delayed' })
            render(<ProductLaunchWidget definition={definition} />)

            const indicator = screen.getByText('Delayed').parentElement
            expect(indicator?.className).toContain('text-red-600')
        })
    })

    describe('interactions', () => {
        it('calls onAction with view_milestone when clicking a milestone', () => {
            const onAction = vi.fn()
            const milestone = { name: 'Launch', date: '2023-01-01', status: 'pending' }
            const definition = createDefinition({
                milestones: [milestone]
            })

            render(<ProductLaunchWidget definition={definition} onAction={onAction} />)

            fireEvent.click(screen.getByText('Launch'))

            expect(onAction).toHaveBeenCalledWith('view_milestone', { milestone })
        })

        it('does not crash when onAction is undefined', () => {
            const definition = createDefinition({
                milestones: [{ name: 'Test', date: '2023-01-01', status: 'pending' }]
            })

            render(<ProductLaunchWidget definition={definition} />)

            fireEvent.click(screen.getByText('Test'))
            // Should not throw
        })
    })

    describe('default values', () => {
        it('handles missing data gracefully', () => {
            const definition = createDefinition({})

            render(<ProductLaunchWidget definition={definition} />)

            expect(screen.getByText('No milestones defined')).toBeTruthy()
        })

        it('defaults to on_track status when not provided', () => {
            const definition = createDefinition({ milestones: [] })
            render(<ProductLaunchWidget definition={definition} />)
            expect(screen.getByText('On Track')).toBeTruthy()
        })

        it('handles milestones without optional fields', () => {
            // TypeScript interface forbids missing required fields, but runtime checks are good
            const definition = createDefinition({
                milestones: [
                    { name: 'Minimal', date: '2023-01-01', status: 'pending' }
                ]
            })

            render(<ProductLaunchWidget definition={definition} />)
            expect(screen.getByText('Minimal')).toBeTruthy()
        })
    })

    describe('date formatting', () => {
        it('formats dates correctly', () => {
            const definition = createDefinition({
                milestones: [
                    { name: 'A', date: '2023-12-25', status: 'pending' }
                ]
            })

            render(<ProductLaunchWidget definition={definition} />)
            expect(screen.getByText('Dec 25')).toBeTruthy()
            expect(screen.getByText('2023')).toBeTruthy()
        })

        it('handles invalid dates gracefully', () => {
            const definition = createDefinition({
                milestones: [
                    { name: 'A', date: 'Invalid Date', status: 'pending' }
                ]
            })

            render(<ProductLaunchWidget definition={definition} />)
            expect(screen.getByText('Invalid Date')).toBeTruthy()
        })
    })
})
