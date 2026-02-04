// @vitest-environment jsdom
/**
 * Unit tests for FormWidget
 */

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import React from 'react'
import FormWidget from './FormWidget'
import { WidgetDefinition } from '@/types/widgets'

describe('FormWidget', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    const createDefinition = (data: Record<string, unknown>, title = 'Test Form'): WidgetDefinition => ({
        type: 'form',
        title,
        data
    })

    const mockFields = [
        { name: 'fullName', label: 'Full Name', type: 'text', required: true },
        { name: 'email', label: 'Email Address', type: 'email', required: true },
        {
            name: 'department',
            label: 'Department',
            type: 'select',
            options: ['Sales', 'Engineering', 'HR']
        },
        { name: 'notes', label: 'Additional Notes', type: 'textarea' }
    ]

    describe('rendering', () => {
        it('renders form title', () => {
            const definition = createDefinition({ fields: [] }, 'Employee Survey')
            render(<FormWidget definition={definition} />)
            expect(screen.getByText('Employee Survey')).toBeTruthy()
        })

        it('renders all field labels', () => {
            const definition = createDefinition({ fields: mockFields })
            render(<FormWidget definition={definition} />)

            expect(screen.getByText('Full Name')).toBeTruthy()
            expect(screen.getByText('Email Address')).toBeTruthy()
            expect(screen.getByText('Department')).toBeTruthy()
            expect(screen.getByText('Additional Notes')).toBeTruthy()
        })

        it('renders correct input types', () => {
            const definition = createDefinition({ fields: mockFields })
            render(<FormWidget definition={definition} />)

            // Text input
            const nameInput = screen.getByLabelText(/Full Name/i)
            expect(nameInput.getAttribute('type')).toBe('text')

            // Email input
            const emailInput = screen.getByLabelText(/Email Address/i)
            expect(emailInput.getAttribute('type')).toBe('email')

            // Select input (combobox using native select for simplicity in basic widget)
            const deptSelect = screen.getByLabelText(/Department/i)
            expect(deptSelect.tagName).toBe('SELECT')

            // Textarea
            const notesInput = screen.getByLabelText(/Additional Notes/i)
            expect(notesInput.tagName).toBe('TEXTAREA')
        })

        it('renders submit button with default label', () => {
            const definition = createDefinition({ fields: [] })
            render(<FormWidget definition={definition} />)
            expect(screen.getByRole('button', { name: /submit/i })).toBeTruthy()
        })

        it('renders submit button with custom label', () => {
            const definition = createDefinition({ fields: [], submitLabel: 'Send Request' })
            render(<FormWidget definition={definition} />)
            expect(screen.getByRole('button', { name: 'Send Request' })).toBeTruthy()
        })
    })

    describe('interactions', () => {
        it('updates field values when typing', () => {
            const definition = createDefinition({ fields: mockFields })
            render(<FormWidget definition={definition} />)

            const nameInput = screen.getByLabelText(/Full Name/i)
            fireEvent.change(nameInput, { target: { value: 'John Doe' } })

            expect((nameInput as HTMLInputElement).value).toBe('John Doe')
        })

        it('validates required fields on submit', () => {
            const onAction = vi.fn()
            const definition = createDefinition({ fields: mockFields })
            render(<FormWidget definition={definition} onAction={onAction} />)

            // Click submit without filling required fields
            fireEvent.click(screen.getByRole('button', { name: /submit/i }))

            // Should show validation error (HTML5 validation or custom)
            // For this test, we check that onAction was NOT called
            expect(onAction).not.toHaveBeenCalled()
        })

        it('calls onAction with form data on valid submit', () => {
            const onAction = vi.fn()
            const definition = createDefinition({ fields: mockFields })
            render(<FormWidget definition={definition} onAction={onAction} />)

            // Fill fields
            fireEvent.change(screen.getByLabelText(/Full Name/i), { target: { value: 'Jane Smith' } })
            fireEvent.change(screen.getByLabelText(/Email Address/i), { target: { value: 'jane@example.com' } })
            fireEvent.change(screen.getByLabelText(/Department/i), { target: { value: 'Engineering' } })

            // Submit
            fireEvent.click(screen.getByRole('button', { name: /submit/i }))

            expect(onAction).toHaveBeenCalledWith('submit_form', {
                fullName: 'Jane Smith',
                email: 'jane@example.com',
                department: 'Engineering',
                notes: '' // Optional field empty
            })
        })
    })

    describe('default values', () => {
        it('initializes fields with default values if provided', () => {
            const fieldsWithDefaults = [
                { name: 'role', label: 'Role', type: 'text', defaultValue: 'Developer' }
            ]
            const definition = createDefinition({ fields: fieldsWithDefaults })
            render(<FormWidget definition={definition} />)

            const input = screen.getByLabelText(/Role/i)
            expect((input as HTMLInputElement).value).toBe('Developer')
        })
    })
})
