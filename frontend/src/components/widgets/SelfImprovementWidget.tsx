'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, TrendingDown, Minus, AlertTriangle, Zap, Target, BarChart3, RefreshCw } from 'lucide-react';
import { fetchWithAuth } from '@/services/api';
import type { WidgetProps } from './WidgetRegistry';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DashboardSummary {
    total_interactions: number;
    total_skills_scored: number;
    avg_effectiveness: number;
    underperformers: number;
    high_performers: number;
    pending_actions: number;
    unresolved_gaps: number;
}

interface SkillScore {
    skill_name: string;
    effectiveness_score: number;
    total_uses: number;
    positive_rate: number;
    completion_rate: number;
    trend: string | null;
    score_delta: number | null;
}

interface ImprovementAction {
    id: string;
    action_type: string;
    skill_name: string | null;
    trigger_reason: string;
    status: string;
    created_at: string;
}

interface CoverageGap {
    id: string;
    user_query: string;
    agent_id: string;
    confidence_score: number;
    occurrence_count: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function TrendIcon({ trend }: { trend: string | null }) {
    if (trend === 'improving') return <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />;
    if (trend === 'declining') return <TrendingDown className="w-3.5 h-3.5 text-red-500" />;
    return <Minus className="w-3.5 h-3.5 text-slate-400" />;
}

function ScoreBar({ score }: { score: number }) {
    const pct = Math.round(score * 100);
    const color = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
    return (
        <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
            </div>
            <span className="text-xs font-mono text-slate-500 w-8 text-right">{pct}%</span>
        </div>
    );
}

function StatCard({ icon: Icon, label, value, accent }: { icon: React.ElementType; label: string; value: string | number; accent?: string }) {
    return (
        <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700">
            <div className={`p-2 rounded-lg ${accent || 'bg-indigo-100 dark:bg-indigo-900/40'}`}>
                <Icon className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
                <p className="text-lg font-bold text-slate-800 dark:text-slate-100 leading-none">{value}</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{label}</p>
            </div>
        </div>
    );
}

const ACTION_LABELS: Record<string, string> = {
    skill_created: 'Created',
    skill_refined: 'Refined',
    skill_promoted: 'Promoted',
    skill_demoted: 'Demoted',
    skill_merged: 'Merged',
    gap_identified: 'Gap Found',
    instruction_updated: 'Instruction Updated',
};

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    applied: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    validated: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    reverted: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function SelfImprovementWidget({ definition }: WidgetProps) {
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [scores, setScores] = useState<SkillScore[]>([]);
    const [actions, setActions] = useState<ImprovementAction[]>([]);
    const [gaps, setGaps] = useState<CoverageGap[]>([]);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState<'overview' | 'skills' | 'actions' | 'gaps'>('overview');

    const fetchData = async () => {
        setLoading(true);
        try {
            const [summaryRes, scoresRes, actionsRes, gapsRes] = await Promise.all([
                fetchWithAuth('/self-improvement/dashboard'),
                fetchWithAuth('/self-improvement/scores?limit=20'),
                fetchWithAuth('/self-improvement/actions?limit=10'),
                fetchWithAuth('/self-improvement/gaps?limit=10'),
            ]);
            setSummary(await summaryRes.json());
            const scoresData = await scoresRes.json();
            setScores(scoresData.scores || []);
            const actionsData = await actionsRes.json();
            setActions(actionsData.actions || []);
            const gapsData = await gapsRes.json();
            setGaps(gapsData.gaps || []);
        } catch (err) {
            console.error('Failed to fetch self-improvement data', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchData(); }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
                <span className="ml-2 text-sm text-slate-500">Loading improvement data...</span>
            </div>
        );
    }

    const tabs = [
        { id: 'overview' as const, label: 'Overview', icon: BarChart3 },
        { id: 'skills' as const, label: 'Skills', icon: Zap },
        { id: 'actions' as const, label: 'Actions', icon: Activity },
        { id: 'gaps' as const, label: 'Gaps', icon: AlertTriangle },
    ];

    return (
        <div className="flex flex-col gap-4">
            {/* Tabs */}
            <div className="flex gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">
                {tabs.map(t => (
                    <button
                        key={t.id}
                        onClick={() => setTab(t.id)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                            tab === t.id
                                ? 'bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                        }`}
                    >
                        <t.icon className="w-3.5 h-3.5" />
                        {t.label}
                    </button>
                ))}
                <button
                    onClick={fetchData}
                    className="ml-auto p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                    title="Refresh"
                >
                    <RefreshCw className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* Overview Tab */}
            {tab === 'overview' && summary && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <StatCard icon={Activity} label="Interactions" value={summary.total_interactions} />
                    <StatCard icon={Target} label="Avg Effectiveness" value={`${Math.round(summary.avg_effectiveness * 100)}%`} accent="bg-emerald-100 dark:bg-emerald-900/40" />
                    <StatCard icon={Zap} label="High Performers" value={summary.high_performers} accent="bg-teal-100 dark:bg-teal-900/40" />
                    <StatCard icon={AlertTriangle} label="Underperformers" value={summary.underperformers} accent="bg-red-100 dark:bg-red-900/40" />
                </div>
            )}

            {tab === 'overview' && summary && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <StatCard icon={BarChart3} label="Skills Scored" value={summary.total_skills_scored} />
                    <StatCard icon={Activity} label="Pending Actions" value={summary.pending_actions} accent="bg-amber-100 dark:bg-amber-900/40" />
                    <StatCard icon={Target} label="Unresolved Gaps" value={summary.unresolved_gaps} accent="bg-orange-100 dark:bg-orange-900/40" />
                </div>
            )}

