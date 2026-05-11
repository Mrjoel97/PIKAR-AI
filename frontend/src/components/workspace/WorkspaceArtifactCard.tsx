'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { FileText, FileVideo, FileImage, FileQuestion } from 'lucide-react';
import type { WorkspaceArtifactEvent } from '@/types/workspace-events';

interface Props {
    event: WorkspaceArtifactEvent;
}

const IMAGE_KINDS = new Set(['image']);
const VIDEO_KINDS = new Set(['video_render', 'video']);
const DOC_KINDS = new Set(['doc', 'report']);

function DocIcon({ kind }: { kind: string }) {
    if (kind === 'doc' || kind === 'report') {
        return (
            <FileText
                size={20}
                data-testid="artifact-doc-icon"
                aria-hidden="true"
            />
        );
    }
    if (kind === 'image') {
        return <FileImage size={20} aria-hidden="true" />;
    }
    if (kind === 'video_render' || kind === 'video') {
        return <FileVideo size={20} aria-hidden="true" />;
    }
    return <FileQuestion size={20} aria-hidden="true" />;
}

/**
 * Preview-aware artifact card emitted by the workspace SSE bus.
 *
 * Renders an inline preview for image / video_render artifacts and a doc
 * icon strip for doc / report artifacts. Unknown kinds fall through to the
 * summary-only layout — the video-director / graphic-agent visibility gap
 * from spec § 12 is solved by surfacing *every* artifact event regardless of
 * the producing agent.
 */
export function WorkspaceArtifactCard({ event }: Props) {
    const { artifact_kind, preview_url, summary, agent_id, ref } = event;

    let preview: React.ReactNode = null;
    if (preview_url && IMAGE_KINDS.has(artifact_kind)) {
        preview = (
            <img
                src={preview_url}
                alt={summary}
                className="w-full rounded-xl object-cover max-h-72"
            />
        );
    } else if (preview_url && VIDEO_KINDS.has(artifact_kind)) {
        preview = (
            <video
                src={preview_url}
                controls
                data-testid="artifact-preview-video"
                className="w-full rounded-xl max-h-72"
            />
        );
    } else if (DOC_KINDS.has(artifact_kind)) {
        preview = (
            <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-4 text-slate-600">
                <DocIcon kind={artifact_kind} />
                <span className="text-sm capitalize">{artifact_kind}</span>
            </div>
        );
    }

    return (
        <article
            className="flex flex-col gap-3 rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
            data-testid="workspace-artifact-card"
            data-artifact-kind={artifact_kind}
        >
            <header className="flex items-center justify-between">
                <span
                    className="rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-teal-700"
                    aria-label={`agent ${agent_id}`}
                >
                    {agent_id}
                </span>
                <span className="text-[11px] uppercase tracking-wider text-slate-400">
                    {artifact_kind.replace('_', ' ')}
                </span>
            </header>
            {preview}
            <p className="text-sm text-slate-700">{summary}</p>
            <a
                href={ref}
                rel="noreferrer noopener"
                className="text-xs font-semibold text-teal-700 hover:underline"
            >
                Open
            </a>
        </article>
    );
}
