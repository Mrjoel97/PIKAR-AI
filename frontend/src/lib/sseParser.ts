/**
 * Pure SSE event parser for the A2A streaming protocol.
 *
 * Extracts the event-parsing logic from useAgentChat's `executeSend` onmessage
 * handler into stateless, testable functions. All side-effects are described
 * declaratively in the returned `ParseResult` rather than executed inline.
 */

import type { TraceStep } from '@/hooks/useAgentChat';
import {
  extractMessageMetadataFromEvent,
  extractMessageMetadataFromParts,
  type MessageMetadata,
} from '@/lib/chatMetadata';
import { validateWidgetDefinition } from '@/types/widgets';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/** Mutable accumulator that tracks streaming state across SSE events. */
export interface SSEAccumulator {
  agentText: string;
  currentTraces: TraceStep[];
  currentWidget: unknown | null;
  agentName: string;
  isThinking: boolean;
  directorProgress: { step: string; total: number; current: number } | null;
  metadata: Record<string, unknown> | null;
  /** De-duplication set for director_progress stages. */
  seenProgressStages: Set<string>;
  /** Whether an error event has been received during this stream. */
  hasError: boolean;
  /** Interaction ID captured from the interaction_complete SSE event. */
  interactionId: string | null;
}

export interface ParsedSideEffect {
  type: 'save_widget' | 'focus_widget' | 'workspace_activity' | 'error_activity';
  payload: unknown;
}

/** Result of parsing a single SSE event. */
export interface ParseResult {
  /** New text fragment to append (null if no text in this event). */
  textDelta: string | null;
  /** Accumulated full text so far. */
  fullText: string;
  /** Raw widget data if a valid widget was found (pre-workspace-defaults). */
  widgetFound: unknown | null;
  /** Updated traces array. */
  traces: TraceStep[];
  /** Agent name if changed by this event, null otherwise. */
  agentName: string | null;
  /** Whether the agent is still "thinking" (no content yet). */
  isThinking: boolean;
  /** Metadata extracted from this event, if any. */
  metadata: MessageMetadata | null;
  /** Declarative side effects that should be executed by the caller. */
  sideEffects: ParsedSideEffect[];
  /** If the event was an error, the error text. */
  errorText: string | null;
  /** Whether this event was a ping / no-op. */
  skipped: boolean;
  /** Interaction ID from an interaction_complete event, null otherwise. */
  interactionId: string | null;
}

// ---------------------------------------------------------------------------
// Director progress stage labels (mirrored from useAgentChat)
// ---------------------------------------------------------------------------

const DIRECTOR_STAGE_LABELS: Record<string, string> = {
  planning_started: 'Planning storyboard',
  planning_done: 'Storyboard ready',
  assets_done: 'Scene assets generated',
  rendering_started: 'Rendering final video',
  completed: 'Video completed',
  failed: 'Video generation failed',
};

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create a fresh accumulator for a new streaming session.
 *
 * @param defaultAgentName - The display name to use when the author is
 *   ExecutiveAgent or not yet known.
 */
export function createAccumulator(defaultAgentName: string = 'Pikar AI'): SSEAccumulator {
  return {
    agentText: '',
    currentTraces: [],
    currentWidget: null,
    agentName: defaultAgentName,
    isThinking: true,
    directorProgress: null,
    metadata: null,
    seenProgressStages: new Set(),
    hasError: false,
    interactionId: null,
  };
}

// ---------------------------------------------------------------------------
// Core parser
// ---------------------------------------------------------------------------

/**
 * Parse a single SSE event payload and update the accumulator in place.
 *
 * This is a pure-ish function: it mutates `accumulator` for efficiency but
 * returns a `ParseResult` that the caller can use to decide what React state
 * updates or DOM side effects to perform.
 *
 * @param eventData - The raw `event.data` string from the SSE message.
 * @param accumulator - The mutable accumulator tracking this stream.
 * @param defaultAgentName - Fallback display name for ExecutiveAgent.
 * @returns A ParseResult describing what changed.
 */
