'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import MetricCard from '@/components/ui/MetricCard';
import { getDashboardSummary, type DashboardSummary } from '@/services/dashboard';
import {
    CreditCard,
    Zap,
    FileText,
    Database,
    Check,
    Crown,
    ExternalLink,
    AlertTriangle,
    Loader2,
} from 'lucide-react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { useSubscription, type PikarTier } from '@/contexts/SubscriptionContext';

// ---------------------------------------------------------------------------
// Plan config — maps tiers to display names, prices, and Stripe Price IDs.
// Price IDs are loaded from env at build time; fallback to empty string.
// ---------------------------------------------------------------------------

type TierKey = Exclude<PikarTier, 'free'>;

interface PlanInfo {
    name: string;
    price: string;
    stripePriceId: string;
}

const PLAN_CONFIG: Record<TierKey, PlanInfo> = {
    solopreneur: {
        name: 'Solopreneur',
        price: '$99/mo',
        stripePriceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_SOLOPRENEUR ?? '',
    },
    startup: {
        name: 'Startup',
        price: '$297/mo',
        stripePriceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_STARTUP ?? '',
    },
    sme: {
        name: 'SME',
        price: '$597/mo',
        stripePriceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_SME ?? '',
    },
    enterprise: {
        name: 'Enterprise',
        price: 'Custom',
        stripePriceId: '',
    },
};

interface FeatureRow {
    label: string;
    solopreneur: boolean;
    startup: boolean;
    sme: boolean;
    enterprise: boolean;
}

