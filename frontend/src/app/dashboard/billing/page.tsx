'use client';

import { useState, useEffect, useMemo } from 'react';
import { usePersona } from '@/contexts/PersonaContext';
import { type PersonaType } from '@/services/onboarding';
import MetricCard from '@/components/ui/MetricCard';
import { getDashboardSummary, type DashboardSummary } from '@/services/dashboard';
import { CreditCard, Zap, FileText, Database, Check, Crown } from 'lucide-react';

const PLAN_CONFIG: Record<PersonaType, { name: string; price: string }> = {
    solopreneur: { name: 'Solopreneur', price: '$99/mo' },
    startup: { name: 'Startup', price: '$297/mo' },
    sme: { name: 'SME', price: '$597/mo' },
    enterprise: { name: 'Enterprise', price: 'Custom' },
};

interface FeatureRow {
    label: string;
    solopreneur: boolean;
    startup: boolean;
    sme: boolean;
    enterprise: boolean;
}

const FEATURE_ROWS: FeatureRow[] = [
    { label: 'AI Agents', solopreneur: true, startup: true, sme: true, enterprise: true },
    { label: 'Brain Dump & Action Plans', solopreneur: true, startup: true, sme: true, enterprise: true },
    { label: 'Invoice Generation', solopreneur: true, startup: true, sme: true, enterprise: true },
    { label: 'Social Publishing', solopreneur: true, startup: true, sme: true, enterprise: true },
    { label: 'Workflow Engine', solopreneur: false, startup: true, sme: true, enterprise: true },
    { label: 'Sales Pipeline & CRM', solopreneur: false, startup: true, sme: true, enterprise: true },
    { label: 'Compliance Suite', solopreneur: false, startup: false, sme: true, enterprise: true },
    { label: 'Financial Forecasting', solopreneur: false, startup: false, sme: true, enterprise: true },
    { label: 'Custom Workflows', solopreneur: false, startup: false, sme: false, enterprise: true },
    { label: 'SSO & Governance', solopreneur: false, startup: false, sme: false, enterprise: true },
];

const TIERS: PersonaType[] = ['solopreneur', 'startup', 'sme', 'enterprise'];

export default function BillingPage() {
    const { persona } = usePersona();
    const currentPersona = (persona ?? 'solopreneur') as PersonaType;
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getDashboardSummary()
            .then(setSummary)
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const plan = useMemo(() => PLAN_CONFIG[currentPersona], [currentPersona]);

    if (loading) {
        return (
            <div className="min-h-screen bg-white p-6">
                <div className="max-w-7xl mx-auto space-y-6">
                    <div className="h-8 w-64 bg-slate-200 rounded animate-pulse" />
                    <div className="h-48 bg-slate-200 rounded-2xl animate-pulse" />
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {Array.from({ length: 4 }).map((_, i) => (
                            <div key={i} className="h-24 bg-slate-200 rounded-2xl animate-pulse" />
                        ))}
                    </div>
                    <div className="h-96 bg-slate-200 rounded-2xl animate-pulse" />
                </div>
            </div>
        );
    }

    const signals = summary?.signals;

    return (
        <div className="min-h-screen bg-white p-6">
            <div className="max-w-7xl mx-auto space-y-8">
                {/* Header */}
                <h1 className="text-2xl font-bold text-slate-900">Billing & Subscription</h1>

                {/* Current Plan Card */}
                <div className="rounded-2xl bg-gradient-to-r from-teal-700 to-teal-900 text-white p-8">
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <Crown className="h-6 w-6" />
                                <h2 className="text-xl font-bold">{plan.name} Plan</h2>
                                <span className="bg-white/20 rounded-full px-3 py-1 text-xs">Current Plan</span>
                            </div>
                            <p className="text-3xl font-bold mt-4">{plan.price}</p>
                            <p className="text-teal-200 text-sm mt-2">Next billing: April 14, 2026</p>
                        </div>
                        <CreditCard className="h-10 w-10 text-teal-200" />
                    </div>
                </div>

                {/* Usage Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <MetricCard
                        label="Active Workflows"
                        value={signals?.active_workflows ?? 0}
                        icon={Zap}
                    />
                    <MetricCard
                        label="Open Tasks"
                        value={signals?.open_tasks ?? 0}
                        icon={FileText}
                    />
                    <MetricCard
                        label="Pending Approvals"
                        value={signals?.pending_approvals ?? 0}
                        icon={Check}
                    />
                    <MetricCard
                        label="Reports Generated"
                        value={signals?.recent_reports ?? 0}
                        icon={Database}
                    />
                </div>

                {/* Plan Comparison Table */}
                <div className="rounded-2xl border border-slate-200 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="bg-slate-50">
                                    <th className="text-left p-4 font-semibold text-slate-700 w-1/5">Feature</th>
                                    {TIERS.map((tier) => (
                                        <th
                                            key={tier}
                                            className={`p-4 text-center ${
                                                tier === currentPersona
                                                    ? 'ring-2 ring-teal-600 bg-teal-50'
                                                    : ''
                                            }`}
                                        >
                                            <div className="font-bold text-slate-900">
                                                {PLAN_CONFIG[tier].name}
                                            </div>
                                            <div className="text-slate-500 text-xs mt-1">
                                                {PLAN_CONFIG[tier].price}
                                            </div>
                                            {tier === currentPersona && (
                                                <span className="inline-block mt-1 bg-teal-600 text-white text-xs rounded-full px-2 py-0.5">
                                                    Current
                                                </span>
                                            )}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {FEATURE_ROWS.map((row, idx) => (
                                    <tr
                                        key={row.label}
                                        className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}
                                    >
                                        <td className="p-4 font-medium text-slate-700">
                                            {row.label === 'AI Agents' ? 'AI Agents (All 11)' : row.label}
                                        </td>
                                        {TIERS.map((tier) => (
                                            <td
                                                key={tier}
                                                className={`p-4 text-center ${
                                                    tier === currentPersona
                                                        ? 'ring-2 ring-teal-600 bg-teal-50/30'
                                                        : ''
                                                }`}
                                            >
                                                {row[tier] ? (
                                                    <Check className="h-5 w-5 text-teal-600 mx-auto" />
                                                ) : (
                                                    <span className="text-slate-300">&mdash;</span>
                                                )}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                                {/* Action Row */}
                                <tr className="bg-slate-50 border-t border-slate-200">
                                    <td className="p-4" />
                                    {TIERS.map((tier) => (
                                        <td
                                            key={tier}
                                            className={`p-4 text-center ${
                                                tier === currentPersona
                                                    ? 'ring-2 ring-teal-600'
                                                    : ''
                                            }`}
                                        >
                                            {tier === currentPersona ? (
                                                <span className="text-sm font-medium text-slate-500">
                                                    Current Plan
                                                </span>
                                            ) : tier === 'enterprise' ? (
                                                <button className="px-4 py-2 rounded-full bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800 transition-colors">
                                                    Talk to Sales
                                                </button>
                                            ) : (
                                                <button className="px-4 py-2 rounded-full bg-teal-600 text-white text-sm font-semibold hover:bg-teal-700 transition-colors">
                                                    Upgrade
                                                </button>
                                            )}
                                        </td>
                                    ))}
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
