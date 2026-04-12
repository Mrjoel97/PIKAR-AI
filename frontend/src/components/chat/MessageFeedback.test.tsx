// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetchWithAuth before importing the component
vi.mock('@/services/api', () => ({
  fetchWithAuth: vi.fn(() => Promise.resolve(new Response(JSON.stringify({ ok: true })))),
}));

import { MessageFeedback } from '@/components/chat/MessageFeedback';
import { MessageItem } from '@/components/chat/MessageItem';
import { fetchWithAuth } from '@/services/api';
import type { Message } from '@/hooks/useAgentChat';

const mockedFetch = vi.mocked(fetchWithAuth);

describe('MessageFeedback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders two buttons (thumbs-up, thumbs-down) when interactionId is provided', () => {
    render(<MessageFeedback interactionId="uuid-abc" />);

    const positiveBtn = screen.getByRole('button', { name: /rate positive/i });
    const negativeBtn = screen.getByRole('button', { name: /rate negative/i });

    expect(positiveBtn).toBeTruthy();
    expect(negativeBtn).toBeTruthy();
  });

  it('renders nothing when interactionId is undefined', () => {
    const { container } = render(<MessageFeedback interactionId={undefined as unknown as string} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders nothing when interactionId is null', () => {
    const { container } = render(<MessageFeedback interactionId={null as unknown as string} />);
    expect(container.innerHTML).toBe('');
  });

  it('clicking thumbs-down immediately shows selected state (aria-pressed="true") before API resolves', () => {
    // Make API never resolve during this test
    mockedFetch.mockReturnValue(new Promise(() => {}));

    render(<MessageFeedback interactionId="uuid-abc" />);

    const negativeBtn = screen.getByRole('button', { name: /rate negative/i });
    expect(negativeBtn.getAttribute('aria-pressed')).toBe('false');

    fireEvent.click(negativeBtn);

    // Optimistic: pressed immediately without waiting for API
    expect(negativeBtn.getAttribute('aria-pressed')).toBe('true');
  });

  it('clicking thumbs-down calls fetchWithAuth with POST to correct endpoint and rating=negative body', async () => {
    render(<MessageFeedback interactionId="uuid-abc" />);

    const negativeBtn = screen.getByRole('button', { name: /rate negative/i });
    fireEvent.click(negativeBtn);

    await waitFor(() => {
      expect(mockedFetch).toHaveBeenCalledWith(
        '/self-improvement/interactions/uuid-abc/feedback',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ rating: 'negative' }),
        }),
      );
    });
  });

  it('clicking thumbs-up after thumbs-down switches selection to thumbs-up (only one active at a time)', async () => {
    render(<MessageFeedback interactionId="uuid-abc" />);

    const positiveBtn = screen.getByRole('button', { name: /rate positive/i });
    const negativeBtn = screen.getByRole('button', { name: /rate negative/i });

    fireEvent.click(negativeBtn);
    expect(negativeBtn.getAttribute('aria-pressed')).toBe('true');
    expect(positiveBtn.getAttribute('aria-pressed')).toBe('false');

    fireEvent.click(positiveBtn);
    expect(positiveBtn.getAttribute('aria-pressed')).toBe('true');
    expect(negativeBtn.getAttribute('aria-pressed')).toBe('false');
  });
});

describe('MessageItem + MessageFeedback integration', () => {
  const defaultProps = {
    index: 0,
    onToggleWidgetMinimized: vi.fn(),
    onWidgetAction: vi.fn(),
    onWidgetDismiss: vi.fn(),
  };

  it('renders MessageFeedback for agent messages with interactionId', () => {
    const agentMsg: Message = {
      id: 'agent-1',
      role: 'agent',
      text: 'Hello there',
      agentName: 'TestAgent',
      interactionId: 'uuid-xyz',
      isThinking: false,
    };

    render(<MessageItem msg={agentMsg} {...defaultProps} />);

    expect(screen.getByRole('button', { name: /rate positive/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /rate negative/i })).toBeTruthy();
  });

  it('does NOT render MessageFeedback for user messages', () => {
    const userMsg: Message = {
      id: 'user-1',
      role: 'user',
      text: 'Hello',
    };

    render(<MessageItem msg={userMsg} {...defaultProps} />);

    expect(screen.queryByRole('button', { name: /rate positive/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /rate negative/i })).toBeNull();
  });
});
