'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * DirectorProgressCard — surfaces the AI Director's storyboard plan as a
 * collapsible, scene-by-scene card.
 *
 * Driven by the `director_storyboard` widget emitted by the SSE parser when
 * the backend's `planning_done` progress event arrives with
 * `storyboard_captions`. Replaces raw JSON in the trace drawer with a
 * readable, structured view.
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Clapperboard, Clock } from 'lucide-react';

import type { WidgetProps } from '@/components/widgets/WidgetRegistry';
import type {
    DirectorStoryboardCaption,
    DirectorStoryboardData,
} from '@/types/widgets';

export interface DirectorProgressCardProps {
    captions: DirectorStoryboardCaption[];
    scene_count: number;
    video_prompt?: string;
}

function formatDuration(duration?: number): string | null {
    if (typeof duration !== 'number' || !Number.isFinite(duration)) return null;
    if (duration <= 0) return null;
    return `${duration.toFixed(duration % 1 === 0 ? 0 : 1)}s`;
}

export function DirectorProgressCard({
    captions,
    scene_count,
    video_prompt,
}: DirectorProgressCardProps) {
    const [open, setOpen] = useState(true);
    const sceneLabel = scene_count === 1 ? 'scene' : 'scenes';

    return (
        <div className="w-full rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 bg-slate-50/80 border-b border-slate-100 text-left hover:bg-slate-100/70 transition-colors"
                aria-expanded={open}
            >
                <div className="flex items-center gap-2 min-w-0">
                    <span className="inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-teal-100 text-teal-700">
                        <Clapperboard size={14} />
                    </span>
                    <div className="min-w-0">
                        <h4 className="text-sm font-semibold text-slate-800 truncate">
                            Storyboard ({scene_count} {sceneLabel})
                        </h4>
                        {video_prompt && (
                            <p className="text-xs text-slate-500 truncate">
                                {video_prompt}
                            </p>
                        )}
                    </div>
                </div>
                <span className="flex-shrink-0 text-slate-400">
                    {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </span>
            </button>

            {open && (
                <ol className="divide-y divide-slate-100">
                    {captions.length === 0 ? (
                        <li className="px-4 py-3 text-sm text-slate-500">
                            No scene captions available.
                        </li>
                    ) : (
                        captions.map((caption, idx) => {
                            const duration = formatDuration(caption.duration);
                            const sceneNumber = caption.scene || idx + 1;
                            return (
                                <li
                                    key={`${sceneNumber}-${idx}`}
                                    className="flex items-start gap-3 px-4 py-3"
                                >
                                    <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-teal-50 text-[11px] font-semibold text-teal-700">
                                        {sceneNumber}
                                    </span>
                                    <div className="min-w-0 flex-1">
                                        <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-wrap break-words">
                                            {caption.caption}
                                        </p>
                                        {duration && (
                                            <p className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-slate-500">
                                                <Clock size={11} />
                                                {duration}
                                            </p>
                                        )}
                                    </div>
                                </li>
                            );
                        })
                    )}
                </ol>
            )}
        </div>
    );
}

/**
 * Widget-registry entry point. Reads props from a `director_storyboard`
 * `WidgetDefinition` and renders the card.
 */
export default function DirectorProgressCardWidget({ definition }: WidgetProps) {
    const data = definition.data as unknown as DirectorStoryboardData;
    return (
        <DirectorProgressCard
            captions={data?.captions ?? []}
            scene_count={data?.scene_count ?? data?.captions?.length ?? 0}
            video_prompt={data?.video_prompt}
        />
    );
}
