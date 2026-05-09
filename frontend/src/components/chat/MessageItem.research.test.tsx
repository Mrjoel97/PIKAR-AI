// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { MessageItem } from './MessageItem';

// Helper to build the props common to all research-card test cases.
function renderResearch(research: Record<string, unknown> | undefined) {
  return render(
    <MessageItem
      msg={{
        role: 'agent',
        text: 'Research complete.',
        agentName: 'ExecutiveAgent',
        metadata: research === undefined ? undefined : { research },
      }}
      index={0}
      onToggleWidgetMinimized={() => undefined}
      onWidgetAction={() => undefined}
      onWidgetDismiss={() => undefined}
    />
  );
}

vi.mock('@/components/widgets/WidgetRegistry', () => ({
  WidgetContainer: () => <div data-testid="widget-container" />,
}));

vi.mock('@/components/chat/ThoughtProcess', () => ({
  ThoughtProcess: () => <div data-testid="thought-process" />,
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe('MessageItem research metadata', () => {
  it('renders confidence, citations, contradictions, and next questions', () => {
    render(
      <MessageItem
        msg={{
          role: 'agent',
          text: 'Research complete.',
          agentName: 'ExecutiveAgent',
          metadata: {
            research: {
              topic: 'AI copilots for SMBs',
              researchType: 'market',
              confidenceScore: 0.82,
              quickAnswer: 'Demand is growing across SMB operations.',
              citations: [
                {
                  title: 'Example Source',
                  url: 'https://example.com/source',
                  snippet: 'Useful market evidence.',
                },
              ],
              contradictions: ['Two sources disagree on exact market size.'],
              recommendedNextQuestions: ['What changed most recently in 2025 and 2026?'],
              keyFindings: ['SMB adoption is increasing.'],
            },
          },
        }}
        index={0}
        onToggleWidgetMinimized={() => undefined}
        onWidgetAction={() => undefined}
        onWidgetDismiss={() => undefined}
      />
    );

    expect(screen.getByText('82% confidence')).toBeTruthy();
    expect(screen.getByText('Top citations')).toBeTruthy();
    expect(screen.getByText('Example Source')).toBeTruthy();
    expect(screen.getByText('Potential contradictions')).toBeTruthy();
    expect(screen.getByText(/What changed most recently/)).toBeTruthy();
  });

  it('renders the Conflicting sources section when research.conflicts is non-empty', () => {
    renderResearch({
      topic: 'AI copilots',
      researchType: 'market',
      confidenceScore: 0.7,
      citations: [],
      contradictions: [],
      recommendedNextQuestions: [],
      conflicts: [
        {
          claim: 'Adoption costs remain a major barrier.',
          source_a_id: 2,
          source_a_title: 'Adoption Costs Report',
          source_a_url: 'https://example.com/b',
          source_a_excerpt: 'Costs are still the top blocker for SMBs.',
          source_b_id: 1,
          source_b_title: 'AI in the Enterprise',
          source_b_url: 'https://example.com/a',
          source_b_excerpt: 'AI agents are reshaping enterprise workflows.',
        },
        {
          claim: 'Second conflicting claim.',
          source_a_id: 3,
          source_a_title: 'Source Three',
          source_a_url: '',
          source_a_excerpt: '',
          source_b_id: 4,
          source_b_title: 'Source Four',
          source_b_url: '',
          source_b_excerpt: '',
        },
      ],
    });

    expect(screen.getByText('Conflicting sources')).toBeTruthy();
    // Count badge.
    expect(screen.getByText('2')).toBeTruthy();
    // Each conflict has a claim line.
    expect(screen.getByText('Adoption costs remain a major barrier.')).toBeTruthy();
    expect(screen.getByText('Second conflicting claim.')).toBeTruthy();
    // Side-by-side source labels appear (one per card per conflict).
    const sourceALabels = screen.getAllByText('Source A');
    const sourceBLabels = screen.getAllByText('Source B');
    expect(sourceALabels.length).toBe(2);
    expect(sourceBLabels.length).toBe(2);
    // Source titles render.
    expect(screen.getByText('Adoption Costs Report')).toBeTruthy();
    expect(screen.getByText('AI in the Enterprise')).toBeTruthy();
    // Conflict cards exist as data-testid.
    expect(screen.getAllByTestId('research-conflict').length).toBe(2);
  });

  it('hides the Conflicting sources section when conflicts is missing or empty', () => {
    // Missing conflicts field entirely (older agent runs without Phase 99 backend).
    const { unmount } = renderResearch({
      topic: 'old run',
      researchType: 'market',
      confidenceScore: 0.5,
      citations: [],
      contradictions: [],
      recommendedNextQuestions: [],
      // no conflicts field
    });
    expect(screen.queryByText('Conflicting sources')).toBeNull();
    unmount();

    // Empty conflicts array.
    renderResearch({
      topic: 'no conflicts',
      researchType: 'market',
      confidenceScore: 0.9,
      citations: [],
      contradictions: [],
      recommendedNextQuestions: [],
      conflicts: [],
    });
    expect(screen.queryByText('Conflicting sources')).toBeNull();
  });
});
