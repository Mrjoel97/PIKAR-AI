// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { createAccumulator, parseSSEEvent } from '@/lib/sseParser';

describe('sseParser – interaction_complete event', () => {
  it('createAccumulator initializes interactionId as null', () => {
    const acc = createAccumulator('TestAgent');
    expect(acc.interactionId).toBeNull();
  });

  it('sets result.interactionId and accumulator.interactionId from interaction_complete event', () => {
    const acc = createAccumulator('TestAgent');
    const eventData = JSON.stringify({
      type: 'interaction_complete',
      interaction_id: 'uuid-123',
    });

    const result = parseSSEEvent(eventData, acc, 'TestAgent');

    expect(result.interactionId).toBe('uuid-123');
    expect(acc.interactionId).toBe('uuid-123');
    expect(result.skipped).toBe(false);
  });

  it('sets interactionId to null when interaction_id is null in the event', () => {
    const acc = createAccumulator('TestAgent');
    const eventData = JSON.stringify({
      type: 'interaction_complete',
      interaction_id: null,
    });

    const result = parseSSEEvent(eventData, acc, 'TestAgent');

    expect(result.interactionId).toBeNull();
    expect(acc.interactionId).toBeNull();
  });

  it('does NOT set interactionId for normal content events', () => {
    const acc = createAccumulator('TestAgent');
    const eventData = JSON.stringify({
      content: { parts: [{ text: 'Hello world' }] },
      author: 'TestAgent',
    });

    const result = parseSSEEvent(eventData, acc, 'TestAgent');

    expect(result.interactionId).toBeNull();
    expect(acc.interactionId).toBeNull();
  });
});
