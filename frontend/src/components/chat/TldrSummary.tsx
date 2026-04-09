// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import React, { useState } from 'react';
import { ArrowRight, ChevronDown, ChevronRight, FileText, Hash } from 'lucide-react';

// ---------------------------------------------------------------------------
// Parser — extract structured TL;DR block from agent message text
// ---------------------------------------------------------------------------

export interface TldrData {
    summary: string;
    keyNumber: string;
    nextStep: string;
    remainingText: string;
}

/**
 * Parse a ---TLDR--- / ---END_TLDR--- block from agent message text.
 * Returns the three structured fields plus the remaining message body,
 * or null if delimiters are not found.
 */
export function parseTldr(text: string): TldrData | null {
    const startTag = '---TLDR---';
    const endTag = '---END_TLDR---';

    const startIdx = text.indexOf(startTag);
    if (startIdx === -1) return null;

    const endIdx = text.indexOf(endTag, startIdx);
    if (endIdx === -1) return null;

    const block = text.substring(startIdx + startTag.length, endIdx);

    const summaryMatch = block.match(/\*\*Summary:\*\*\s*(.+)/);
    const keyNumberMatch = block.match(/\*\*Key Number:\*\*\s*(.+)/);
    const nextStepMatch = block.match(/\*\*Next Step:\*\*\s*(.+)/);

    if (!summaryMatch || !keyNumberMatch || !nextStepMatch) return null;

    const remainingText = text.substring(endIdx + endTag.length).trimStart();

    return {
        summary: summaryMatch[1].trim(),
        keyNumber: keyNumberMatch[1].trim(),
        nextStep: nextStepMatch[1].trim(),
        remainingText,
    };
}

// ---------------------------------------------------------------------------
// Component — collapsible TL;DR card
// ---------------------------------------------------------------------------

export interface TldrSummaryProps {
    summary: string;
    keyNumber: string;
    nextStep: string;
    defaultExpanded?: boolean;
}

export function TldrSummary({ summary, keyNumber, nextStep, defaultExpanded = false }: TldrSummaryProps) {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded);

    return (
        <div
            className="mb-3 not-prose rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-50 to-slate-50 dark:border-indigo-800/50 dark:from-indigo-950/30 dark:to-slate-900 transition-all duration-200"
        >
            {/* Collapsed / header row */}
            <button
                type="button"
                onClick={() => setIsExpanded((prev) => !prev)}
                aria-expanded={isExpanded}
                className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm"
            >
                {isExpanded
                    ? <ChevronDown size={16} className="flex-shrink-0 text-indigo-500" />
                    : <ChevronRight size={16} className="flex-shrink-0 text-indigo-500" />
                }
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-indigo-600 dark:text-indigo-400">
                    TL;DR
                </span>
                {!isExpanded && (
                    <span className="truncate text-sm text-slate-600 dark:text-slate-300">
                        {summary}
                    </span>
                )}
            </button>

            {/* Expanded detail rows */}
            {isExpanded && (
                <div role="region" className="space-y-2 px-3 pb-3 text-sm">
                    <div className="flex items-start gap-2">
                        <FileText size={14} className="mt-0.5 flex-shrink-0 text-slate-400" />
                        <span className="text-slate-700 dark:text-slate-300">{summary}</span>
                    </div>
                    <div className="flex items-start gap-2">
                        <Hash size={14} className="mt-0.5 flex-shrink-0 text-slate-400" />
                        <span className="text-base font-semibold text-slate-900 dark:text-white">{keyNumber}</span>
                    </div>
                    <div className="flex items-start gap-2">
                        <ArrowRight size={14} className="mt-0.5 flex-shrink-0 text-indigo-500" />
                        <span className="text-sm text-indigo-600 dark:text-indigo-400">{nextStep}</span>
                    </div>
                </div>
            )}
        </div>
    );
}
