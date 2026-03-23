// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from 'vitest'
import {
  createAccumulator,
  parseSSEEvent,
  type SSEAccumulator,
} from '@/lib/sseParser'

describe('sseParser', () => {
  let acc: SSEAccumulator

  beforeEach(() => {
    acc = createAccumulator('Pikar AI')
  })

  // -------------------------------------------------------------------------
  // createAccumulator
  // -------------------------------------------------------------------------
  describe('createAccumulator', () => {
    it('returns a fresh accumulator with default values', () => {
      expect(acc.agentText).toBe('')
      expect(acc.currentTraces).toEqual([])
      expect(acc.currentWidget).toBeNull()
      expect(acc.agentName).toBe('Pikar AI')
      expect(acc.isThinking).toBe(true)
      expect(acc.metadata).toBeNull()
      expect(acc.seenProgressStages).toBeInstanceOf(Set)
      expect(acc.hasError).toBe(false)
    })

    it('accepts a custom default agent name', () => {
      const custom = createAccumulator('Custom Bot')
      expect(custom.agentName).toBe('Custom Bot')
    })
  })

  // -------------------------------------------------------------------------
  // Text parsing
  // -------------------------------------------------------------------------
  describe('text events', () => {
    it('parses text from content.parts and returns textDelta', () => {
      const event = JSON.stringify({
        author: 'ExecutiveAgent',
        content: { parts: [{ text: 'Hello world' }] },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.textDelta).toBe('Hello world')
      expect(result.fullText).toBe('Hello world')
      expect(result.isThinking).toBe(false)
      expect(acc.agentText).toBe('Hello world')
    })

    it('parses text from string content', () => {
      const event = JSON.stringify({
        content: 'simple string content',
      })
      const result = parseSSEEvent(event, acc)

      expect(result.textDelta).toBe('simple string content')
      expect(result.fullText).toBe('simple string content')
    })

    it('accumulates text across multiple events', () => {
      parseSSEEvent(
        JSON.stringify({ content: { parts: [{ text: 'Hello ' }] } }),
        acc,
      )
      const result = parseSSEEvent(
        JSON.stringify({ content: { parts: [{ text: 'world' }] } }),
        acc,
      )

      expect(result.textDelta).toBe('world')
      expect(result.fullText).toBe('Hello world')
      expect(acc.agentText).toBe('Hello world')
    })

    it('concatenates multiple text parts within one event', () => {
      const event = JSON.stringify({
        content: { parts: [{ text: 'Part1 ' }, { text: 'Part2' }] },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.textDelta).toBe('Part1 Part2')
      expect(result.fullText).toBe('Part1 Part2')
    })

    it('returns null textDelta when event has no text', () => {
      const event = JSON.stringify({
        status: 'Processing...',
      })
      const result = parseSSEEvent(event, acc)

      expect(result.textDelta).toBeNull()
    })
  })

  // -------------------------------------------------------------------------
  // Malformed / edge-case events
  // -------------------------------------------------------------------------
  describe('malformed events', () => {
    it('handles empty string gracefully', () => {
      const result = parseSSEEvent('', acc)
      expect(result.skipped).toBe(true)
      expect(result.textDelta).toBeNull()
    })

    it('handles invalid JSON gracefully', () => {
      const result = parseSSEEvent('not-json{{{', acc)
      expect(result.skipped).toBe(true)
    })

    it('handles event with null content', () => {
      const event = JSON.stringify({ content: null })
      const result = parseSSEEvent(event, acc)
      expect(result.textDelta).toBeNull()
      expect(result.skipped).toBe(false)
    })

    it('handles event with empty parts array', () => {
      const event = JSON.stringify({ content: { parts: [] } })
      const result = parseSSEEvent(event, acc)
      expect(result.textDelta).toBeNull()
    })
  })

  // -------------------------------------------------------------------------
  // Agent name resolution
  // -------------------------------------------------------------------------
  describe('agent name', () => {
    it('resolves ExecutiveAgent to the default agent name', () => {
      const event = JSON.stringify({
        author: 'ExecutiveAgent',
        content: { parts: [{ text: 'Hi' }] },
      })
      const result = parseSSEEvent(event, acc, 'Pikar AI')

      expect(result.agentName).toBeNull() // no change — already default
      expect(acc.agentName).toBe('Pikar AI')
    })

    it('uses raw author name for non-Executive agents', () => {
      const event = JSON.stringify({
        author: 'FinancialAgent',
        content: { parts: [{ text: 'Numbers' }] },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.agentName).toBe('FinancialAgent')
      expect(acc.agentName).toBe('FinancialAgent')
    })

    it('ignores user and system authors', () => {
      parseSSEEvent(JSON.stringify({ author: 'user' }), acc)
      expect(acc.agentName).toBe('Pikar AI')

      parseSSEEvent(JSON.stringify({ author: 'system' }), acc)
      expect(acc.agentName).toBe('Pikar AI')
    })
  })

  // -------------------------------------------------------------------------
  // Error handling
  // -------------------------------------------------------------------------
  describe('error events', () => {
    it('sets errorText for string errors', () => {
      const event = JSON.stringify({ error: 'Something went wrong' })
      const result = parseSSEEvent(event, acc)

      expect(result.errorText).toBe('Something went wrong')
      expect(acc.hasError).toBe(true)
    })

    it('provides default error message for non-string errors', () => {
      const event = JSON.stringify({ error: { code: 500 } })
      const result = parseSSEEvent(event, acc)

      expect(result.errorText).toBe(
        'Agent encountered an internal error. Please try again.',
      )
      expect(acc.hasError).toBe(true)
    })

    it('emits error_activity side effect', () => {
      const event = JSON.stringify({ error: 'oops' })
      const result = parseSSEEvent(event, acc)

      const errorEffect = result.sideEffects.find(
        (e) => e.type === 'error_activity',
      )
      expect(errorEffect).toBeDefined()
    })
  })

  // -------------------------------------------------------------------------
  // Director progress
  // -------------------------------------------------------------------------
  describe('director progress', () => {
    it('adds trace for director_progress events', () => {
      const event = JSON.stringify({
        event_type: 'director_progress',
        stage: 'planning_started',
        payload: { scene_count: 4 },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.traces).toHaveLength(1)
      expect(result.traces[0].toolName).toBe('AI Director')
      expect(result.traces[0].content).toContain('Planning storyboard')
      expect(result.traces[0].type).toBe('tool_use')
    })

    it('uses tool_output type for completed/failed stages', () => {
      const event = JSON.stringify({
        event_type: 'director_progress',
        stage: 'completed',
        payload: {},
      })
      const result = parseSSEEvent(event, acc)

      expect(result.traces[0].type).toBe('tool_output')
    })

    it('deduplicates identical progress events', () => {
      const event = JSON.stringify({
        event_type: 'director_progress',
        stage: 'rendering_started',
        payload: {},
      })
      parseSSEEvent(event, acc)
      parseSSEEvent(event, acc)

      expect(acc.currentTraces).toHaveLength(1)
    })

    it('handles unknown stage gracefully', () => {
      const event = JSON.stringify({
        event_type: 'director_progress',
        stage: 'some_new_stage',
        payload: {},
      })
      const result = parseSSEEvent(event, acc)

      expect(result.traces[0].content).toContain('Progress: some_new_stage')
    })
  })

  // -------------------------------------------------------------------------
  // Widget extraction
  // -------------------------------------------------------------------------
  describe('widgets', () => {
    const validWidget = {
      type: 'table',
      data: { columns: [{ key: 'a', label: 'A' }], rows: [] },
    }

    it('extracts widget from content.parts[].widget', () => {
      const event = JSON.stringify({
        content: { parts: [{ widget: validWidget }] },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.widgetFound).toEqual(validWidget)
      expect(acc.currentWidget).toEqual(validWidget)
    })

    it('extracts widget from top-level widget field', () => {
      const event = JSON.stringify({ widget: validWidget })
      const result = parseSSEEvent(event, acc)

      expect(result.widgetFound).toEqual(validWidget)
    })

    it('extracts widget from functionResponse', () => {
      const event = JSON.stringify({
        content: {
          parts: [
            {
              functionResponse: {
                response: validWidget,
              },
            },
          ],
        },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.widgetFound).toEqual(validWidget)
    })

    it('extracts widget from nested function_response.result', () => {
      const event = JSON.stringify({
        content: {
          parts: [
            {
              function_response: {
                response: { result: validWidget },
              },
            },
          ],
        },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.widgetFound).toEqual(validWidget)
    })

    it('emits save_widget and focus_widget side effects', () => {
      const event = JSON.stringify({
        content: { parts: [{ widget: validWidget }] },
      })
      const result = parseSSEEvent(event, acc)

      const save = result.sideEffects.find((e) => e.type === 'save_widget')
      const focus = result.sideEffects.find((e) => e.type === 'focus_widget')
      expect(save).toBeDefined()
      expect(focus).toBeDefined()
    })

    it('ignores invalid widget definitions', () => {
      const event = JSON.stringify({
        content: { parts: [{ widget: { type: 'invalid_type', data: {} } }] },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.widgetFound).toBeNull()
    })
  })

  // -------------------------------------------------------------------------
  // Tool traces
  // -------------------------------------------------------------------------
  describe('custom events (tool traces)', () => {
    it('tracks tool_call trace', () => {
      const event = JSON.stringify({
        custom_event: {
          type: 'tool_call',
          name: 'get_calendar',
          input: { date: '2025-01-01' },
        },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.traces).toHaveLength(1)
      expect(result.traces[0].type).toBe('tool_use')
      expect(result.traces[0].toolName).toBe('get_calendar')
    })

    it('tracks tool_result trace', () => {
      const event = JSON.stringify({
        custom_event: {
          type: 'tool_result',
          name: 'get_calendar',
        },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.traces).toHaveLength(1)
      expect(result.traces[0].type).toBe('tool_output')
      expect(result.traces[0].content).toBe('Completed')
    })
  })

  // -------------------------------------------------------------------------
  // Status traces
  // -------------------------------------------------------------------------
  describe('status traces', () => {
    it('adds a thinking trace for status strings', () => {
      const event = JSON.stringify({ status: 'Processing request...' })
      const result = parseSSEEvent(event, acc)

      expect(result.traces).toHaveLength(1)
      expect(result.traces[0].type).toBe('thinking')
      expect(result.traces[0].content).toBe('Processing request...')
    })
  })

  // -------------------------------------------------------------------------
  // isThinking state
  // -------------------------------------------------------------------------
  describe('isThinking', () => {
    it('starts as true and becomes false when text arrives', () => {
      expect(acc.isThinking).toBe(true)

      const event = JSON.stringify({
        content: { parts: [{ text: 'Data' }] },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.isThinking).toBe(false)
      expect(acc.isThinking).toBe(false)
    })

    it('becomes false when traces arrive (even without text)', () => {
      const event = JSON.stringify({ status: 'Working...' })
      const result = parseSSEEvent(event, acc)

      expect(result.isThinking).toBe(false)
    })

    it('becomes false when a widget arrives', () => {
      const event = JSON.stringify({
        content: {
          parts: [
            {
              widget: {
                type: 'table',
                data: { columns: [], rows: [] },
              },
            },
          ],
        },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.isThinking).toBe(false)
    })
  })

  // -------------------------------------------------------------------------
  // Workspace activity side effect
  // -------------------------------------------------------------------------
  describe('workspace_activity side effect', () => {
    it('always emits workspace_activity for non-error, non-director events', () => {
      const event = JSON.stringify({
        content: { parts: [{ text: 'Hello' }] },
      })
      const result = parseSSEEvent(event, acc)

      const activity = result.sideEffects.find(
        (e) => e.type === 'workspace_activity',
      )
      expect(activity).toBeDefined()
      expect((activity!.payload as Record<string, unknown>).text).toBe('Hello')
    })
  })

  // -------------------------------------------------------------------------
  // Metadata extraction
  // -------------------------------------------------------------------------
  describe('metadata', () => {
    it('extracts metadata from content parts', () => {
      const event = JSON.stringify({
        content: {
          parts: [
            { text: 'info', metadata: { confidence: 0.9 } },
          ],
        },
      })
      const result = parseSSEEvent(event, acc)

      expect(result.metadata).toEqual({ confidence: 0.9 })
    })

    it('falls back to event-level metadata', () => {
      const event = JSON.stringify({
        content: { parts: [{ text: 'Hi' }] },
        metadata: { agent: 'test' },
      })
      // First call — parts have no metadata, so fallback kicks in
      // But extractMessageMetadataFromParts returns undefined for parts without metadata field,
      // so the event-level metadata should be picked up.
      const result = parseSSEEvent(event, acc)

      expect(result.metadata).toEqual({ agent: 'test' })
    })
  })
})
