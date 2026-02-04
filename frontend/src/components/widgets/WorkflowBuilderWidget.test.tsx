// @vitest-environment jsdom
/**
 * Unit tests for WorkflowBuilderWidget
 */

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import React from 'react'
import WorkflowBuilderWidget from './WorkflowBuilderWidget'
import { WidgetDefinition } from '@/types/widgets'

describe('WorkflowBuilderWidget', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    const createDefinition = (data: Record<string, unknown>, title = 'Test Workflow'): WidgetDefinition => ({
        type: 'workflow_builder',
        title,
        data
    })

    describe('rendering', () => {
        it('displays workflow title', () => {
            const definition = createDefinition({}, 'My Custom Workflow')

            render(<WorkflowBuilderWidget definition={definition} />)

            expect(screen.getByText('Workflow: My Custom Workflow')).toBeTruthy()
        })

        it('renders node labels', () => {
            const definition = createDefinition({
                nodes: [
                    { id: '1', position: { x: 0, y: 0 }, data: { label: 'Start Node' } },
                    { id: '2', position: { x: 0, y: 100 }, data: { label: 'Process Node' } },
                    { id: '3', position: { x: 0, y: 200 }, data: { label: 'End Node' } }
                ]
            })

            render(<WorkflowBuilderWidget definition={definition} />)

            expect(screen.getByText('Start Node')).toBeTruthy()
            expect(screen.getByText('Process Node')).toBeTruthy()
            expect(screen.getByText('End Node')).toBeTruthy()
        })

        it('shows empty state when no nodes', () => {
            const definition = createDefinition({ nodes: [], edges: [] })

            render(<WorkflowBuilderWidget definition={definition} />)

            expect(screen.getByText(/empty workflow/i)).toBeTruthy()
        })

        it('renders action buttons', () => {
            const definition = createDefinition({})

            render(<WorkflowBuilderWidget definition={definition} />)

            expect(screen.getByText('Open Full Editor')).toBeTruthy()
            expect(screen.getByText('Save Workflow')).toBeTruthy()
        })
    })

    describe('interactions', () => {
        it('calls onAction with save_workflow when clicking Save', () => {
            const onAction = vi.fn()
            const nodes = [{ id: '1', position: { x: 0, y: 0 }, data: { label: 'Test' } }]
            const edges = [{ id: 'e1', source: '1', target: '2' }]
            const definition = createDefinition({ nodes, edges })

            render(<WorkflowBuilderWidget definition={definition} onAction={onAction} />)

            fireEvent.click(screen.getByText('Save Workflow'))

            expect(onAction).toHaveBeenCalledWith('save_workflow', { nodes, edges })
        })

        it('calls onAction with expand_workflow when clicking Open Full Editor', () => {
            const onAction = vi.fn()
            const nodes = [{ id: '1', position: { x: 0, y: 0 }, data: { label: 'Test' } }]
            const definition = createDefinition({ nodes, edges: [] })

            render(<WorkflowBuilderWidget definition={definition} onAction={onAction} />)

            fireEvent.click(screen.getByText('Open Full Editor'))

            expect(onAction).toHaveBeenCalledWith('expand_workflow', { nodes, edges: [] })
        })
    })

    describe('default values', () => {
        it('handles undefined nodes and edges gracefully', () => {
            const definition = createDefinition({})

            render(<WorkflowBuilderWidget definition={definition} />)

            // Should render empty state without crashing
            expect(screen.getByText(/empty workflow/i)).toBeTruthy()
        })

        it('passes empty arrays when saving with no data', () => {
            const onAction = vi.fn()
            const definition = createDefinition({})

            render(<WorkflowBuilderWidget definition={definition} onAction={onAction} />)

            fireEvent.click(screen.getByText('Save Workflow'))

            expect(onAction).toHaveBeenCalledWith('save_workflow', { nodes: [], edges: [] })
        })
    })
})
