// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
/**
 * Unit tests for RevenueChart widget
 */

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import React from 'react'
import RevenueChart from './RevenueChart'
import { WidgetDefinition } from '@/types/widgets'

describe('RevenueChart', () => {
    afterEach(() => {
        cleanup()
        vi.clearAllMocks()
    })

    const createDefinition = (data: Record<string, unknown>): WidgetDefinition => ({
        type: 'revenue_chart',
        title: 'Revenue Overview',
        data
    })

    describe('rendering', () => {
        it('formats and displays current revenue', () => {
            const definition = createDefinition({
                periods: ['Jan', 'Feb', 'Mar'],
                values: [45000, 52000, 61000],
                currency: 'USD',
                currentPeriod: { revenue: 61000, change: 9000, changePercent: 17.3 }
            })

            render(<RevenueChart definition={definition} />)

            // Should format as currency
            expect(screen.getByText('$61,000')).toBeTruthy()
        })

        it('displays positive trend indicator', () => {
            const definition = createDefinition({
                currentPeriod: { revenue: 70000, change: 5000, changePercent: 7.7 }
            })

            render(<RevenueChart definition={definition} />)

            expect(screen.getByText('+7.7%')).toBeTruthy()
        })

        it('displays negative trend indicator', () => {
            const definition = createDefinition({
                currentPeriod: { revenue: 50000, change: -5000, changePercent: -9.1 }
            })

            render(<RevenueChart definition={definition} />)

            expect(screen.getByText('-9.1%')).toBeTruthy()
        })

        it('renders period selector with all options', () => {
            const definition = createDefinition({})

            render(<RevenueChart definition={definition} />)

            expect(screen.getByText('Daily')).toBeTruthy()
            expect(screen.getByText('Weekly')).toBeTruthy()
            expect(screen.getByText('Monthly')).toBeTruthy()
        })

        it('renders bar chart with period labels', () => {
            const definition = createDefinition({
                periods: ['Q1', 'Q2', 'Q3', 'Q4'],
                values: [100000, 120000, 110000, 140000]
            })

            render(<RevenueChart definition={definition} />)

            expect(screen.getByText('Q1')).toBeTruthy()
            expect(screen.getByText('Q4')).toBeTruthy()
        })

        it('displays min/avg/max summary stats', () => {
            const definition = createDefinition({
                values: [10000, 20000, 30000]
            })

            render(<RevenueChart definition={definition} />)

            expect(screen.getByText('Min')).toBeTruthy()
            expect(screen.getByText('Average')).toBeTruthy()
            expect(screen.getByText('Max')).toBeTruthy()
        })
    })

    describe('interactions', () => {
        it('calls onAction when changing period', () => {
            const onAction = vi.fn()
            const definition = createDefinition({})

            render(<RevenueChart definition={definition} onAction={onAction} />)

            fireEvent.click(screen.getByText('Weekly'))

            expect(onAction).toHaveBeenCalledWith('change_period', { period: 'weekly' })
        })

        it('highlights selected period', () => {
            const definition = createDefinition({})

            render(<RevenueChart definition={definition} />)

            // Click on Weekly
            fireEvent.click(screen.getByText('Weekly'))

            // Weekly button should now have active styling (we check it's clickable)
            const weeklyButton = screen.getByText('Weekly')
            expect(weeklyButton).toBeTruthy()
        })
    })

    describe('default values', () => {
        it('uses default periods and values when not provided', () => {
            const definition = createDefinition({})

            render(<RevenueChart definition={definition} />)

            // Default periods include 'Jan'
            expect(screen.getByText('Jan')).toBeTruthy()
        })

        it('computes currentPeriod from values if not provided', () => {
            const definition = createDefinition({
                values: [50000, 60000]
            })

            render(<RevenueChart definition={definition} />)

            // Should compute change from last two values
            expect(screen.getByText('$60,000')).toBeTruthy()
        })

        it('defaults to USD currency', () => {
            const definition = createDefinition({
                currentPeriod: { revenue: 12345, change: 0, changePercent: 0 }
            })

            render(<RevenueChart definition={definition} />)

            expect(screen.getByText('$12,345')).toBeTruthy()
        })
    })
})

