'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { Users } from 'lucide-react';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';

const OrgChart = dynamic(() => import('@/components/org-chart/OrgChart'), {
    ssr: false,
    loading: () => <p>Loading Chart...</p>
});

export default function OrgChartPage() {
    return (
        <DashboardErrorBoundary fallbackTitle="Org Chart Error">
        <div className="h-screen w-full bg-slate-50 dark:bg-slate-900 flex flex-col">
            <motion.div
                initial={{ opacity: 0, y: -12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: [0.21, 0.47, 0.32, 0.98] }}
                className="p-4 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center shadow-sm z-10"
            >
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-400 to-violet-500 shadow-lg">
                        <Users className="h-5 w-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-slate-800 dark:text-white">Hybrid Workforce</h1>
                        <p className="text-sm text-slate-500">Real-time view of your AI Agents and their status</p>
                    </div>
                </div>
                <div className="flex gap-2 text-sm">
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full">1 Director</span>
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full">Active Agents</span>
                </div>
            </motion.div>
            <div className="flex-1 relative">
                <OrgChart />
            </div>
        </div>
        </DashboardErrorBoundary>
    );
}
