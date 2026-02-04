'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { FileText, UploadCloud, Folder, MoreVertical, Search } from 'lucide-react';

export function VaultInterface() {
    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-outfit font-bold text-slate-900">Knowledge Vault</h1>
                    <p className="text-slate-500 mt-1">Manage your business context, files, and strategic documents.</p>
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition shadow-sm font-medium">
                    <UploadCloud size={20} />
                    <span>Upload Documents</span>
                </button>
            </div>

            {/* Search / Filter Bar */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex items-center gap-4">
                <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                    <input
                        type="text"
                        placeholder="Search files and context..."
                        className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-50 border-none focus:ring-2 focus:ring-teal-500 outline-none text-slate-700"
                    />
                </div>
                <div className="flex gap-2">
                    {['All', 'Strategic', 'Financial', 'Operational'].map(filter => (
                        <button key={filter} className="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors">
                            {filter}
                        </button>
                    ))}
                </div>
            </div>

            {/* Recent Files Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[
                    { name: 'Q3 Financial Projections.pdf', type: 'PDF', size: '2.4 MB', date: '2 hours ago' },
                    { name: 'Marketing Strategy 2026.docx', type: 'DOC', size: '1.1 MB', date: 'Yesterday' },
                    { name: 'Team Structure.xlsx', type: 'XLS', size: '850 KB', date: '3 days ago' },
                ].map((file, i) => (
                    <motion.div
                        key={i}
                        whileHover={{ y: -2 }}
                        className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex items-start justify-between group cursor-pointer"
                    >
                        <div className="flex items-start gap-3">
                            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                                <FileText size={20} />
                            </div>
                            <div>
                                <h3 className="font-semibold text-slate-800 text-sm">{file.name}</h3>
                                <p className="text-xs text-slate-500 mt-1">{file.size} • {file.date}</p>
                            </div>
                        </div>
                        <button className="text-slate-300 hover:text-slate-600">
                            <MoreVertical size={18} />
                        </button>
                    </motion.div>
                ))}
            </div>

            {/* Context Sections */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-teal-50 text-teal-600 rounded-lg">
                            <Folder size={20} />
                        </div>
                        <h2 className="font-bold text-slate-900 text-lg">Business Context</h2>
                    </div>
                    <div className="space-y-4">
                        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                            <h4 className="font-medium text-slate-800 text-sm">Company Mission</h4>
                            <p className="text-xs text-slate-500 mt-2 line-clamp-2">
                                Integrating AI to streamline executive decision making and automate operational workflows...
                            </p>
                        </div>
                        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                            <h4 className="font-medium text-slate-800 text-sm">Target Audience</h4>
                            <p className="text-xs text-slate-500 mt-2 line-clamp-2">
                                C-Suite executives, Founders of Series A+ startups, and Operational Directors...
                            </p>
                        </div>
                    </div>
                </div>

                {/* Upload Area */}
                <div className="border-2 border-dashed border-slate-300 rounded-2xl p-8 flex flex-col items-center justify-center text-center hover:bg-slate-50 transition-colors cursor-pointer group">
                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 group-hover:text-teal-500 group-hover:bg-teal-50 transition-colors mb-4">
                        <UploadCloud size={32} />
                    </div>
                    <h3 className="font-bold text-slate-900">Drop files to upload</h3>
                    <p className="text-sm text-slate-500 mt-2">
                        Supported formats: PDF, DOCX, TXT, MD
                    </p>
                </div>
            </div>
        </div>
    );
}
