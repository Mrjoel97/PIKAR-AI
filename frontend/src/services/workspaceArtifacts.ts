// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import type { MessageMetadata } from '@/lib/chatMetadata';
import type { MarkdownReportKind, WidgetDefinition } from '@/types/widgets';

const LONGFORM_MIN_CHARS = 650;
const STRUCTURED_MIN_CHARS = 220;
const RESEARCH_MIN_CHARS = 180;
const TITLE_MAX_LENGTH = 88;
const MARKDOWN_TITLE_RE = /^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$/m;
const MARKDOWN_SIGNAL_RE = /(^|\n)\s*(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|\|.+\|)/m;
const LONGFORM_WIDGET_TYPES = new Set(['braindump_analysis', 'markdown_report']);

type ResearchMetadata = {
    topic?: string;
    researchType?: string;
    quickAnswer?: string;
    citations?: unknown[];
};

function normalizeMarkdown(text: string): string {
    return text.replace(/\r\n/g, '\n').trim();
}

function truncate(text: string, maxLength: number): string {
    return text.length > maxLength ? `${text.slice(0, maxLength - 1).trimEnd()}…` : text;
}

function stripMarkdown(value: string): string {
    return value
        .replace(/^#{1,6}\s+/g, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/[*_`~]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

function extractResearchMetadata(metadata?: MessageMetadata | null): ResearchMetadata | null {
    if (!metadata || typeof metadata !== 'object') return null;
    const candidate = (metadata as Record<string, unknown>).research;
    if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) return null;
    return candidate as ResearchMetadata;
}

function deriveKind(markdown: string, research: ResearchMetadata | null): MarkdownReportKind {
    if (research?.topic || research?.researchType) return 'research';
    if (/\banalysis\b/i.test(markdown)) return 'analysis';
    if (/\breport\b/i.test(markdown)) return 'report';
    return 'notes';
}

function deriveTitle(
    markdown: string,
    agentName?: string,
    research?: ResearchMetadata | null,
): string {
    const headingMatch = markdown.match(MARKDOWN_TITLE_RE);
    if (headingMatch?.[1]) {
        return truncate(stripMarkdown(headingMatch[1]), TITLE_MAX_LENGTH);
    }

    if (research?.topic) {
        const prefix = research.researchType
            ? research.researchType.replace(/_/g, ' ')
            : 'Research';
        return truncate(`${prefix.replace(/\b\w/g, (char) => char.toUpperCase())}: ${research.topic}`, TITLE_MAX_LENGTH);
    }

    const firstLine = markdown
        .split('\n')
        .map((line) => stripMarkdown(line))
        .find((line) => line.length > 0);
    if (firstLine) {
        return truncate(firstLine, TITLE_MAX_LENGTH);
    }

    return truncate(agentName ? `${agentName} report` : 'Agent report', TITLE_MAX_LENGTH);
}

export function shouldPromoteTextToWorkspaceArtifact(
    text: string,
    metadata?: MessageMetadata | null,
): boolean {
    const markdown = normalizeMarkdown(text);
    if (!markdown) return false;

    const research = extractResearchMetadata(metadata);
    const hasStructuredMarkdown = MARKDOWN_SIGNAL_RE.test(markdown);
    const nonEmptyLineCount = markdown.split('\n').filter((line) => line.trim().length > 0).length;

    if (research) {
        return markdown.length >= RESEARCH_MIN_CHARS;
    }

    return markdown.length >= LONGFORM_MIN_CHARS
        || (hasStructuredMarkdown && markdown.length >= STRUCTURED_MIN_CHARS)
        || nonEmptyLineCount >= 12;
}

export function hasLongformWorkspaceWidget(widget: WidgetDefinition | null | undefined): boolean {
    return Boolean(widget && LONGFORM_WIDGET_TYPES.has(widget.type));
}

export function buildMarkdownWorkspaceWidget(options: {
    text: string;
    sessionId: string;
    agentName?: string;
    metadata?: MessageMetadata | null;
}): WidgetDefinition | null {
    const markdown = normalizeMarkdown(options.text);
    if (!shouldPromoteTextToWorkspaceArtifact(markdown, options.metadata)) {
        return null;
    }

    const research = extractResearchMetadata(options.metadata);
    const title = deriveTitle(markdown, options.agentName, research);
    const summary = research?.quickAnswer ? truncate(research.quickAnswer.trim(), 240) : undefined;

    return {
        type: 'markdown_report',
        title,
        data: {
            markdown,
            title,
            agentName: options.agentName,
            summary,
            kind: deriveKind(markdown, research),
            sourceCount: Array.isArray(research?.citations) ? research.citations.length : undefined,
            generatedAt: new Date().toISOString(),
        },
        workspace: {
            mode: 'focus',
            sessionId: options.sessionId,
        },
    };
}
