'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { createClient } from '@/lib/supabase/client';
import MetricCard from '@/components/ui/MetricCard';
import {
    PlusCircle,
    Filter,
    Search,
    ArrowRight,
    CheckCircle2,
    Clock,
    AlertTriangle,
    Pause,
    Circle,
    Target,
    Lightbulb,
    FlaskConical,
    Hammer,
    Rocket,
} from 'lucide-react';

type InitiativeStatus = 'not_started' | 'in_progress' | 'completed' | 'blocked' | 'on_hold';
type InitiativePhase = 'ideation' | 'validation' | 'prototype' | 'build' | 'scale';

interface Initiative {
    id: string;
    title: string;
    description: string;
    status: InitiativeStatus;
    priority: string;
    progress: number;
    phase: InitiativePhase;
    phase_progress: Record<string, number>;
    created_at: string;
    metadata: Record<string, unknown>;
}

const statusConfig: Record<InitiativeStatus, { label: string; color: string; icon: React.ReactNode }> = {
    not_started: { label: 'Not Started', color: 'bg-slate-100 text-slate-600', icon: <Circle size={14} /> },
    in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-700', icon: <Clock size={14} /> },
    completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700', icon: <CheckCircle2 size={14} /> },
    blocked: { label: 'Blocked', color: 'bg-red-100 text-red-700', icon: <AlertTriangle size={14} /> },
    on_hold: { label: 'On Hold', color: 'bg-amber-100 text-amber-700', icon: <Pause size={14} /> },
};

const phaseConfig: Record<InitiativePhase, { label: string; icon: React.ReactNode; color: string }> = {
    ideation: { label: 'Ideation', icon: <Lightbulb size={14} />, color: 'text-amber-600' },
    validation: { label: 'Validation', icon: <Target size={14} />, color: 'text-blue-600' },
    prototype: { label: 'Prototype', icon: <FlaskConical size={14} />, color: 'text-purple-600' },
    build: { label: 'Build', icon: <Hammer size={14} />, color: 'text-indigo-600' },
    scale: { label: 'Scale', icon: <Rocket size={14} />, color: 'text-emerald-600' },
};

const priorityColors: Record<string, string> = {
    critical: 'bg-red-50 text-red-700 border-red-200',
    high: 'bg-orange-50 text-orange-700 border-orange-200',
    medium: 'bg-blue-50 text-blue-700 border-blue-200',
    low: 'bg-slate-50 text-slate-600 border-slate-200',
};

