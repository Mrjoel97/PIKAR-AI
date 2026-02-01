// @vitest-environment jsdom
/**
 * Unit tests for WidgetRegistry
 * 
 * Tests widget resolution, lazy loading, and container functionality.
 */

import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react'
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest'
import React, { Suspense } from 'react'

// Mock the lazy-loaded widget components
vi.mock('./InitiativeDashboard', () => ({
    default: ({ definition }: { definition: { title?: string } }) => (
        <div data-testid="initiative-dashboard">Initiative Dashboard: {definition.title}</div>
    )
}))

vi.mock('./RevenueChart', () => ({
    default: ({ definition }: { definition: { title?: string } }) => (
        <div data-testid="revenue-chart">Revenue Chart: {definition.title}</div>
    )
}))

vi.mock('./WorkflowBuilderWidget', () => ({
    default: ({ definition }: { definition: { title?: string } }) => (
        <div data-testid="workflow-builder">Workflow Builder: {definition.title}</div>
    )
}))

import {
    resolveWidget,
    isWidgetTypeSupported,
    getRegisteredWidgetTypes,
    WidgetContainer,
    Widget
} from './WidgetRegistry'
import { WidgetDefinition } from '@/hooks/useAgentChat'

describe('WidgetRegistry', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    describe('resolveWidget', () => {
        it('returns InitiativeDashboard for "initiative_dashboard" type', () => {
            const Component = resolveWidget('initiative_dashboard')
            expect(Component).toBeDefined()
        })

        it('returns RevenueChart for "revenue_chart" type', () => {
            const Component = resolveWidget('revenue_chart')
            expect(Component).toBeDefined()
        })

        it('returns WorkflowBuilderWidget for "workflow_builder" type', () => {
            const Component = resolveWidget('workflow_builder')
            expect(Component).toBeDefined()
        })

        it('returns UnknownWidget for unregistered type', () => {
            const Component = resolveWidget('nonexistent_widget')
            expect(Component).toBeDefined()
        })
    })

    describe('isWidgetTypeSupported', () => {
        it('returns true for registered widget types', () => {
            expect(isWidgetTypeSupported('initiative_dashboard')).toBe(true)
            expect(isWidgetTypeSupported('revenue_chart')).toBe(true)
            expect(isWidgetTypeSupported('workflow_builder')).toBe(true)
        })

        it('returns false for unregistered widget types', () => {
            expect(isWidgetTypeSupported('nonexistent')).toBe(false)
            expect(isWidgetTypeSupported('')).toBe(false)
        })
    })

    describe('getRegisteredWidgetTypes', () => {
        it('returns array of all registered widget types', () => {
            const types = getRegisteredWidgetTypes()
            expect(types).toContain('initiative_dashboard')
            expect(types).toContain('revenue_chart')
            expect(types).toContain('workflow_builder')
            expect(types.length).toBeGreaterThanOrEqual(3)
        })
    })

    describe('WidgetContainer', () => {
        const mockDefinition: WidgetDefinition = {
            type: 'initiative_dashboard',
            title: 'Test Dashboard',
            data: { initiatives: [], metrics: { total: 0, completed: 0, in_progress: 0, blocked: 0 } },
            dismissible: true,
            expandable: true
        }

        it('renders widget title in header', async () => {
            render(
                <Suspense fallback={<div>Loading...</div>}>
                    <WidgetContainer definition={mockDefinition} />
                </Suspense>
            )

            await waitFor(() => {
                expect(screen.getByText('Test Dashboard')).toBeTruthy()
            })
        })

        it('calls onToggleMinimized when collapse button clicked', async () => {
            const onToggleMinimized = vi.fn()

            render(
                <Suspense fallback={<div>Loading...</div>}>
                    <WidgetContainer
                        definition={mockDefinition}
                        onToggleMinimized={onToggleMinimized}
                    />
                </Suspense>
            )

            await waitFor(() => {
                const collapseButton = screen.getByRole('button', { name: /collapse/i })
                fireEvent.click(collapseButton)
                expect(onToggleMinimized).toHaveBeenCalled()
            })
        })

        it('calls onDismiss when dismiss button clicked', async () => {
            const onDismiss = vi.fn()

            render(
                <Suspense fallback={<div>Loading...</div>}>
                    <WidgetContainer
                        definition={mockDefinition}
                        onDismiss={onDismiss}
                    />
                </Suspense>
            )

            await waitFor(() => {
                const dismissButton = screen.getByRole('button', { name: /dismiss/i })
                fireEvent.click(dismissButton)
                expect(onDismiss).toHaveBeenCalled()
            })
        })

        it('shows collapsed state text when minimized', async () => {
            render(
                <Suspense fallback={<div>Loading...</div>}>
                    <WidgetContainer
                        definition={mockDefinition}
                        isMinimized={true}
                    />
                </Suspense>
            )

            await waitFor(() => {
                expect(screen.getByText(/widget collapsed/i)).toBeTruthy()
            })
        })

        it('shows expand button when widget is expandable', async () => {
            const onExpand = vi.fn()

            render(
                <Suspense fallback={<div>Loading...</div>}>
                    <WidgetContainer
                        definition={mockDefinition}
                        onExpand={onExpand}
                    />
                </Suspense>
            )

            await waitFor(() => {
                const expandButton = screen.getByRole('button', { name: /expand to full screen/i })
                expect(expandButton).toBeTruthy()
            })
        })
    })

    describe('Widget (simple)', () => {
        it('renders the correct widget component based on type', async () => {
            const definition: WidgetDefinition = {
                type: 'initiative_dashboard',
                title: 'My Dashboard',
                data: {}
            }

            render(
                <Suspense fallback={<div>Loading...</div>}>
                    <Widget definition={definition} />
                </Suspense>
            )

            await waitFor(() => {
                expect(screen.getByTestId('initiative-dashboard')).toBeTruthy()
            })
        })
    })
})
