// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import React from 'react';
import { HelpCircle } from 'lucide-react';

// ---------------------------------------------------------------------------
// Parser — extracts structured intent options from agent message text
// ---------------------------------------------------------------------------

export interface IntentParseResult {
    introText: string;
    options: string[];
    remainingText: string;
}

const INTENT_START = '---INTENT_OPTIONS---';
const INTENT_END = '---END_OPTIONS---';
const OPTION_RE = /\[OPTION_\d+\]\s*/g;

/**
 * Parse an agent message for the intent clarification block.
 *
 * Returns `null` when the message does not contain the delimiters,
 * allowing the caller to fall back to default markdown rendering.
 */
export function parseIntentOptions(text: string): IntentParseResult | null {
    const startIdx = text.indexOf(INTENT_START);
    const endIdx = text.indexOf(INTENT_END);

    if (startIdx === -1 || endIdx === -1 || endIdx <= startIdx) return null;

    const before = text.slice(0, startIdx).trim();
    const block = text.slice(startIdx + INTENT_START.length, endIdx).trim();
    const after = text.slice(endIdx + INTENT_END.length).trim();

    // Split block into lines, separate intro from option lines
    const lines = block.split('\n').map((l) => l.trim()).filter(Boolean);

    const introLines: string[] = [];
    const options: string[] = [];

    for (const line of lines) {
        if (/^\[OPTION_\d+\]/.test(line)) {
            options.push(line.replace(OPTION_RE, '').trim());
        } else {
            // Lines before the first option are intro text
            if (options.length === 0) {
                introLines.push(line);
            }
        }
    }

    if (options.length === 0) return null;

    const introText = introLines.join(' ') || "I'd like to help! Your request could mean a few different things:";

    // Combine any text before/after the block as remaining
    const remainingText = [before, after].filter(Boolean).join('\n\n');

    return { introText, options, remainingText };
}

// ---------------------------------------------------------------------------
// Component — renders clickable intent option cards
// ---------------------------------------------------------------------------

export interface IntentClarificationProps {
    introText: string;
    options: string[];
    onSelect: (optionText: string) => void;
}

export function IntentClarification({ introText, options, onSelect }: IntentClarificationProps) {
    return (
        <div className="not-prose my-2 rounded-xl border border-indigo-100 bg-gradient-to-b from-indigo-50/60 to-white shadow-sm">
            {/* Header */}
            <div className="flex items-center gap-2 border-b border-indigo-100/60 px-4 py-2.5">
                <HelpCircle size={16} className="text-indigo-500" />
                <span className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                    Let me clarify
                </span>
            </div>

            {/* Intro text */}
            <div className="px-4 pt-3 pb-1">
                <p className="text-sm text-slate-600">{introText}</p>
            </div>

            {/* Option buttons */}
            <div className="flex flex-col gap-2 px-4 pb-4 pt-2">
                {options.map((option, idx) => (
                    <button
                        key={idx}
                        type="button"
                        role="button"
                        onClick={() => onSelect(option)}
                        className="w-full px-4 py-3 text-left text-sm font-medium bg-slate-50 hover:bg-indigo-50 hover:text-indigo-700 border border-slate-200 hover:border-indigo-300 rounded-xl transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-1"
                    >
                        {option}
                    </button>
                ))}
            </div>
        </div>
    );
}
