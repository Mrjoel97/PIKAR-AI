'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell'
import { Plus, MoreHorizontal, ArrowUpRight, ArrowDownRight, Clock, CheckCircle2, Circle, Zap } from 'lucide-react'
import { WidgetContainer } from '@/components/widgets/WidgetRegistry' // Using Container instead of direct widget
import { WidgetDefinition, SavedWidget } from '@/types/widgets'
import { WidgetDisplayService } from '@/services/widgetDisplay'
import { createClient } from '@/lib/supabase/client'

interface ActiveWorkspaceProps {
    user: any;
    persona: string;
}

export function ActiveWorkspace({ user, persona }: ActiveWorkspaceProps) {
    const [activeTab, setActiveTab] = useState('overview');
    const [workspaceWidgets, setWorkspaceWidgets] = useState<SavedWidget[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadWidgets = async () => {
            const supabase = createClient();
            const { data } = await supabase.auth.getUser();
            if (data?.user) {
                const service = new WidgetDisplayService();
                const pinned = service.getPinnedWidgets(data.user.id);
                // Filter for workspace-relevant widgets
                const relevant = pinned.filter(w =>
                    ['revenue_chart', 'initiative_dashboard', 'kanban_board', 'product_launch'].includes(w.definition.type)
                );
                setWorkspaceWidgets(relevant);
            }
            setLoading(false);
        };
        loadWidgets();
    }, []);
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

    return (
        <div className="space-y-10">
            {/* Header / Welcome */}
            <div className="space-y-2">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h1 className="text-xl lg:text-3xl font-outfit font-bold text-slate-900 tracking-tight">
                        {greeting}, <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-cyan-600">Executive</span>.
                    </h1>
                    <p className="text-slate-500 mt-2 text-sm">
                        Here is your active workspace.
                    </p>
                </motion.div>
            </div>

            {/* Widgets Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {workspaceWidgets.length > 0 ? (
                    workspaceWidgets.map((widget, idx) => (
                        <WidgetContainer
                            key={widget.id || idx}
                            definition={widget.definition}
                            className="!bg-slate-50 shadow-[inset_-5px_-5px_10px_rgba(255,255,255,0.8),inset_5px_5px_10px_rgba(0,0,0,0.05),0_15px_30px_rgba(0,0,0,0.05)] border-slate-100/50 rounded-3xl h-full"
                        />
                    ))
                ) : (
                    // Fallback: Default Welcome Widget or Empty State
                    <div className="bg-slate-50 p-8 rounded-3xl shadow-[inset_-5px_-5px_10px_rgba(255,255,255,0.8),inset_5px_5px_10px_rgba(0,0,0,0.05),0_15px_30px_rgba(0,0,0,0.05)] border border-slate-100/50">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-bold text-slate-900">Get Started</h2>
                            <Clock size={20} className="text-slate-400" />
                        </div>
                        <p className="text-slate-500 mb-4">
                            Your workspace is empty. Chat with your agent and pin widgets here to track your initiatives.
                        </p>
                    </div>
                )}

                {/* Always show Active Agents as per plan */}
                <div className="bg-slate-50 p-8 rounded-3xl shadow-[inset_-5px_-5px_10px_rgba(255,255,255,0.8),inset_5px_5px_10px_rgba(0,0,0,0.05),0_15px_30px_rgba(0,0,0,0.05)] border border-slate-100/50">
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h2 className="text-xl font-bold text-slate-900">Active Agents</h2>
                            <p className="text-sm text-slate-500">Operational status check</p>
                        </div>
                        <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
                            <Zap size={20} />
                        </div>
                    </div>

                    <div className="space-y-4">
                        {[
                            { name: 'Sarah Jenkins', role: 'Support Lead', status: 'online', color: 'bg-green-500' },
                            { name: 'Michael Chen', role: 'DevOps', status: 'busy', color: 'bg-amber-500' },
                            { name: 'System Bot A1', role: 'Automated Tasks', status: 'running', color: 'bg-teal-500' },
                        ].map((agent, i) => (
                            <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer">
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-slate-700 font-bold border border-slate-200">
                                        {agent.name.charAt(0)}
                                    </div>
                                    <div>
                                        <div className="font-bold text-slate-900 text-sm">{agent.name}</div>
                                        <div className="text-xs text-slate-500">{agent.role}</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className={`w-2 h-2 rounded-full ${agent.color}`} />
                                    <span className="text-xs font-medium text-slate-600 uppercase">{agent.status}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