            {/* Skills Tab */}
            {tab === 'skills' && (
                <div className="space-y-2">
                    {scores.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-6">No skill scores yet. Run an evaluation cycle to generate scores.</p>
                    ) : (
                        scores.map(s => (
                            <div key={`${s.skill_name}-${s.effectiveness_score}`} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700">
                                <div className="flex items-center justify-between mb-1.5">
                                    <span className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">{s.skill_name}</span>
                                    <div className="flex items-center gap-1.5">
                                        <TrendIcon trend={s.trend} />
                                        <span className="text-xs text-slate-500">{s.total_uses} uses</span>
                                    </div>
                                </div>
                                <ScoreBar score={s.effectiveness_score} />
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* Actions Tab */}
            {tab === 'actions' && (
                <div className="space-y-2">
                    {actions.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-6">No improvement actions yet.</p>
                    ) : (
                        actions.map(a => (
                            <div key={a.id} className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                                            {ACTION_LABELS[a.action_type] || a.action_type}
                                        </span>
                                        {a.skill_name && (
                                            <span className="text-xs text-slate-400 truncate">· {a.skill_name}</span>
                                        )}
                                    </div>
                                    <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">{a.trigger_reason}</p>
                                </div>
                                <span className={`shrink-0 px-2 py-0.5 rounded-full text-[10px] font-medium ${STATUS_COLORS[a.status] || 'bg-slate-100 text-slate-600'}`}>
                                    {a.status}
                                </span>
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* Gaps Tab */}
            {tab === 'gaps' && (
                <div className="space-y-2">
                    {gaps.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-6">No coverage gaps detected.</p>
                    ) : (
                        gaps.map(g => (
                            <div key={g.id} className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700">
                                <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-slate-700 dark:text-slate-200 line-clamp-2">{g.user_query}</p>
                                    <div className="flex items-center gap-3 mt-1">
                                        <span className="text-[11px] text-slate-400">Agent: {g.agent_id}</span>
                                        <span className="text-[11px] text-slate-400">Confidence: {Math.round(g.confidence_score * 100)}%</span>
                                        <span className="text-[11px] text-amber-600 dark:text-amber-400 font-medium">×{g.occurrence_count}</span>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
