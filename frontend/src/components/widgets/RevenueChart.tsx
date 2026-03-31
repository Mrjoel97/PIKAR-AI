'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Revenue Chart Widget
 * 
 * Displays revenue metrics with visual indicators and period selection.
 * Used when agent responds to revenue-related queries.
 */

import React, { useState } from 'react';
import { WidgetProps } from './WidgetRegistry';
import { WidgetDefinition, RevenueData } from '@/types/widgets';
import { TrendingUp, TrendingDown, DollarSign, Calendar } from 'lucide-react';
import PersonaEmptyState from './PersonaEmptyState';

// =============================================================================
// Data Types
// =============================================================================


type PeriodType = 'daily' | 'weekly' | 'monthly';

// =============================================================================
// Helper Components
// =============================================================================

function SimpleBarChart({ values, periods }: { values: number[]; periods: string[] }) {
    const maxValue = Math.max(...values, 1);

    return (
        <div className="flex items-end gap-2 h-32">
            {values.map((value, index) => (
                <div key={index} className="flex-1 flex flex-col items-center gap-1">
                    <div
                        className="w-full bg-indigo-500 rounded-t transition-all duration-500 min-h-[4px]"
                        style={{ height: `${(value / maxValue) * 100}%` }}
                    />
                    <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate max-w-full">
                        {periods[index]}
                    </span>
                </div>
            ))}
        </div>
    );
}

function TrendIndicator({ change, changePercent }: { change: number; changePercent: number }) {
    const isPositive = change >= 0;
    const Icon = isPositive ? TrendingUp : TrendingDown;
    const colorClass = isPositive
        ? 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30'
        : 'text-red-600 bg-red-100 dark:bg-red-900/30';

    return (
        <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${colorClass}`}>
            <Icon className="w-4 h-4" />
            <span>{isPositive ? '+' : ''}{changePercent.toFixed(1)}%</span>
        </div>
    );
}

// =============================================================================
// Main Component
// =============================================================================

export default function RevenueChart({ definition, onAction }: WidgetProps) {
    const data = definition.data as unknown as RevenueData;
    const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('monthly');

    if (!data || (!data.values?.length && !data.currentPeriod)) {
        return <PersonaEmptyState widgetType="revenue_chart" />;
    }

    // Provide defaults if data is incomplete
    const currency = data?.currency ?? 'USD';
    const periods = data?.periods ?? ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    const values = data?.values ?? [45000, 52000, 48000, 61000, 55000, 67000];
    const currentPeriod = data?.currentPeriod ?? {
        revenue: values[values.length - 1] ?? 0,
        change: values.length >= 2 ? values[values.length - 1] - values[values.length - 2] : 0,
        changePercent: values.length >= 2
            ? ((values[values.length - 1] - values[values.length - 2]) / values[values.length - 2]) * 100
            : 0,
    };

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    };

    const handlePeriodChange = (period: PeriodType) => {
        setSelectedPeriod(period);
        onAction?.('change_period', { period });
    };

    return (
        <div className="space-y-4">
            {/* Current Revenue Summary */}
            <div className="flex items-start justify-between">
                <div>
                    <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm mb-1">
                        <DollarSign className="w-4 h-4" />
                        <span>Current Period Revenue</span>
                    </div>
                    <p className="text-3xl font-bold text-slate-800 dark:text-slate-100">
                        {formatCurrency(currentPeriod.revenue)}
                    </p>
                </div>
                <TrendIndicator change={currentPeriod.change} changePercent={currentPeriod.changePercent} />
            </div>

            {/* Period Selector */}
            <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-400" />
                <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
                    {(['daily', 'weekly', 'monthly'] as PeriodType[]).map((period) => (
                        <button
                            key={period}
                            onClick={() => handlePeriodChange(period)}
                            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${selectedPeriod === period
                                ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                                : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                                }`}
                        >
                            {period.charAt(0).toUpperCase() + period.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Bar Chart */}
            <div className="pt-2">
                <SimpleBarChart values={values} periods={periods} />
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 gap-3 pt-2 border-t border-slate-200 dark:border-slate-700 sm:grid-cols-3">
                <div className="text-center">
                    <p className="text-lg font-semibold text-slate-800 dark:text-slate-200">
                        {formatCurrency(Math.min(...values))}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Min</p>
                </div>
                <div className="text-center">
                    <p className="text-lg font-semibold text-slate-800 dark:text-slate-200">
                        {formatCurrency(values.reduce((a, b) => a + b, 0) / values.length)}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Average</p>
                </div>
                <div className="text-center">
                    <p className="text-lg font-semibold text-slate-800 dark:text-slate-200">
                        {formatCurrency(Math.max(...values))}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Max</p>
                </div>
            </div>
        </div>
    );
}
