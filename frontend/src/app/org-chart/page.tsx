'use client';

import React from 'react';
import dynamic from 'next/dynamic';

const OrgChart = dynamic(() => import('@/components/org-chart/OrgChart'), {
    ssr: false,
    loading: () => <p>Loading Chart...</p>
});

export default function OrgChartPage() {
    return (
        <div className="h-screen w-full bg-slate-50 dark:bg-slate-900 flex flex-col">
            <div className="p-4 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center shadow-sm z-10">
                <div>
                    <h1 className="text-xl font-bold text-slate-800 dark:text-white">Hybrid Workforce</h1>
                    <p className="text-sm text-slate-500">Real-time view of your AI Agents and their status</p>
                </div>
                <div className="flex gap-2 text-sm">
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full">1 Director</span>
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full">Active Agents</span>
                </div>
            </div>
            <div className="flex-1 relative">
                <OrgChart />
            </div>
        </div>
    );
}
