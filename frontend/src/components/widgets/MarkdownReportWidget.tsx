'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { useMemo, useState } from 'react';
import { Copy, Download, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { WidgetProps } from './WidgetRegistry';
import type { MarkdownReportData } from '@/types/widgets';

const KIND_LABELS: Record<string, string> = {
    analysis: 'Analysis',
    research: 'Research',
    report: 'Report',
    notes: 'Notes',
};

function downloadMarkdownFile(markdown: string, title: string) {
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${title.replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '').toLowerCase() || 'agent-report'}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

export default function MarkdownReportWidget({ definition }: WidgetProps) {
    const data = definition.data as unknown as MarkdownReportData;
    const [copied, setCopied] = useState(false);
    const kindLabel = KIND_LABELS[data.kind || 'report'] || 'Report';

    const metadataChips = useMemo(() => {
        const chips: string[] = [];
        if (data.agentName) chips.push(data.agentName);
        if (typeof data.sourceCount === 'number' && data.sourceCount > 0) {
            chips.push(`${data.sourceCount} source${data.sourceCount === 1 ? '' : 's'}`);
        }
        return chips;
    }, [data.agentName, data.sourceCount]);

    const handleCopy = async () => {
        if (!data.markdown || typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
            return;
        }

        try {
            await navigator.clipboard.writeText(data.markdown);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1800);
        } catch (error) {
            console.warn('Failed to copy markdown report:', error);
        }
    };

    return (
        <div className="flex min-h-[460px] flex-col bg-white">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 bg-slate-50/70 px-6 py-4">
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">
                            <FileText size={12} />
                            {kindLabel}
                        </span>
                        {metadataChips.map((chip) => (
                            <span
                                key={chip}
                                className="inline-flex rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-500"
                            >
                                {chip}
                            </span>
                        ))}
                    </div>
                    {data.summary && (
                        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
                            {data.summary}
                        </p>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={() => void handleCopy()}
                        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50"
                    >
                        <Copy size={14} />
                        {copied ? 'Copied' : 'Copy'}
                    </button>
                    <button
                        type="button"
                        onClick={() => downloadMarkdownFile(data.markdown || '', data.title || definition.title || 'agent-report')}
                        className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
                    >
                        <Download size={14} />
                        Download
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-6">
                <div className="prose prose-slate prose-lg max-w-none prose-headings:font-semibold prose-headings:text-slate-900 prose-p:text-slate-700 prose-li:text-slate-700 prose-strong:text-slate-900 prose-a:text-teal-600 prose-pre:overflow-x-auto prose-pre:rounded-2xl prose-pre:bg-slate-950 prose-code:text-slate-900 prose-img:rounded-2xl prose-blockquote:border-teal-200 prose-blockquote:text-slate-600">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {data.markdown || 'No report content available.'}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    );
}
