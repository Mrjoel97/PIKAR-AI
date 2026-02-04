import { useState, useCallback, useRef, useEffect } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { createClient } from '@/lib/supabase/client';
import { WidgetDefinition, validateWidgetDefinition } from '@/types/widgets';

/**
 * Chat message representing user input, agent response, or system notification.
 * Messages can optionally contain a widget for interactive UI display.
 */
export type Message = {
  role: 'user' | 'agent' | 'system';
  /** Text content - optional when message is widget-only */
  text?: string;
  /** Agent-generated widget definition */
  widget?: WidgetDefinition;
  /** Name of the agent that generated this message */
  agentName?: string;
  /** Indicates agent is still processing */
  isThinking?: boolean;
  /** Widget collapse state (user preference) */
  isMinimized?: boolean;
  /** Internal reasoning traces */
  traces?: TraceStep[];
};

export type TraceStep = {
  type: 'thinking' | 'tool_use' | 'tool_output';
  content: string;
  toolName?: string;
};


export type SessionEvent = {
  id: string;
  app_name: string;
  user_id: string;
  session_id: string;
  event_data: any; // or Record<string, any> for more specificity
  event_index: number;
  created_at: string;
};

export function useAgentChat(initialSessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'agent', text: 'Hello! I am Pikar AI. How can I help you optimize your business today?', agentName: 'ExecutiveAgent' }
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const supabase = createClient();

  // Persist session ID across renders, initialize with prop if provided
  const sessionIdRef = useRef<string>(initialSessionId || `session-${Date.now()}`);

  // Fetch history when initialSessionId changes
  useEffect(() => {
    if (initialSessionId) {
      sessionIdRef.current = initialSessionId;
      loadHistory(initialSessionId);
    }
  }, [initialSessionId]);

  const loadHistory = async (sessionId: string) => {
    try {
      setIsLoadingHistory(true);
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { data: events, error } = await supabase
        .from('session_events')
        .select('*')
        .eq('session_id', sessionId)
        .order('event_index', { ascending: true });

      if (error) throw error;

      if (events && events.length > 0) {
        const historyMessages: Message[] = [];
        let currentGroupedMessage: Message | null = null;

        events.forEach((eventRow: SessionEvent) => {
          const event = eventRow.event_data;

          // Basic mapping based on A2A event structure
          // This logic may need refinement based on exact stored JSON structure
          if (event.source === 'user') {
            // Push previous agent message if exists
            if (currentGroupedMessage) {
              historyMessages.push(currentGroupedMessage);
              currentGroupedMessage = null;
            }

            // User message
            let text = '';
            if (event.content?.parts) {
              text = event.content.parts.map((p: any) => p.text || '').join('');
            } else if (typeof event.content === 'string') {
              text = event.content;
            }

            historyMessages.push({ role: 'user', text });

          } else if (event.source === 'model' || event.source === 'agent' || (event.source && event.source !== 'system')) {
            // Agent message - might be fragmented in storage or whole
            // Assuming storage keeps logical events.

            // Extract text
            let text = '';
            let widget: WidgetDefinition | undefined = undefined;

            if (event.content?.parts) {
              event.content.parts.forEach((p: any) => {
                if (p.text) text += p.text;
                if (p.widget) {
                  // Verify widget
                  if (validateWidgetDefinition(p.widget)) {
                    widget = p.widget;
                  }
                }
              });
            } else if (typeof event.content === 'string') {
              text = event.content;
            }

            // Check for widget at top level
            if (event.widget && validateWidgetDefinition(event.widget)) {
              widget = event.widget;
            }

            // If we rely on grouping logic (if events are granular chunks), we'd merge.
            // But usually persistence stores "turn" or "logical event".
            // Let's treat each as a message for now, or merge if sequential same agent?
            // Simplification: Push as new message
            historyMessages.push({
              role: 'agent',
              text: text || undefined,
              agentName: event.source, // or from event.author
              widget: widget
            });
          }
        });

        if (currentGroupedMessage) {
          historyMessages.push(currentGroupedMessage);
        }

        if (historyMessages.length > 0) {
          setMessages(historyMessages);
        }
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  /**
   * Toggle the minimized state of a widget message
   */
  const toggleWidgetMinimized = useCallback((messageIndex: number) => {
    setMessages((prev) => {
      // Create a shallow copy of the array
      const newMsgs = [...prev];
      // Check if the message exists and has a widget
      if (newMsgs[messageIndex]?.widget) {
        // Create a shallow copy of the message object
        newMsgs[messageIndex] = {
          ...newMsgs[messageIndex],
          isMinimized: !newMsgs[messageIndex].isMinimized
        };
      }
      return newMsgs;
    });
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    const userMsg: Message = { role: 'user', text: content };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      let currentAgentMessage = '';
      let currentAgentName = 'ExecutiveAgent';
      let currentWidget: WidgetDefinition | undefined = undefined;
      let currentTraces: TraceStep[] = [];

      // Add placeholder for streaming response
      setMessages((prev) => [
        ...prev,
        { role: 'agent', text: '', agentName: currentAgentName, isThinking: true }
      ]);

      await fetchEventSource(`${API_URL}/a2a/pikar_ai/run_sse`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          user_id: session?.user?.id, // Explicitly pass user ID
          new_message: { parts: [{ text: content }] },
        }),
        async onopen(response) {
          if (response.ok) {
            return;
          } else {
            throw new Error(`Failed to connect: ${response.statusText}`);
          }
        },
        onmessage(msg) {
          if (msg.event === 'ping') return;

          try {
            // A2A SSE payload structure check
            const data = JSON.parse(msg.data);

            // Handle agent updates (orchestration)
            if (data.author && data.author !== 'user' && data.author !== 'system') {
              if (data.author !== currentAgentName) {
                currentAgentName = data.author;
              }
            }

            // Handle content
            let newText = '';
            if (data.content && data.content.parts) {
              for (const part of data.content.parts) {
                // Extract text content
                if (part.text) {
                  newText += part.text;
                }
                // Extract widget definition (Agent-to-UI)
                if (part.widget) {
                  if (validateWidgetDefinition(part.widget)) {
                    currentWidget = part.widget as WidgetDefinition;
                  } else {
                    console.warn('Invalid widget definition received:', part.widget);
                  }
                }
              }
            } else if (data.content && typeof data.content === 'string') {
              // Sometimes it might send raw string, though A2A usually sends Content object
              newText = data.content;
            }

            // Also check for widget at the top level of the payload
            if (data.widget) {
              if (validateWidgetDefinition(data.widget)) {
                currentWidget = data.widget as WidgetDefinition;
              } else {
                console.warn('Invalid widget definition received:', data.widget);
              }
            }

            // Handle Traces (Tool Usage & Thoughts)
            // Note: Adjust parsing based on actual A2A event structure
            if (data.custom_event) {
              // Example: { custom_event: { type: 'tool_call', name: 'search', input: '...' } }
              if (data.custom_event.type === 'tool_call') {
                currentTraces.push({
                  type: 'tool_use',
                  toolName: data.custom_event.name,
                  content: JSON.stringify(data.custom_event.input)
                });
              } else if (data.custom_event.type === 'tool_result') {
                currentTraces.push({
                  type: 'tool_output',
                  toolName: data.custom_event.name,
                  content: "Completed" // Often too large to show full result
                });
              }
            }
            // Fallback for simple status/thought updates
            if (data.status) {
              currentTraces.push({
                type: 'thinking',
                content: data.status
              });
            }

            // if (newText || currentWidget) { // Relaxed condition to allow trace updates
            if (newText) {
              currentAgentMessage += newText;
            }

            setMessages((prev) => {
              const newMsgs = [...prev];
              const lastMsg = newMsgs[newMsgs.length - 1];
              if (lastMsg.role === 'agent') {
                lastMsg.text = currentAgentMessage || undefined;
                lastMsg.agentName = currentAgentName;
                // We deliberately keep isThinking=true until 'onclose' or explicit finish
                // However, for UX, if we have text, we might want to stop the spinner, 
                // but keep the ThoughtProcess active.
                // For now, let's keep isThinking true while streaming.
                lastMsg.traces = [...currentTraces];
                if (currentWidget) {
                  lastMsg.widget = currentWidget;
                }
              }
              return newMsgs;
            });
          } catch (e) {
            // console.error('Error parsing chunk', e);
          }
        },
        onerror(err) {
          console.error('SSE Error', err);
          setIsStreaming(false);
          throw err; // rethrow to stop
        }
      });

    } catch {
      // console.error('Chat failed', err); // Removed unused err
      setMessages((prev) => {
        // Remove the "thinking" placeholder if empty, or append error
        const newMsgs = [...prev];
        const lastMsg = newMsgs[newMsgs.length - 1];
        if (lastMsg.isThinking && !lastMsg.text && !lastMsg.widget) {
          return [...newMsgs.slice(0, -1), { role: 'system', text: 'Error: Failed to connect to Pikar AI.' }];
        }
        return [...prev, { role: 'system', text: 'Error: Connection interrupted.' }];
      });
      setIsStreaming(false);
    }
  }, [supabase]);

  return { messages, sendMessage, isStreaming, toggleWidgetMinimized, isLoadingHistory };
}

