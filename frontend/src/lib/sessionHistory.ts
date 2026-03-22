/**
 * Standalone utility to load and reconstruct session chat history from Supabase.
 *
 * Extracted from `useAgentChat.loadHistory` so that multiple consumers
 * (useSessionPreload, cold-switch, rewritten useAgentChat) can call it
 * without depending on React state or hooks.
 */

import { createClient } from '@/lib/supabase/client';
import { extractMessageMetadataFromEvent } from '@/lib/chatMetadata';
import { WidgetDefinition, validateWidgetDefinition } from '@/types/widgets';
import type { Message, SessionEvent } from '@/hooks/useAgentChat';

/**
 * Apply workspace defaults to a widget definition.
 * Morning briefing widgets are returned as-is; all others default to focus mode.
 */
function withWorkspaceDefaults(widget: WidgetDefinition): WidgetDefinition {
  if (widget.type === 'morning_briefing') return widget;
  return {
    ...widget,
    workspace: {
      ...widget.workspace,
      mode: widget.workspace?.mode ?? 'focus',
    },
  };
}

/**
 * Load session history from Supabase and reconstruct a Message array.
 *
 * This is a pure async function with no React dependencies. It queries
 * `session_events`, parses ADK event payloads, validates widgets, and
 * returns the reconstructed message list.
 *
 * @param sessionId  - The session to load
 * @param userId     - The authenticated user's ID
 * @param appName    - ADK app name filter (defaults to 'agents')
 * @returns Reconstructed messages, or an empty array if nothing is found
 */
export async function loadSessionHistory(
  sessionId: string,
  userId: string,
  appName: string = 'agents',
): Promise<Message[]> {
  const supabase = createClient();

  const { data: events, error } = await supabase
    .from('session_events')
    .select('*')
    .eq('session_id', sessionId)
    .eq('app_name', appName)
    .eq('user_id', userId)
    .is('superseded_by', null)
    .order('event_index', { ascending: true });

  if (error) {
    console.error('[sessionHistory] Failed to query session_events:', error);
    return [];
  }

  if (!events || events.length === 0) {
    return [];
  }

  const historyMessages: Message[] = [];

  events.forEach((eventRow: SessionEvent) => {
    const event = eventRow.event_data || {};
    const who = event?.author ?? event?.source;

    // --- User messages ---
    if (who === 'user') {
      let text = '';
      if (event.content?.parts) {
        text = event.content.parts.map((p: any) => p.text || '').join('');
      } else if (typeof event.content === 'string') {
        text = event.content;
      }
      historyMessages.push({ id: eventRow.id, role: 'user', text });
      return;
    }

    // --- Agent / model messages ---
    if (who === 'model' || who === 'agent' || (who && who !== 'system')) {
      let text = '';
      let widget: WidgetDefinition | undefined;

      if (event.content?.parts) {
        event.content.parts.forEach((p: any) => {
          if (p.text) text += p.text;

          // Widget directly in part
          if (p.widget && validateWidgetDefinition(p.widget)) {
            widget = withWorkspaceDefaults(p.widget as WidgetDefinition);
          }

          // Widget buried in function_response
          const fr =
            p?.function_response ??
            (p as { functionResponse?: { response?: unknown; response_data?: unknown } })
              .functionResponse;
          if (fr && !widget) {
            const response = (fr as any).response ?? (fr as any).response_data;
            let candidate =
              typeof response === 'object' && response !== null
                ? (response as Record<string, unknown>)
                : undefined;
            if (candidate && typeof candidate.result === 'object' && candidate.result !== null) {
              candidate = candidate.result as Record<string, unknown>;
            }
            if (candidate && validateWidgetDefinition(candidate)) {
              widget = withWorkspaceDefaults(candidate as WidgetDefinition);
            }
          }
        });
      } else if (typeof event.content === 'string') {
        text = event.content;
      }

      // Top-level widget field on the event
      if (event.widget && validateWidgetDefinition(event.widget)) {
        widget = withWorkspaceDefaults(event.widget as WidgetDefinition);
      }

      const metadata = extractMessageMetadataFromEvent(event);
      const displayName = who === 'ExecutiveAgent' ? undefined : who;

      historyMessages.push({
        id: eventRow.id,
        role: 'agent',
        text: text || undefined,
        agentName: displayName,
        widget,
        metadata,
      });
    }
  });

  return historyMessages;
}
