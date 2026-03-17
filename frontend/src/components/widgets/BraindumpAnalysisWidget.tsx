'use client';

import React, { useState } from 'react';
import { Brain, Download, BrainCircuit, Loader2, CheckSquare, Lightbulb } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { createInitiativeFromBraindump } from '@/services/initiatives';
import type { WidgetProps } from './WidgetRegistry';
import type { BraindumpAnalysisData } from '@/types/widgets';

export default function BraindumpAnalysisWidget({ definition }: WidgetProps) {
    const data = definition.data as unknown as BraindumpAnalysisData;
    const [isCreatingInitiative, setIsCreatingInitiative] = useState(false);

    const handleCreateInitiative = async () => {
        if (!data.documentId) return;
        setIsCreatingInitiative(true);
        try {
            const result = await createInitiativeFromBraindump(data.documentId);
            if (result.success && result.initiative?.id) {
                window.location.href = `/dashboard/initiatives/${result.initiative.id}`;
            }
        } catch (error) {
            console.error('Failed to create initiative', error);
        } finally {
            setIsCreatingInitiative(false);
        }
    };

    const handleDownload = () => {
        if (!data.markdown) return;
        const blob = new Blob([data.markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${(data.title || 'brain-dump-analysis').replace(/\s+/g, '_').toLowerCase()}.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-start justify-between gap-4 p-6 border-b border-slate-100 bg-slate-50/50">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                            <Brain size={12} />
                            Brain Dump Analysis
                        </span>
                        {data.actionItemCount > 0 && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                                <CheckSquare size={11} />
                                {data.actionItemCount} action item{data.actionItemCount !== 1 ? 's' : ''}
                            </span>
                        )}
                        {data.keyThemes.length > 0 && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200">
                                <Lightbulb size={11} />
                                {data.keyThemes.length} theme{data.keyThemes.length !== 1 ? 's' : ''}
                            </span>
                        )}
                    </div>
                    <h2 className="text-xl font-outfit font-bold text-slate-800 leading-tight truncate">
                        {data.title || 'Brain Dump Analysis'}
                    </h2>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                        onClick={handleCreateInitiative}
                        disabled={isCreatingInitiative || !data.documentId}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-semibold rounded-xl hover:bg-green-700 transition-colors disabled:opacity-50"
                    >
                        {isCreatingInitiative ? <Loader2 size={16} className="animate-spin" /> : <BrainCircuit size={16} />}
                        {isCreatingInitiative ? 'Creating...' : 'Create Initiative'}
                    </button>
                    <button
                        onClick={handleDownload}
                        disabled={!data.markdown}
                        className="flex items-center gap-2 px-4 py-2 bg-white text-slate-600 text-sm font-semibold rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors disabled:opacity-50"
                    >
                        <Download size={16} />
                        Download
                    </button>
                </div>
            </div>

            {/* Markdown Body */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="prose prose-slate prose-lg max-w-none prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-a:text-teal-600 prose-headings:font-outfit prose-img:rounded-xl">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {data.markdown || 'No content available.'}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    );
}