const FEATURE_ROWS: FeatureRow[] = [
    { label: 'AI Agents (All 11)', solopreneur: true, startup: true, sme: true, enterprise: true },
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

const TIERS: TierKey[] = ['solopreneur', 'startup', 'sme', 'enterprise'];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function BillingPage() {
    const sub = useSubscription();
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [dashLoading, setDashLoading] = useState(true);

    useEffect(() => {
        getDashboardSummary()
            .then(setSummary)
            .catch(() => {})
            .finally(() => setDashLoading(false));
    }, []);

    // Refresh subscription state after returning from Stripe Checkout.
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get('checkout') === 'success') {
            sub.refresh();
            // Clean up the URL.
            window.history.replaceState({}, '', '/dashboard/billing');
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const loading = !sub.ready || dashLoading;
    const activeTier = sub.tier === 'free' ? null : sub.tier;
    const planDisplay = activeTier ? PLAN_CONFIG[activeTier] : null;

    // Format the renewal/expiry date.
    const periodEndLabel = (() => {
        if (!sub.periodEnd) return null;
        return sub.periodEnd.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    })();

    // ── Handlers ─────────────────────────────────────────────────────────
    const handleSubscribe = async (tierKey: TierKey) => {
        const plan = PLAN_CONFIG[tierKey];
        if (!plan.stripePriceId) return;
        await sub.checkout(plan.stripePriceId);
    };

    // ── Loading skeleton ─────────────────────────────────────────────────
    if (loading) {
        return (
            <DashboardErrorBoundary fallbackTitle="Billing Error">
                <PremiumShell>
                    <div className="max-w-7xl mx-auto space-y-6">
                        <div className="h-8 w-64 bg-slate-200 rounded-xl animate-pulse" />
                        <div className="h-48 bg-slate-200 rounded-[28px] animate-pulse" />
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {Array.from({ length: 4 }).map((_, i) => (
                                <div key={i} className="h-24 bg-slate-200 rounded-[28px] animate-pulse" />
                            ))}
                        </div>
                        <div className="h-96 bg-slate-200 rounded-[28px] animate-pulse" />
                    </div>
                </PremiumShell>
            </DashboardErrorBoundary>
        );
    }

    const signals = summary?.signals;

    return (
        <DashboardErrorBoundary fallbackTitle="Billing Error">
            <PremiumShell>
                <motion.div
                    className="max-w-7xl mx-auto space-y-8"
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                        Billing & Subscription
                    </h1>

                    {/* Error banner */}
                    {sub.error && (
                        <div className="rounded-2xl bg-red-50 border border-red-200 p-4 flex items-start gap-3 text-sm text-red-800">
                            <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                            <span>{sub.error}</span>
                        </div>
                    )}

                    {/* Billing issue warning */}
                    {sub.hasBillingIssue && (
                        <div className="rounded-2xl bg-amber-50 border border-amber-200 p-4 flex items-start gap-3 text-sm text-amber-800">
                            <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                            <div>
                                <p className="font-semibold">Payment issue detected</p>
                                <p className="mt-1">
                                    There&apos;s a problem with your payment method. Please update
                                    your billing details to avoid service interruption.
                                </p>
                                <button
                                    onClick={() => sub.openPortal()}
                                    className="mt-2 inline-flex items-center gap-1.5 text-amber-900 font-semibold underline underline-offset-2"
                                >
                                    Update payment method
                                    <ExternalLink className="h-3.5 w-3.5" />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Current Plan Card */}
                    <div className="rounded-[28px] bg-gradient-to-r from-teal-700 to-teal-900 text-white p-8 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.5)]">
                        <div className="flex items-start justify-between">
                            <div>
                                <div className="flex items-center gap-3 mb-2">
                                    <Crown className="h-6 w-6" />
                                    <h2 className="text-xl font-bold">
                                        {planDisplay ? `${planDisplay.name} Plan` : 'Free Plan'}
                                    </h2>
                                    <span className="bg-white/20 rounded-full px-3 py-1 text-[11px] tracking-[0.28em] uppercase font-semibold">
                                        {sub.subscription?.period_type === 'trial' ? 'Trial' : 'Current Plan'}
                                    </span>
                                </div>

                                <p className="text-3xl font-bold mt-4">
                                    {planDisplay?.price ?? '$0/mo'}
                                </p>

                                {periodEndLabel && (
                                    <p className="text-teal-200 text-sm mt-2">
                                        {sub.willRenew
                                            ? `Renews ${periodEndLabel}`
                                            : `Expires ${periodEndLabel}`}
                                    </p>
                                )}
                            </div>

                            <div className="flex items-center gap-3">
                                {activeTier && (
                                    <button
                                        onClick={() => sub.openPortal()}
                                        disabled={sub.loading}
                                        className="inline-flex items-center gap-2 rounded-full bg-white/15 hover:bg-white/25 backdrop-blur-sm px-4 py-2 text-sm font-semibold transition-all disabled:opacity-50"
                                    >
                                        {sub.loading ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <ExternalLink className="h-4 w-4" />
                                        )}
                                        Manage Billing
                                    </button>
                                )}
                                <CreditCard className="h-10 w-10 text-teal-200" />
                            </div>
                        </div>
                    </div>

                    {/* Usage Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <MetricCard
                            label="Active Workflows"
                            value={signals?.active_workflows ?? 0}
                            icon={Zap}
                            gradient="from-violet-400 to-purple-500"
                            delay={0}
                        />
                        <MetricCard
                            label="Open Tasks"
                            value={signals?.open_tasks ?? 0}
                            icon={FileText}
                            gradient="from-sky-400 to-blue-500"
                            delay={0.05}
                        />
                        <MetricCard
                            label="Pending Approvals"
                            value={signals?.pending_approvals ?? 0}
                            icon={Check}
                            gradient="from-amber-400 to-orange-500"
                            delay={0.1}
                        />
                        <MetricCard
                            label="Reports Generated"
                            value={signals?.recent_reports ?? 0}
                            icon={Database}
                            gradient="from-emerald-400 to-teal-500"
                            delay={0.15}
                        />
                    </div>

                    {/* Plan Comparison Table */}
                    <div className="rounded-[28px] border border-slate-100/80 overflow-hidden shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-slate-50">
                                        <th className="text-left p-4 font-semibold text-slate-700 w-1/5">Feature</th>
                                        {TIERS.map((tierKey) => {
                                            const isCurrent = tierKey === activeTier;
                                            return (
                                                <th
                                                    key={tierKey}
                                                    className={`p-4 text-center ${isCurrent ? 'ring-2 ring-teal-600 bg-teal-50' : ''}`}
                                                >
                                                    <div className="font-bold text-slate-900">
                                                        {PLAN_CONFIG[tierKey].name}
                                                    </div>
                                                    <div className="text-slate-500 text-xs mt-1">
                                                        {PLAN_CONFIG[tierKey].price}
                                                    </div>
                                                    {isCurrent && (
                                                        <span className="inline-block mt-1 bg-teal-600 text-white text-xs rounded-full px-2 py-0.5">
                                                            Current
                                                        </span>
                                                    )}
                                                </th>
                                            );
                                        })}
                                    </tr>
                                </thead>
                                <tbody>
                                    {FEATURE_ROWS.map((row, idx) => (
                                        <tr key={row.label} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}>
                                            <td className="p-4 font-medium text-slate-700">{row.label}</td>
                                            {TIERS.map((tierKey) => (
                                                <td
                                                    key={tierKey}
                                                    className={`p-4 text-center ${tierKey === activeTier ? 'ring-2 ring-teal-600 bg-teal-50/30' : ''}`}
                                                >
                                                    {row[tierKey] ? (
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
                                        {TIERS.map((tierKey) => {
                                            const isCurrent = tierKey === activeTier;
                                            return (
                                                <td key={tierKey} className={`p-4 text-center ${isCurrent ? 'ring-2 ring-teal-600' : ''}`}>
                                                    {isCurrent ? (
                                                        <span className="text-sm font-medium text-slate-500">Current Plan</span>
                                                    ) : tierKey === 'enterprise' ? (
                                                        <a
                                                            href="mailto:hello@pikar-ai.com"
                                                            className="inline-block px-4 py-2 rounded-full bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800 shadow-sm hover:shadow-md transition-all"
                                                        >
                                                            Talk to Sales
                                                        </a>
                                                    ) : (
                                                        <button
                                                            onClick={() => handleSubscribe(tierKey)}
                                                            disabled={sub.loading || !PLAN_CONFIG[tierKey].stripePriceId}
                                                            className="px-4 py-2 rounded-full bg-teal-600 text-white text-sm font-semibold hover:bg-teal-700 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
                                                        >
                                                            {sub.loading && <Loader2 className="h-4 w-4 animate-spin" />}
                                                            {activeTier ? 'Change Plan' : 'Subscribe'}
                                                        </button>
                                                    )}
                                                </td>
                                            );
                                        })}
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </motion.div>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
