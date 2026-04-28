'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { PersonaType, PERSONA_INFO } from '@/services/onboarding';
import { DashboardSummary, getDashboardSummary } from '@/services/dashboard';

interface DashboardBriefCardProps {
    persona: PersonaType;
    /** Optional fallback copy used while the brief loads or if the summary fails. */
    fallback?: { title: string; body: string };
    /** Hide the "Recommended next move" side panel for compact placements. */
    compact?: boolean;
}

/**
 * Standalone brief card extracted from CommandCenter. Renders the persona
 * headline, subheadline, the brief title/body, and (optionally) the recommended
 * next move panel. CommandCenter and the idle persona-page workspace surface
 * both render this so the brief stays consistent across surfaces.
 */
export function DashboardBriefCard({ persona, fallback, compact = false }: DashboardBriefCardProps) {
    const router = useRouter();
    const [state, setState] = useState<{ summary: DashboardSummary | null; loading: boolean }>({
        summary: null,
        loading: true,
    });
    const { summary, loading } = state;

    useEffect(() => {
        let cancelled = false;
        getDashboardSummary()
            .then((data) => {
                if (!cancelled) setState({ summary: data, loading: false });
            })
            .catch(() => {
                if (!cancelled) setState({ summary: null, loading: false });
            });
        return () => {
            cancelled = true;
        };
    }, [persona]);

    const info = PERSONA_INFO[persona];
    const dateLabel = useMemo(
        () => new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }),
        [],
    );

    if (loading && !summary) {
        return (
            <div className="mx-auto w-full max-w-6xl">
                <div className="h-52 animate-pulse rounded-[32px] bg-slate-100" />
            </div>
        );
    }

    const briefTitle = summary?.brief.title ?? fallback?.title ?? 'Your brief';
    const briefBody =
        summary?.brief.body
        ?? fallback?.body
        ?? 'Your daily brief will appear here once enough activity is captured. Start a chat with your agent to seed it.';
    const headline = summary?.headline ?? info.title;
    const subheadline = summary?.subheadline ?? info.description;
    const label = summary?.label ?? info.title;
    const recommended = summary?.recommended_action;

    return (
        <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative overflow-hidden rounded-[36px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.95),rgba(248,250,252,0.94)_40%,rgba(226,232,240,0.98))] p-6 shadow-[0_30px_90px_-50px_rgba(15,23,42,0.45)] sm:p-8"
        >
            <div className={`absolute -right-10 -top-12 h-40 w-40 rounded-full bg-gradient-to-br ${info.color} opacity-20 blur-3xl`} />
            <div className="relative flex flex-col gap-6 sm:gap-8 md:flex-row md:items-end md:justify-between">
                <div className="max-w-3xl">
                    <div className="flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
                        <span>{label}</span>
                        <span className="h-1 w-1 rounded-full bg-slate-300" />
                        <span>{dateLabel}</span>
                    </div>
                    <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">{headline}</h1>
                    <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">{subheadline}</p>
                    <div className="mt-6 rounded-3xl border border-white/70 bg-white/70 p-5 backdrop-blur-sm">
                        <p className="text-sm font-semibold text-slate-900">{briefTitle}</p>
                        <p className="mt-2 text-sm leading-6 text-slate-600">{briefBody}</p>
                    </div>
                </div>
                {!compact && recommended && (
                    <div className="w-full max-w-sm rounded-[28px] border border-slate-200 bg-white/90 p-5 shadow-[0_20px_60px_-35px_rgba(15,23,42,0.45)]">
                        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Recommended next move</p>
                        <p className="mt-3 text-lg font-semibold text-slate-900">{recommended.title}</p>
                        <p className="mt-2 text-sm leading-6 text-slate-600">{recommended.description}</p>
                        <button
                            type="button"
                            onClick={() => router.push(recommended.href)}
                            className="mt-5 inline-flex items-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-700"
                        >
                            Open focus area <ArrowRight size={16} />
                        </button>
                    </div>
                )}
            </div>
        </motion.section>
    );
}

export default DashboardBriefCard;
