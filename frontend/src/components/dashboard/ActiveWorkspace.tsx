'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
    Zap
} from 'lucide-react';
import { WidgetContainer } from '@/components/widgets/WidgetRegistry';
import { PersonaType } from '@/services/onboarding';

interface ActiveWorkspaceProps {
    user: any;
    persona: PersonaType;
}

export function ActiveWorkspace({ user: _user, persona: _persona }: ActiveWorkspaceProps) {
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
                {/* Revenue Chart Widget */}
                <WidgetContainer
                    definition={{
                        type: 'revenue_chart',
                        title: 'Revenue Trends',
                        data: {
                            loading: false,
                            data: {
                                revenue: 1245000,
                                growth: 12.5,
                                history: [10, 25, 40, 30, 60, 85, 120]
                            }
                        }
                    }}
                    className="!bg-slate-50 shadow-[inset_-5px_-5px_10px_rgba(255,255,255,0.8),inset_5px_5px_10px_rgba(0,0,0,0.05),0_15px_30px_rgba(0,0,0,0.05)] border-slate-100/50 rounded-3xl"
                />

                {/* Active Agents / Tasks */}
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