export function parseSSEEvent(
  eventData: string,
  accumulator: SSEAccumulator,
  defaultAgentName: string = 'Pikar AI',
): ParseResult {
  const result: ParseResult = {
    textDelta: null,
    fullText: accumulator.agentText,
    widgetFound: null,
    traces: accumulator.currentTraces,
    agentName: null,
    isThinking: accumulator.isThinking,
    metadata: null,
    sideEffects: [],
    errorText: null,
    skipped: false,
    interactionId: null,
  };

  // ------- Parse JSON -------
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(eventData) as Record<string, unknown>;
  } catch {
    // Malformed JSON — skip silently (matches existing console.error behaviour
    // but the caller can log if desired).
    result.skipped = true;
    return result;
  }

  // ------- Interaction complete (feedback loop) -------
  if (data.type === 'interaction_complete') {
    const iid = typeof data.interaction_id === 'string' ? data.interaction_id : null;
    accumulator.interactionId = iid;
    result.interactionId = iid;
    return result;
  }

  // ------- Director progress -------
  if (data.event_type === 'director_progress') {
    const stage = typeof data.stage === 'string' ? data.stage : 'unknown';
    const label = DIRECTOR_STAGE_LABELS[stage] || `Progress: ${stage}`;
    const payload = data.payload as Record<string, unknown> | undefined;
    const payloadText =
      payload && Object.keys(payload).length > 0 ? ` (${JSON.stringify(payload)})` : '';
    const traceContent = `${label}${payloadText}`;
    const dedupeKey = `${stage}:${payloadText}`;

    if (!accumulator.seenProgressStages.has(dedupeKey)) {
      accumulator.seenProgressStages.add(dedupeKey);
      const trace: TraceStep = {
        type: stage === 'completed' || stage === 'failed' ? 'tool_output' : 'tool_use',
        toolName: 'AI Director',
        content: traceContent,
      };
      accumulator.currentTraces.push(trace);
      result.traces = [...accumulator.currentTraces];
    }

    // Director progress events carry no text / widget / author — return early.
    return result;
  }

  // ------- Error -------
  if (data.error) {
    accumulator.hasError = true;
    const errorText =
      typeof data.error === 'string'
        ? data.error
        : 'Agent encountered an internal error. Please try again.';
    result.errorText = errorText;

    result.sideEffects.push({
      type: 'error_activity',
      payload: {
        agentName: accumulator.agentName,
        text: errorText,
        traces: [...accumulator.currentTraces],
      },
    });
    return result;
  }

  // ------- Author -------
  if (data.author && data.author !== 'user' && data.author !== 'system') {
    const rawAuthor = data.author as string;
    const resolvedName = rawAuthor === 'ExecutiveAgent' ? defaultAgentName : rawAuthor;
    if (resolvedName !== accumulator.agentName) {
      accumulator.agentName = resolvedName;
      result.agentName = resolvedName;
    }
  }

  // ------- Content parts -------
  let newText = '';
  if (
    data.content &&
    typeof data.content === 'object' &&
    !Array.isArray(data.content) &&
    (data.content as Record<string, unknown>).parts
  ) {
    const parts = (data.content as Record<string, unknown>).parts as unknown[];

    // Metadata from parts
    const extractedMetadata = extractMessageMetadataFromParts(parts);
    if (extractedMetadata) {
      accumulator.metadata = extractedMetadata;
      result.metadata = extractedMetadata;
    }

    for (const part of parts) {
      if (!part || typeof part !== 'object') continue;
      const p = part as Record<string, unknown>;

      // Text
      if (typeof p.text === 'string') {
        newText += p.text;
      }

      // Widget in part
      if (p.widget && validateWidgetDefinition(p.widget)) {
        accumulator.currentWidget = p.widget;
        result.widgetFound = p.widget;
      }

      // Widget in functionResponse / function_response
      const fr =
        (p.function_response as Record<string, unknown> | undefined) ??
        (p.functionResponse as Record<string, unknown> | undefined);
      if (fr && !accumulator.currentWidget) {
        const response = (fr.response ?? fr.response_data) as
          | Record<string, unknown>
          | undefined;
        let candidate: Record<string, unknown> | undefined =
          typeof response === 'object' && response !== null ? response : undefined;
        if (
          candidate &&
          typeof candidate.result === 'object' &&
          candidate.result !== null
        ) {
          candidate = candidate.result as Record<string, unknown>;
        }
        if (candidate && validateWidgetDefinition(candidate)) {
          accumulator.currentWidget = candidate;
          result.widgetFound = candidate;
        }
      }
    }
  } else if (typeof data.content === 'string') {
    newText = data.content;
  }

  // Fallback metadata from event
  if (!accumulator.metadata) {
    const eventMeta = extractMessageMetadataFromEvent(data);
    if (eventMeta) {
      accumulator.metadata = eventMeta;
      result.metadata = eventMeta;
    }
  }

  // ------- Top-level widget field -------
  if (data.widget && validateWidgetDefinition(data.widget)) {
    accumulator.currentWidget = data.widget;
    result.widgetFound = data.widget;
  }

  // ------- Widget side effects -------
  if (accumulator.currentWidget) {
    result.sideEffects.push({
      type: 'save_widget',
      payload: accumulator.currentWidget,
    });
    result.sideEffects.push({
      type: 'focus_widget',
      payload: accumulator.currentWidget,
    });
  }

  // ------- Custom events (tool traces) -------
  if (data.custom_event && typeof data.custom_event === 'object') {
    const customEvent = data.custom_event as Record<string, unknown>;
    if (customEvent.type === 'tool_call') {
      accumulator.currentTraces.push({
        type: 'tool_use',
        toolName: customEvent.name as string,
        content: JSON.stringify(customEvent.input),
      });
    } else if (customEvent.type === 'tool_result') {
      accumulator.currentTraces.push({
        type: 'tool_output',
        toolName: customEvent.name as string,
        content: 'Completed',
      });
    }
  }

  // ------- Status trace -------
  if (typeof data.status === 'string') {
    accumulator.currentTraces.push({
      type: 'thinking',
      content: data.status,
    });
  }

  // ------- Text accumulation -------
  if (newText) {
    accumulator.agentText += newText;
    result.textDelta = newText;
    result.fullText = accumulator.agentText;
  }

  // ------- Thinking state -------
  const hasContent = Boolean(
    accumulator.agentText || accumulator.currentWidget || accumulator.currentTraces.length > 0,
  );
  accumulator.isThinking = !hasContent;
  result.isThinking = !hasContent;

  // ------- Workspace activity -------
  result.sideEffects.push({
    type: 'workspace_activity',
    payload: {
      agentName: accumulator.agentName,
      text: accumulator.agentText || undefined,
      traces: [...accumulator.currentTraces],
    },
  });

  result.traces = [...accumulator.currentTraces];
  return result;
}
