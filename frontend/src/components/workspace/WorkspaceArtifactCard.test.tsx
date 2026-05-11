// @vitest-environment jsdom

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkspaceArtifactCard } from './WorkspaceArtifactCard';
import type { WorkspaceArtifactEvent } from '@/types/workspace-events';

function fixture(over: Partial<WorkspaceArtifactEvent> = {}): WorkspaceArtifactEvent {
    return {
        kind: 'artifact',
        agent_id: 'FIN',
        contract_id: 'c-1',
        artifact_kind: 'report',
        ref: 'vault://abc',
        summary: 'FY26 H1 forecast',
        preview_url: null,
        ...over,
    };
}

describe('WorkspaceArtifactCard', () => {
    it('renders the summary and agent badge', () => {
        render(<WorkspaceArtifactCard event={fixture()} />);
        expect(screen.getByText('FY26 H1 forecast')).toBeTruthy();
        expect(screen.getByText('FIN')).toBeTruthy();
    });

    it('renders an <img> preview for image artifacts', () => {
        render(
            <WorkspaceArtifactCard
                event={fixture({
                    artifact_kind: 'image',
                    preview_url: 'https://cdn/x.png',
                })}
            />,
        );
        const img = screen.getByRole('img', {
            name: /FY26 H1 forecast/i,
        }) as HTMLImageElement;
        expect(img.src).toContain('https://cdn/x.png');
    });

    it('renders a <video> preview for video_render artifacts', () => {
        render(
            <WorkspaceArtifactCard
                event={fixture({
                    artifact_kind: 'video_render',
                    preview_url: 'https://cdn/x.mp4',
                })}
            />,
        );
        const video = screen.getByTestId('artifact-preview-video') as HTMLVideoElement;
        expect(video.src).toContain('https://cdn/x.mp4');
    });

    it('renders a doc icon for doc/report artifacts without a preview', () => {
        render(<WorkspaceArtifactCard event={fixture({ artifact_kind: 'doc' })} />);
        expect(screen.getByTestId('artifact-doc-icon')).toBeTruthy();
    });

    it('renders a doc icon for report artifacts too', () => {
        render(<WorkspaceArtifactCard event={fixture({ artifact_kind: 'report' })} />);
        expect(screen.getByTestId('artifact-doc-icon')).toBeTruthy();
    });

    it('falls through to the summary-only layout when no preview is available and kind is unknown', () => {
        render(
            <WorkspaceArtifactCard
                event={fixture({ artifact_kind: 'data_query', preview_url: null })}
            />,
        );
        // Card itself still renders; no preview node is attached.
        expect(screen.getByTestId('workspace-artifact-card')).toBeTruthy();
        expect(screen.queryByTestId('artifact-doc-icon')).toBeNull();
        expect(screen.queryByTestId('artifact-preview-video')).toBeNull();
    });

    it('exposes the vault ref as a link', () => {
        render(<WorkspaceArtifactCard event={fixture({ ref: 'vault://abc' })} />);
        const link = screen.getByRole('link', { name: /open/i }) as HTMLAnchorElement;
        expect(link.href).toContain('vault://abc');
    });
});
