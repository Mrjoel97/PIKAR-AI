'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Save, Clock, CheckCircle2, AlertCircle, FileText, ChevronRight, Search, Filter } from 'lucide-react';

interface Report {
    id: number;
    title: string;
    type: string;
    status: 'Completed' | 'Processing' | 'Failed';
    date: string;
    summary: string;
    content?: string; // Extended content for detail view
}

export function ReportsInterface() {
    // Mock reports logic with more detail
    const reports: Report[] = [
        {
            id: 1,
            title: 'Q3 Market Analysis',
            type: 'Strategy',
            status: 'Completed',
            date: '2 hours ago',
            summary: 'Detailed analysis of competitor movements in the APAC region.',
            content: 'Full market analysis report including SWOT analysis, competitor pricing strategies, and recommended GTM adjustments for Q4. The data suggests a strong opportunity in the mid-market segment due to a competitor exit.'
        },
        {
            id: 2,
            title: 'Weekly Team Performance',
            type: 'HR',
            status: 'Completed',
            date: 'Yesterday',
            summary: 'Productivity metrics for the engineering team.',
            content: 'Team velocity increased by 12% this sprint. Key bottleneck identified in QA handoff process. Recommendation: Implement automated regression testing suite to reduce cycle time.'
        },
        {
            id: 3,
            title: 'Customer Churn Prediction',
            type: 'Data Science',
            status: 'Processing',
            date: 'In Progress',
            summary: 'Generating predictive models based on last month\'s usage data.',
            content: 'Processing large dataset (2.5TB). estimated completion time: 45 minutes. Preliminary results indicate a high correlation between support ticket volume and churn risk.'
        },
        {
            id: 4,
            title: 'Infrastructure Cost Audit',
            type: 'Finance',
            status: 'Failed',
            date: '2 days ago',
            summary: 'Could not access AWS billing API.',
            content: 'Error: Access Denied. The service role lacks "billing:GetCostAndUsage" permissions. Please update the IAM policy and retry the report generation.'
        },
        {
            id: 5,
            title: 'Social Media Engagement',
            type: 'Marketing',
            status: 'Completed',
            date: '3 days ago',
            summary: 'Weekly analysis of LinkedIn and Twitter metrics.',
            content: 'Engagement rate is up 5% week-over-week. Top performing post was the "Future of AI" thought leadership piece. identifying low-performing content pillars for deprecation.'
        },
    ];

    const [selectedId, setSelectedId] = useState<number>(reports[0].id);
    const selectedReport = reports.find(r => r.id === selectedId) || reports[0];

    return (
        <div className="min-h-screen flex flex-col pb-10">
            {/* Header */}
            <div className="flex items-center justify-between mb-6 flex-shrink-0">
                <div>
                    <h1 className="text-3xl font-outfit font-bold text-slate-900">AI Reports</h1>
                    <p className="text-slate-500 mt-1">Generated insights and workflow outputs.</p>
                </div>
                <div className="flex gap-3">
                    <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 transition-colors shadow-sm">
                        <Filter size={18} />
                        <span>Filter</span>
                    </button>
                    <button className="flex items-center gap-2 px-4 py-2 bg-teal-900 text-white rounded-xl hover:bg-teal-800 transition-colors shadow-md">
                        <FileText size={18} />
                        <span>New Report</span>
                    </button>
                </div>
            </div>

            {/* Main Content Area - Split View */}
            <div className="flex-1 flex gap-8 items-start">

                {/* LEFT: List View (30%) */}
                <div className="w-[30%] min-w-[320px] flex flex-col gap-4 sticky top-6 max-h-[calc(100vh-3rem)] overflow-y-auto pr-2 pb-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search reports..."
                            className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500/20 text-slate-700 shadow-sm"
                        />
                    </div>

                    <div className="space-y-3">
                        {reports.map((report) => (
                            <motion.button
                                key={report.id}
                                layoutId={`card-${report.id}`}
                                onClick={() => setSelectedId(report.id)}
                                className={`w-full text-left p-4 rounded-xl border transition-all duration-200 group relative overflow-hidden
                                    ${selectedId === report.id
                                        ? 'bg-teal-50 border-teal-200 shadow-md ring-1 ring-teal-500/30'
                                        : 'bg-white border-slate-200 hover:border-teal-200 hover:shadow-sm'
                                    }
                                `}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <div className={`p-1.5 rounded-lg 
                                        ${report.status === 'Completed' ? 'bg-green-100 text-green-700' :
                                            report.status === 'Processing' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'}
                                    `}>
                                        {report.status === 'Completed' ? <CheckCircle2 size={16} /> :
                                            report.status === 'Processing' ? <Clock size={16} /> : <AlertCircle size={16} />}
                                    </div>
                                    <span className="text-xs text-slate-400 font-medium">{report.date}</span>
                                </div>
                                <h3 className={`font-bold text-sm mb-1 line-clamp-1 ${selectedId === report.id ? 'text-teal-900' : 'text-slate-700'}`}>
                                    {report.title}
                                </h3>
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] uppercase font-bold tracking-wider">
                                        {report.type}
                                    </span>
                                </div>
                                <p className={`text-xs line-clamp-2 ${selectedId === report.id ? 'text-teal-800/70' : 'text-slate-500'}`}>
                                    {report.summary}
                                </p>

                                {selectedId === report.id && (
                                    <div className="absolute right-0 top-0 bottom-0 w-1 bg-teal-500" />
                                )}
                            </motion.button>
                        ))}
                    </div>
                </div>

                {/* RIGHT: Detail View (70%) */}
                <div className="flex-1 bg-white rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col relative h-fit min-h-[600px]">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={selectedId}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ duration: 0.2 }}
                            className="flex flex-col h-full bg-white relative z-10 rounded-3xl"
                        >
                            {/* Detail Header */}
                            <div className="p-8 border-b border-slate-100 bg-slate-50/50">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <div className="flex items-center gap-3 mb-3">
                                            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2
                                                ${selectedReport.status === 'Completed' ? 'bg-green-100 text-green-700' :
                                                    selectedReport.status === 'Processing' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'}
                                            `}>
                                                {selectedReport.status === 'Completed' ? <CheckCircle2 size={14} /> :
                                                    selectedReport.status === 'Processing' ? <Clock size={14} /> : <AlertCircle size={14} />}
                                                {selectedReport.status}
                                            </span>
                                            <span className="text-slate-400 text-sm">•</span>
                                            <span className="text-slate-500 text-sm font-medium">{selectedReport.type}</span>
                                            <span className="text-slate-400 text-sm">•</span>
                                            <span className="text-slate-500 text-sm">{selectedReport.date}</span>
                                        </div>
                                        <h2 className="text-3xl font-outfit font-bold text-slate-800 leading-tight">
                                            {selectedReport.title}
                                        </h2>
                                    </div>
                                    <button className="p-2 hover:bg-slate-100 rounded-xl text-slate-400 hover:text-slate-600 transition-colors">
                                        <ChevronRight size={24} className="rotate-90 md:rotate-0" />
                                    </button>
                                </div>
                            </div>

                            {/* Detail Body */}
                            <div className="p-10 flex-1">
                                <div className="prose prose-slate prose-lg max-w-none">
                                    <h3 className="text-lg font-bold text-slate-800 mb-2">Executive Summary</h3>
                                    <p className="text-slate-600 text-lg leading-relaxed mb-8">
                                        {selectedReport.summary}
                                    </p>

                                    <h3 className="text-lg font-bold text-slate-800 mb-2">Full Details</h3>
                                    <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100 text-slate-700 leading-relaxed whitespace-pre-line">
                                        {selectedReport.content}
                                    </div>
                                </div>
                            </div>

                            {/* Detail Footer Actions */}
                            <div className="p-8 border-t border-slate-100 bg-white flex justify-end gap-3 sticky bottom-0 z-20 rounded-b-3xl">
                                <button className="px-6 py-3 text-slate-600 font-bold hover:bg-slate-50 rounded-xl transition-colors">
                                    Export PDF
                                </button>
                                <button className="flex items-center gap-2 px-8 py-3 bg-teal-900 text-white rounded-xl font-bold tracking-wide hover:bg-teal-800 transition-colors shadow-lg shadow-teal-900/10">
                                    <Save size={20} />
                                    <span>Save to Vault</span>
                                </button>
                            </div>
                        </motion.div>
                    </AnimatePresence>

                    {/* Background decoration for empty state or loading */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-5">
                        <FileText size={300} />
                    </div>
                </div>
            </div>
        </div>
    );
}
