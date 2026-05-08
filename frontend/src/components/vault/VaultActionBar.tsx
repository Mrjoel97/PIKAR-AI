// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import React from 'react';
import { Send, Layers, Mail, MessageSquare, X } from 'lucide-react';
import type { VaultActionId } from '@/lib/vaultActions';

interface VaultActionBarProps {
    selectedCount: number;
    onAction: (action: VaultActionId) => void;
    onClear: () => void;
}

const CHIPS: Array<{ id: VaultActionId; label: string; icon: React.ReactNode }> = [
    { id: 'post_social', label: 'Post to social', icon: <Send size={14} /> },
    { id: 'use_campaign', label: 'Use in campaign', icon: <Layers size={14} /> },
    { id: 'draft_email', label: 'Draft an email', icon: <Mail size={14} /> },
    { id: 'custom', label: 'Custom prompt', icon: <MessageSquare size={14} /> },
];

export function VaultActionBar({ selectedCount, onAction, onClear }: VaultActionBarProps) {
    if (selectedCount === 0) return null;

    return (
        <div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 rounded-2xl bg-white/95 backdrop-blur shadow-xl border border-slate-200 px-5 py-3 flex items-center gap-3"
            role="region"
            aria-label="Vault selection actions"
        >
            <span className="text-sm font-medium text-slate-700">
                {selectedCount} selected
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                Ask agent to:
            </span>
            <div className="flex items-center gap-2">
                {CHIPS.map((chip) => (
                    <button
                        key={chip.id}
                        type="button"
                        onClick={() => onAction(chip.id)}
                        className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 hover:bg-teal-100 text-teal-700 px-3 py-1.5 text-xs font-medium transition-colors"
                    >
                        {chip.icon}
                        {chip.label}
                    </button>
                ))}
            </div>
            <span className="text-slate-300">|</span>
            <button
                type="button"
                onClick={onClear}
                className="inline-flex items-center gap-1 rounded-full hover:bg-slate-100 text-slate-500 px-3 py-1.5 text-xs font-medium transition-colors"
                aria-label="Clear"
            >
                <X size={14} /> Clear
            </button>
        </div>
    );
}