export default function InitiativesPage() {
    const router = useRouter();
    const [initiatives, setInitiatives] = useState<Initiative[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterStatus, setFilterStatus] = useState<string>('all');
    const [filterPhase, setFilterPhase] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');

    const breadcrumbItems = [
        { label: 'Home', href: '/dashboard' },
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Initiatives' },
    ];

    useEffect(() => {
        fetchInitiatives();
    }, []);

    async function fetchInitiatives() {
        try {
            const supabase = createClient();
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) return;

            const { data, error } = await supabase
                .from('initiatives')
                .select('*')
                .eq('user_id', user.id)
                .order('created_at', { ascending: false });

            if (error) throw error;
            setInitiatives(data || []);
        } catch (err) {
            console.error('Error fetching initiatives:', err);
        } finally {
            setLoading(false);
        }
    }

    const filteredInitiatives = initiatives.filter((ini) => {
        if (filterStatus !== 'all' && ini.status !== filterStatus) return false;
        if (filterPhase !== 'all' && ini.phase !== filterPhase) return false;
        if (searchQuery && !ini.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        return true;
    });

    const metrics = {
        total: initiatives.length,
        in_progress: initiatives.filter((i) => i.status === 'in_progress').length,
        completed: initiatives.filter((i) => i.status === 'completed').length,
        blocked: initiatives.filter((i) => i.status === 'blocked').length,
    };

    return (
        <DashboardErrorBoundary fallbackTitle="Initiatives Error">
        <PremiumShell>
            <div className="mb-6">
                <Breadcrumb items={breadcrumbItems} />
            </div>

            <div className="space-y-6 max-w-6xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-500 shadow-lg shadow-teal-200">
                            <Target className="h-6 w-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Initiatives</h1>
                            <p className="mt-0.5 text-sm text-slate-500">Track your strategic projects through the 5-phase framework</p>
                        </div>
                    </div>
                    <button
                        onClick={() => router.push('/dashboard/initiatives/new')}
                        className="flex items-center gap-2 px-5 py-2.5 bg-teal-900 text-white rounded-xl font-semibold hover:bg-teal-800 transition-colors shadow-lg shadow-teal-900/20"
                    >
                        <PlusCircle size={18} />
                        New Initiative
                    </button>
                </div>

                {/* Metrics */}
                <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                    <MetricCard label="Total" value={metrics.total} icon={Target} gradient="from-slate-400 to-slate-600" delay={0} />
                    <MetricCard label="In Progress" value={metrics.in_progress} icon={Clock} gradient="from-blue-400 to-indigo-500" delay={0.05} />
                    <MetricCard label="Completed" value={metrics.completed} icon={CheckCircle2} gradient="from-emerald-400 to-teal-500" delay={0.1} />
                    <MetricCard label="Blocked" value={metrics.blocked} icon={AlertTriangle} gradient="from-rose-400 to-red-500" delay={0.15} />
                </div>

                {/* Filters */}
                <div className="flex flex-col sm:flex-row gap-3">
                    <div className="relative flex-1">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search initiatives..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <Filter size={16} className="text-slate-400" />
                        <select
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value)}
                            className="px-3 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                        >
                            <option value="all">All Statuses</option>
                            <option value="not_started">Not Started</option>
                            <option value="in_progress">In Progress</option>
                            <option value="completed">Completed</option>
                            <option value="blocked">Blocked</option>
                            <option value="on_hold">On Hold</option>
                        </select>
                        <select
                            value={filterPhase}
                            onChange={(e) => setFilterPhase(e.target.value)}
                            className="px-3 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                        >
                            <option value="all">All Phases</option>
                            <option value="ideation">Ideation</option>
                            <option value="validation">Validation</option>
                            <option value="prototype">Prototype</option>
                            <option value="build">Build</option>
                            <option value="scale">Scale</option>
                        </select>
                    </div>
                </div>

                {/* Initiative List */}
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-8 w-8 border-2 border-teal-500 border-t-transparent" />
                    </div>
                ) : filteredInitiatives.length === 0 ? (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white p-12 rounded-[28px] border border-dashed border-slate-200 flex flex-col items-center justify-center text-center"
                    >
                        <Rocket size={48} className="text-slate-300 mb-4" />
                        <h3 className="text-lg font-semibold text-slate-700 mb-2">
                            {initiatives.length === 0 ? 'No initiatives yet' : 'No matching initiatives'}
                        </h3>
                        <p className="text-slate-400 mb-6 max-w-md">
                            {initiatives.length === 0
                                ? 'Create your first initiative to start tracking strategic projects through the 5-phase framework.'
                                : 'Try adjusting your filters or search query.'}
                        </p>
                        {initiatives.length === 0 && (
                            <button
                                onClick={() => router.push('/dashboard/initiatives/new')}
                                className="flex items-center gap-2 px-5 py-2.5 bg-teal-900 text-white rounded-xl font-semibold hover:bg-teal-800 transition-colors"
                            >
                                <PlusCircle size={18} />
                                Create First Initiative
                            </button>
                        )}
                    </motion.div>
                ) : (
                    <AnimatePresence>
                        <div className="space-y-3">
                            {filteredInitiatives.map((ini, idx) => {
                                const sc = statusConfig[ini.status] || statusConfig.not_started;
                                const pc = phaseConfig[ini.phase as InitiativePhase] || phaseConfig.ideation;
                                const prio = priorityColors[ini.priority] || priorityColors.medium;

                                return (
                                    <motion.div
                                        key={ini.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.03 }}
                                        onClick={() => router.push(`/dashboard/initiatives/${ini.id}`)}
                                        className="bg-white rounded-[28px] p-5 border border-slate-100/80 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] hover:-translate-y-0.5 transition-all cursor-pointer group"
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap mb-1.5">
                                                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${sc.color}`}>
                                                        {sc.icon} {sc.label}
                                                    </span>
                                                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${prio} border`}>
                                                        {ini.priority}
                                                    </span>
                                                    <span className={`inline-flex items-center gap-1 text-xs font-medium ${pc.color}`}>
                                                        {pc.icon} {pc.label}
                                                    </span>
                                                </div>
                                                <h3 className="text-base font-semibold text-slate-800 truncate group-hover:text-teal-700 transition-colors">
                                                    {ini.title}
                                                </h3>
                                                {ini.description && (
                                                    <p className="text-sm text-slate-500 mt-1 line-clamp-1">{ini.description}</p>
                                                )}
                                            </div>

                                            <div className="flex items-center gap-3 shrink-0">
                                                {/* Phase Progress Mini */}
                                                <div className="hidden md:flex items-center gap-0.5">
                                                    {(['ideation', 'validation', 'prototype', 'build', 'scale'] as InitiativePhase[]).map((p) => {
                                                        const progress = ini.phase_progress?.[p] ?? 0;
                                                        const isCurrent = ini.phase === p;
                                                        return (
                                                            <div
                                                                key={p}
                                                                className={`w-6 h-1.5 rounded-full transition-colors ${
                                                                    progress >= 100
                                                                        ? 'bg-emerald-500'
                                                                        : isCurrent
                                                                        ? 'bg-blue-500'
                                                                        : 'bg-slate-200'
                                                                }`}
                                                                title={`${phaseConfig[p].label}: ${progress}%`}
                                                            />
                                                        );
                                                    })}
                                                </div>

                                                <div className="text-right">
                                                    <p className="text-lg font-bold text-slate-700">{ini.progress}%</p>
                                                </div>

                                                <ArrowRight size={18} className="text-slate-300 group-hover:text-teal-500 transition-colors" />
                                            </div>
                                        </div>

                                        {/* Progress bar */}
                                        <div className="mt-3 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-teal-400 to-emerald-500 rounded-full transition-all duration-500"
                                                style={{ width: `${ini.progress}%` }}
                                            />
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    </AnimatePresence>
                )}
            </div>
        </PremiumShell>
        </DashboardErrorBoundary>
    );
}
