'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { useState, useEffect, useMemo } from 'react';
import { WidgetProps } from './WidgetRegistry';
import { BoardroomData, BoardPacket, TranscriptItem } from '@/types/widgets';
import {
    User, Briefcase, TrendingUp, DollarSign, Gavel,
    ThumbsUp, ThumbsDown, HelpCircle, Shield, AlertTriangle,
    ChevronRight, CheckCircle2,
} from 'lucide-react';
import PersonaEmptyState from './PersonaEmptyState';

export default function BoardroomWidget({ definition }: WidgetProps) {
    const data = definition.data as unknown as BoardroomData;
    const [visibleItems, setVisibleItems] = useState<TranscriptItem[]>([]);
    const [showPacket, setShowPacket] = useState(false);

    const transcript = data?.transcript ?? [];
    const isEmpty = transcript.length === 0;

    // Simulate streaming effect for the widget playback
    useEffect(() => {
        if (isEmpty) return;

        let i = 0;
        const interval = setInterval(() => {
            if (i < transcript.length) {
                setVisibleItems(prev => [...prev, transcript[i]]);
                i++;
            } else {
                clearInterval(interval);
            }
        }, 1500);

        return () => clearInterval(interval);
    }, [transcript, isEmpty]);

    // Show Board Packet after all transcript items are visible
    useEffect(() => {
        if (!isEmpty && visibleItems.length === transcript.length && data.board_packet) {
            const timer = setTimeout(() => setShowPacket(true), 800);
            return () => clearTimeout(timer);
        }
    }, [visibleItems.length, transcript.length, data.board_packet, isEmpty]);

    const allRevealed = visibleItems.length === transcript.length;

    // Group visible items by round
    const round1Items = useMemo(
        () => visibleItems.filter(t => !t.round || t.round === 1),
        [visibleItems]
    );
    const round2Items = useMemo(
        () => visibleItems.filter(t => t.round === 2),
        [visibleItems]
    );

    if (isEmpty) {
        return <PersonaEmptyState widgetType="boardroom" />;
    }

    const getAvatar = (speaker: string) => {
        switch (speaker) {
            case 'CMO': return <TrendingUp className="text-blue-500" />;
            case 'CFO': return <DollarSign className="text-red-500" />;
            case 'CEO': return <Gavel className="text-purple-500" />;
            default: return <User className="text-gray-500" />;
        }
    };

    const getBgColor = (speaker: string) => {
        switch (speaker) {
            case 'CMO': return 'bg-blue-50 border-blue-100 dark:bg-blue-900/20 dark:border-blue-800';
            case 'CFO': return 'bg-red-50 border-red-100 dark:bg-red-900/20 dark:border-red-800';
            case 'CEO': return 'bg-purple-50 border-purple-100 dark:bg-purple-900/20 dark:border-purple-800';
            default: return 'bg-gray-50';
        }
    };

    const getStanceIcon = (stance?: string) => {
        switch (stance) {
            case 'for': return <ThumbsUp size={14} className="text-emerald-500" />;
            case 'against': return <ThumbsDown size={14} className="text-red-500" />;
            case 'nuanced': return <HelpCircle size={14} className="text-amber-500" />;
            default: return null;
        }
    };

    const getStanceLabel = (stance?: string) => {
        switch (stance) {
            case 'for': return 'Supports';
            case 'against': return 'Opposes';
            case 'nuanced': return 'Nuanced';
            default: return '';
        }
    };

    const renderTurn = (turn: TranscriptItem, idx: number) => (
        <div key={`${turn.round}-${turn.speaker}-${idx}`} className={`flex gap-3 animate-fade-in-up ${turn.speaker === 'CEO' ? 'justify-center' : ''}`}>
            {turn.speaker !== 'CEO' && (
                <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center shrink-0">
                    {getAvatar(turn.speaker)}
                </div>
            )}

            <div className={`p-4 rounded-2xl max-w-[80%] border ${getBgColor(turn.speaker)}`}>
                <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold opacity-75">{turn.speaker}</span>
                    {turn.stance && (
                        <span className="flex items-center gap-1 text-xs opacity-60">
                            {getStanceIcon(turn.stance)}
                            {getStanceLabel(turn.stance)}
                        </span>
                    )}
                </div>
                <p className="text-sm dark:text-slate-200">{turn.content}</p>
            </div>

            {turn.speaker === 'CEO' && (
                <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center shrink-0">
                    {getAvatar(turn.speaker)}
                </div>
            )}
        </div>
    );

    const renderRoundDivider = (label: string) => (
        <div className="flex items-center gap-3 py-2">
            <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700" />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                {label}
            </span>
            <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700" />
        </div>
    );

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl overflow-hidden flex flex-col h-full max-h-[900px]">
            {/* Header */}
            <div className="p-4 bg-slate-900 text-white flex items-center gap-3">
                <Briefcase size={20} className="text-amber-400" />
                <div className="flex-1">
                    <h3 className="font-bold">The Boardroom</h3>
                    <p className="text-xs text-slate-400">Topic: {data.topic}</p>
                </div>
                {/* Vote summary pills */}
                {allRevealed && data.vote_summary && (
                    <div className="flex gap-1.5">
                        {Object.entries(data.vote_summary).map(([speaker, stance]) => (
                            <span
                                key={speaker}
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                    stance === 'for' ? 'bg-emerald-900/50 text-emerald-300' :
                                    stance === 'against' ? 'bg-red-900/50 text-red-300' :
                                    'bg-amber-900/50 text-amber-300'
                                }`}
                            >
                                {getStanceIcon(stance)}
                                {speaker}
                            </span>
                        ))}
                    </div>
                )}
            </div>

            {/* Transcript */}
            <div className="p-4 flex-1 overflow-y-auto space-y-4" role="log" aria-live="polite" aria-label="Boardroom discussion transcript">
                {round1Items.length > 0 && renderRoundDivider('Round 1 — Opening Statements')}
                {round1Items.map((turn, idx) => renderTurn(turn, idx))}

                {round2Items.length > 0 && renderRoundDivider('Round 2 — Rebuttals')}
                {round2Items.map((turn, idx) => renderTurn(turn, idx))}
            </div>

            {/* Verdict */}
            {allRevealed && (
                <div className="p-4 border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                        CEO&apos;s Final Decision
                    </h4>
                    <p className="text-sm text-slate-700 dark:text-slate-300 italic">
                        &ldquo;{data.verdict}&rdquo;
                    </p>
                </div>
            )}

            {/* Board Packet */}
            {showPacket && data.board_packet && (
                <BoardPacketSection packet={data.board_packet} />
            )}
        </div>
    );
}


// ---------------------------------------------------------------------------
// Board Packet sub-component
// ---------------------------------------------------------------------------

function BoardPacketSection({ packet }: { packet: BoardPacket }) {
    const confidencePct = Math.round((packet.confidence ?? 0) * 100);

    return (
        <div className="border-t-2 border-amber-300 dark:border-amber-600 bg-amber-50/50 dark:bg-amber-900/10 p-5 space-y-5 animate-fade-in-up">
            <div className="flex items-center gap-2 mb-1">
                <Briefcase size={16} className="text-amber-600 dark:text-amber-400" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                    Board Packet
                </h3>
            </div>

            {/* Recommendation */}
            {packet.recommendation && (
                <div className="bg-white dark:bg-slate-800 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-1">
                        Recommendation
                    </h4>
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                        {packet.recommendation}
                    </p>
                </div>
            )}

            {/* Confidence Score */}
            <div>
                <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                        Confidence
                    </span>
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                        {confidencePct}%
                    </span>
                </div>
                <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                        className={`h-full rounded-full transition-all duration-700 ${
                            confidencePct >= 70 ? 'bg-emerald-500' :
                            confidencePct >= 40 ? 'bg-amber-500' :
                            'bg-red-500'
                        }`}
                        style={{ width: `${confidencePct}%` }}
                    />
                </div>
            </div>

            {/* Pros / Cons columns */}
            {(packet.pros?.length > 0 || packet.cons?.length > 0) && (
                <div className="grid grid-cols-2 gap-4">
                    {/* Pros */}
                    <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2 flex items-center gap-1">
                            <ThumbsUp size={12} /> Pros
                        </h4>
                        <ul className="space-y-1">
                            {packet.pros?.map((pro, i) => (
                                <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                                    <CheckCircle2 size={12} className="text-emerald-500 mt-0.5 shrink-0" />
                                    {pro}
                                </li>
                            ))}
                        </ul>
                    </div>
                    {/* Cons */}
                    <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-red-600 dark:text-red-400 mb-2 flex items-center gap-1">
                            <ThumbsDown size={12} /> Cons
                        </h4>
                        <ul className="space-y-1">
                            {packet.cons?.map((con, i) => (
                                <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                                    <AlertTriangle size={12} className="text-red-500 mt-0.5 shrink-0" />
                                    {con}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}

            {/* Risks */}
            {packet.risks?.length > 0 && (
                <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-2 flex items-center gap-1">
                        <Shield size={12} /> Risks
                    </h4>
                    <ul className="space-y-1">
                        {packet.risks.map((risk, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                                <AlertTriangle size={12} className="text-orange-500 mt-0.5 shrink-0" />
                                {risk}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Estimated Impact */}
            {packet.estimated_impact && (
                <div className="bg-white dark:bg-slate-800 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
                        Estimated Impact
                    </h4>
                    <p className="text-xs text-slate-700 dark:text-slate-300">{packet.estimated_impact}</p>
                </div>
            )}

            {/* Next Steps */}
            {packet.next_steps?.length > 0 && (
                <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-2 flex items-center gap-1">
                        <ChevronRight size={12} /> Next Steps
                    </h4>
                    <ol className="space-y-1.5">
                        {packet.next_steps.map((step, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
                                <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 text-[10px] font-bold shrink-0 mt-0.5">
                                    {i + 1}
                                </span>
                                {step}
                            </li>
                        ))}
                    </ol>
                </div>
            )}

            {/* Dissenting Views */}
            {packet.dissenting_views?.length > 0 && (
                <div className="opacity-80">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                        Dissenting Views
                    </h4>
                    <ul className="space-y-1">
                        {packet.dissenting_views.map((view, i) => (
                            <li key={i} className="text-xs text-slate-500 dark:text-slate-500 italic">
                                &ldquo;{view}&rdquo;
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
