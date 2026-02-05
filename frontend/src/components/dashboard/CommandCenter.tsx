'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    FileText,
    Map,
    PlusCircle,
    BrainCircuit,
    Building2,
    Zap,
    Clock,
    CheckCircle2,
    TrendingUp,
    ArrowRight
} from 'lucide-react';
import { PersonaType } from '@/services/onboarding';

interface CommandCenterProps {
    user: any;
    persona: PersonaType;
}

export function CommandCenter({ user: _user, persona: _persona }: CommandCenterProps) {
    const router = useRouter();
    const date = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

    const cardRoutes: Record<string, string> = {
        'Workflow Templates': '/dashboard/workflows/templates',
        'User Journeys': '/dashboard/journeys',
        'Create Initiative': '/dashboard/initiatives/new',
        'Brain Dump': '/dashboard/vault',
        'Departments': '/departments',
        'Workflow Generator': '/dashboard/workflows/generate',
        'Ongoing Workflows': '/dashboard/workflows/active',
        'Completed Workflows': '/dashboard/workflows/completed',
        'My Growth Journey': '/dashboard/learning',
    };

    const launchCards = [
        { title: 'Workflow Templates', icon: <FileText size={24} />, color: 'from-blue-400 to-indigo-500', desc: 'Start from best practices' },
        { title: 'User Journeys', icon: <Map size={24} />, color: 'from-purple-400 to-pink-500', desc: 'Map customer experiences' },
        { title: 'Create Initiative', icon: <PlusCircle size={24} />, color: 'from-emerald-400 to-teal-500', desc: 'Launch new strategic projects' },
        { title: 'Brain Dump', icon: <BrainCircuit size={24} />, color: 'from-amber-400 to-orange-500', desc: 'Unload your thoughts' },
        { title: 'Departments', icon: <Building2 size={24} />, color: 'from-slate-400 to-slate-600', desc: 'Manage organizational units' },
        { title: 'Workflow Generator', icon: <Zap size={24} />, color: 'from-cyan-400 to-blue-500', desc: 'AI-powered creation' },
        { title: 'Ongoing Workflows', icon: <Clock size={24} />, color: 'from-yellow-400 to-amber-500', desc: 'Track active progress' },
        { title: 'Completed Workflows', icon: <CheckCircle2 size={24} />, color: 'from-green-400 to-emerald-600', desc: 'Review archive' },
        { title: 'My Growth Journey', icon: <TrendingUp size={24} />, color: 'from-rose-400 to-red-500', desc: 'Personal development' },
    ];

    const handleCardClick = (title: string) => {
        const route = cardRoutes[title];
        if (route) {
            router.push(route);
        }
    };

    return (
        <div className="space-y-10 max-w-6xl mx-auto">
            {/* 1. Daily Brief (Top) */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white rounded-3xl p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 overflow-hidden relative"
            >
                {/* Decorative BG */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-slate-50 rounded-full -translate-y-1/2 translate-x-1/3 blur-3xl" />

                <div className="relative z-10">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-bold font-outfit uppercase tracking-widest text-teal-600">Daily Brief</span>
                        <span className="text-slate-300">•</span>
                        <span className="text-xs font-medium text-slate-400">{date}</span>
                    </div>
                    <h1 className="text-3xl font-outfit font-bold text-slate-900">
                        Good morning, Executive.
                    </h1>
                    <p className="text-slate-600 font-medium mt-3 max-w-xl text-lg leading-relaxed">
                        You have <span className="text-teal-700 font-bold">3 active workflows</span> focusing on Q3 Revenue, and <span className="text-amber-600 font-bold">1 pending approval</span> from the Marketing department. Systems are operating at <span className="text-indigo-600 font-bold">98% efficiency</span>.
                    </p>
                </div>

                <button className="relative z-10 px-8 py-4 bg-teal-900 text-white rounded-xl font-bold tracking-wide hover:bg-teal-800 transition-colors shadow-xl shadow-teal-900/20">
                    View Full Brief
                </button>
            </motion.div>

            {/* Launchpad Grid (9 Cards) */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {launchCards.map((card, i) => (
                    <motion.button
                        key={i}
                        onClick={() => handleCardClick(card.title)}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.05 }}
                        whileHover={{ y: -5, boxShadow: '0 20px 40px -10px rgba(0,0,0,0.1)' }}
                        whileTap={{ scale: 0.98 }}
                        className="group relative bg-slate-50 p-6 rounded-3xl shadow-[inset_-5px_-5px_10px_rgba(255,255,255,0.8),inset_5px_5px_10px_rgba(0,0,0,0.05),0_15px_30px_rgba(0,0,0,0.05)] text-left overflow-hidden h-full flex flex-col border border-slate-100/50"
                    >
                        {/* Icon */}
                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${card.color} flex items-center justify-center text-white shadow-md mb-4 group-hover:scale-110 transition-transform`}>
                            {card.icon}
                        </div>

                        {/* Text */}
                        <div className="flex-1">
                            <h3 className="text-lg font-bold text-slate-800 group-hover:text-teal-700 transition-colors mb-1">
                                {card.title}
                            </h3>
                            <p className="text-sm text-slate-500">
                                {card.desc}
                            </p>
                        </div>

                        {/* Hover Arrow */}
                        <div className="absolute right-6 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 translate-x-4 group-hover:translate-x-0 transition-all duration-300 text-slate-300">
                            <ArrowRight size={20} />
                        </div>
                    </motion.button>
                ))}
            </div>
        </div>
    );
}
