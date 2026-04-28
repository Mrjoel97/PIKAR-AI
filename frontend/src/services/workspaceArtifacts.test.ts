// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, expect, it } from 'vitest';

import {
    buildMarkdownWorkspaceWidget,
    hasLongformWorkspaceWidget,
    shouldPromoteTextToWorkspaceArtifact,
} from './workspaceArtifacts';

describe('workspaceArtifacts', () => {
    it('promotes structured research responses into markdown workspace widgets', () => {
        const widget = buildMarkdownWorkspaceWidget({
            text: [
                '# AI Workflow Automation',
                '',
                '## Executive Summary',
                '',
                'This market is expanding quickly across operations, marketing, and internal tooling.',
                '',
                '## Findings',
                '',
                '- Buyers want measurable time savings.',
                '- Vendors are differentiating on orchestration and auditability.',
                '- Mid-market teams still struggle with fragmented tooling.',
            ].join('\n'),
            sessionId: 'session-1',
            agentName: 'ResearchAgent',
            metadata: {
                research: {
                    topic: 'AI workflow automation',
                    researchType: 'market_research',
                    quickAnswer: 'Demand is rising, especially where teams need repeatable automations.',
                    citations: [{ url: 'https://example.com/1' }, { url: 'https://example.com/2' }],
                },
            },
        });

        expect(widget).not.toBeNull();
        expect(widget?.type).toBe('markdown_report');
        expect(widget?.title).toContain('AI Workflow Automation');
        expect((widget?.data as Record<string, unknown>).kind).toBe('research');
        expect((widget?.data as Record<string, unknown>).sourceCount).toBe(2);
    });

    it('ignores short conversational replies', () => {
        expect(
            shouldPromoteTextToWorkspaceArtifact('Here is the quick answer. Let me know if you want more detail.'),
        ).toBe(false);
    });

    it('recognizes existing long-form workspace widget types', () => {
        expect(
            hasLongformWorkspaceWidget({
                type: 'markdown_report',
                title: 'Report',
                data: {
                    markdown: '# Report',
                    title: 'Report',
                },
            }),
        ).toBe(true);
    });
});
