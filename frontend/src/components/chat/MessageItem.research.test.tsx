// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { MessageItem } from './MessageItem';

vi.mock('@/components/widgets/WidgetRegistry', () => ({
  WidgetContainer: () => <div data-testid="widget-container" />,
}));

vi.mock('@/components/chat/ThoughtProcess', () => ({
  ThoughtProcess: () => <div data-testid="thought-process" />,
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
});
