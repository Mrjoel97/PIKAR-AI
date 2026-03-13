import { useState, useCallback, useRef, useEffect } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { createClient } from '@/lib/supabase/client';
import { extractMessageMetadataFromEvent, extractMessageMetadataFromParts, MessageMetadata } from '@/lib/chatMetadata';
import { WidgetDefinition, validateWidgetDefinition } from '@/types/widgets';
import {
  WidgetDisplayService,
  dispatchFocusWidget,
  dispatchWorkspaceActivity,
} from '@/services/widgetDisplay';

/**
 * Chat message representing user input, agent response, or system notification.
 * Messages can optionally contain a widget for interactive UI display.
 */
export type Message = {
  id?: string;
  role: 'user' | 'agent' | 'system';
  text?: string;
  widget?: WidgetDefinition;
  agentName?: string;
  isThinking?: boolean;
  isMinimized?: boolean;
  traces?: TraceStep[];
  isQueued?: boolean;
  metadata?: MessageMetadata;
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
  event_data: any;
  event_index: number;
  created_at: string;
};

/**
 * Agent interaction mode that determines how the agent behaves:
 * - auto: Agent works independently.
 * - collab: Agent asks for approval and insights.
 * - ask: User asks agent about progress and history.
 */
export type AgentMode = 'auto' | 'collab' | 'ask';

export interface UseAgentChatOptions {
  initialSessionId?: string;
  customAgentName?: string;
  onSessionStarted?: (sessionId: string, firstMessage: string) => void;
  onAgentResponse?: (sessionId: string, agentMessage: string) => void;
}

export function useAgentChat(
  initialSessionIdOrOptions?: string | UseAgentChatOptions,
  customAgentNameLegacy?: string
) {
  // Backward compatibility: allow both useAgentChat("sessionId") and useAgentChat({ ...options })
  const options: UseAgentChatOptions = typeof initialSessionIdOrOptions === 'object'
    ? initialSessionIdOrOptions
    : { initialSessionId: initialSessionIdOrOptions, customAgentName: customAgentNameLegacy };

  const { initialSessionId, customAgentName, onSessionStarted, onAgentResponse } = options;
  const agentDisplayName = customAgentName || 'Pikar AI';

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-message',
      role: 'agent',
      text: `Hello! I am ${agentDisplayName}. How can I help you optimize your business today?`,
      agentName: agentDisplayName,
    },
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const isStreamingRef = useRef(false);
  const messageQueueRef = useRef<{ content: string; agentMode: AgentMode; userMsgId: string }[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const supabase = createClient();
  const widgetServiceRef = useRef(new WidgetDisplayService());

  const sessionIdRef = useRef<string>(
    initialSessionId || `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
  );
  const isNewSessionRef = useRef(!initialSessionId);
  const onSessionStartedRef = useRef(onSessionStarted);
  const onAgentResponseRef = useRef(onAgentResponse);
  const loadingSessionIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    onSessionStartedRef.current = onSessionStarted;
  }, [onSessionStarted]);

  useEffect(() => {
    onAgentResponseRef.current = onAgentResponse;
  }, [onAgentResponse]);

  useEffect(() => {
    setMessages((prev) => {
      if (
        !customAgentName ||
        prev.length === 0 ||
        prev[0].role !== 'agent' ||
        !prev[0].text?.includes('How can I help you optimize your business today?')
      ) {
        return prev;
      }
      const next = [...prev];
      next[0] = {
        ...next[0],
        text: `Hello! I am ${customAgentName}. How can I help you optimize your business today?`,
        agentName: customAgentName,
      };
      return next;
    });
  }, [customAgentName]);

  const withWorkspaceDefaults = useCallback((widget: WidgetDefinition): WidgetDefinition => {
    if (widget.type === 'morning_briefing') return widget;
    return {
      ...widget,
      workspace: {
        ...widget.workspace,
        mode: widget.workspace?.mode ?? 'focus',
      },
    };
  }, []);

  const loadHistory = useCallback(async (sessionId: string) => {
    try {
      setIsLoadingHistory(true);
      let { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        await new Promise((r) => setTimeout(r, 400));
        const retry = await supabase.auth.getUser();
        user = retry.data.user;
      }
      if (!user) {
        setIsLoadingHistory(false);
        return;
      }

      const { data: events, error } = await supabase
        .from('session_events')
        .select('*')
        .eq('session_id', sessionId)
        .eq('app_name', 'agents')
        .eq('user_id', user.id)
        .is('superseded_by', null)
        .order('event_index', { ascending: true });

      if (error) {
        setIsLoadingHistory(false);
        return;
      }

      if (loadingSessionIdRef.current !== sessionId) {
        setIsLoadingHistory(false);
        return;
      }

      if (!events || events.length === 0) {
        if (sessionIdRef.current === sessionId) {
          setMessages([
            {
              id: 'welcome-message',
              role: 'agent',
              text: `Hello! I am ${agentDisplayName}. How can I help you optimize your business today?`,
              agentName: agentDisplayName,
            },
          ]);
        }
        setIsLoadingHistory(false);
        return;
      }

      const historyMessages: Message[] = [];
      events.forEach((eventRow: SessionEvent) => {
        const event = eventRow.event_data || {};
        const who = event?.author ?? event?.source;

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

        if (who === 'model' || who === 'agent' || (who && who !== 'system')) {
          let text = '';
          let widget: WidgetDefinition | undefined;

          if (event.content?.parts) {
            event.content.parts.forEach((p: any) => {
              if (p.text) text += p.text;
              if (p.widget && validateWidgetDefinition(p.widget)) {
                widget = withWorkspaceDefaults(p.widget as WidgetDefinition);
              }

              const fr =
                p?.function_response
                ?? (p as { functionResponse?: { response?: unknown; response_data?: unknown } }).functionResponse;
              if (fr && !widget) {
                const response = (fr as any).response ?? (fr as any).response_data;
                let candidate = typeof response === 'object' && response !== null
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

          if (event.widget && validateWidgetDefinition(event.widget)) {
            widget = withWorkspaceDefaults(event.widget as WidgetDefinition);
          }

          const metadata = extractMessageMetadataFromEvent(event);
          const displayName = who === 'ExecutiveAgent' ? agentDisplayName : who;
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

      const refsMatch = loadingSessionIdRef.current === sessionId && sessionIdRef.current === sessionId;
      if (historyMessages.length > 0 && refsMatch) {
        setMessages(historyMessages);
        const service = new WidgetDisplayService();
        service.clearSessionWidgets(user.id, sessionId);
        historyMessages.forEach((msg) => {
          const widget = msg.widget;
          const isMedia = widget?.type === 'image' || widget?.type === 'video' || widget?.type === 'video_spec';
          if (widget && !isMedia && widget.type !== 'morning_briefing') {
            service.saveWidget(user.id, sessionId, widget, false);
          }
        });
      }
    } catch (err) {
      console.error('[useAgentChat] Failed to load history:', err);
    } finally {
      if (loadingSessionIdRef.current === sessionId) {
        setIsLoadingHistory(false);
      }
    }
  }, [agentDisplayName, supabase, withWorkspaceDefaults]);

  useEffect(() => {
    if (!initialSessionId) return;
    sessionIdRef.current = initialSessionId;
    loadingSessionIdRef.current = initialSessionId;
    loadHistory(initialSessionId);
    return () => {
      loadingSessionIdRef.current = null;
    };
  }, [initialSessionId, loadHistory]);

  const toggleWidgetMinimized = useCallback((messageIndex: number) => {
    setMessages((prev) => {
      const next = [...prev];
      if (next[messageIndex]?.widget) {
        const minimized = !next[messageIndex].isMinimized;
        next[messageIndex] = {
          ...next[messageIndex],
          isMinimized: minimized,
        };
      }
      return next;
    });

    const updatePersistence = async () => {
      const { data } = await supabase.auth.getUser();
      if (data.user && messages[messageIndex]?.widget) {
        const widgetAny = messages[messageIndex].widget as any;
        if (widgetAny.id) {
          widgetServiceRef.current.updateWidgetState(data.user.id, widgetAny.id, {
            isMinimized: !messages[messageIndex].isMinimized,
          });
        }
      }
    };
    updatePersistence();
  }, [messages, supabase]);

  const pinWidget = useCallback(async (messageIndex: number) => {
    const msg = messages[messageIndex];
    if (!msg?.widget) return;
    if (msg.widget.type === 'image' || msg.widget.type === 'video' || msg.widget.type === 'video_spec') return;
    const { data } = await supabase.auth.getUser();
    if (data.user) {
      const widgetAny = msg.widget as any;
      if (widgetAny.id) {
        widgetServiceRef.current.pinWidget(widgetAny.id, data.user.id);
      } else {
        widgetServiceRef.current.saveWidget(data.user.id, sessionIdRef.current, msg.widget, true);
      }
    }
  }, [messages, supabase]);

  const executeSend = useCallback(async (content: string, agentMode: AgentMode, userMsgId: string) => {
    setMessages((prev) => prev.map(m => m.id === userMsgId ? { ...m, isQueued: false } : m));

    isStreamingRef.current = true;
    setIsStreaming(true);

    if (isNewSessionRef.current && onSessionStartedRef.current) {
      onSessionStartedRef.current(sessionIdRef.current, content);
      isNewSessionRef.current = false;
    }

    let finalAgentText = '';
    let finalAgentName = agentDisplayName;
    let finalTraces: TraceStep[] = [];
    const agentMsgId = `agent-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

    let hasError = false;

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      if (!token) {
        throw new Error('Client error: 401'); // Force early exit if token is completely missing
      }

      const userId = session?.user?.id;
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      let currentAgentMessage = '';
      let currentAgentName = agentDisplayName;
      let currentWidget: WidgetDefinition | undefined;
      let currentMetadata: MessageMetadata | undefined;
      const currentTraces: TraceStep[] = [];
      const seenProgressStages = new Set<string>();

      setMessages((prev) => [
        ...prev,
        { id: agentMsgId, role: 'agent', text: '', agentName: currentAgentName, isThinking: true },
      ]);

      if (userId) {
        dispatchWorkspaceActivity({
          userId,
          sessionId: sessionIdRef.current,
          phase: 'running',
          agentName: currentAgentName,
        });
      }

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      await fetchEventSource(`${API_URL}/a2a/app/run_sse`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        signal: abortController.signal,
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          user_id: session?.user?.id,
          new_message: { parts: [{ text: content }] },
          agent_mode: agentMode,
        }),
        openWhenHidden: true,
        async onopen(response) {
          const contentType = response.headers.get('content-type') || '';
          if (response.ok && contentType.startsWith('text/event-stream')) return;
          if (response.status >= 400 && response.status < 500 && response.status !== 429) {
            throw new Error(`Client error: ${response.status}`);
          }
          throw new Error(`Unexpected response: ${response.status} ${response.statusText}`);
        },
        onmessage(msg) {
          if (msg.event === 'ping') return;

          try {
            const data = JSON.parse(msg.data);

            if (data.event_type === 'director_progress') {
              const stage = typeof data.stage === 'string' ? data.stage : 'unknown';
              const stageLabel: Record<string, string> = {
                planning_started: 'Planning storyboard',
                planning_done: 'Storyboard ready',
                assets_done: 'Scene assets generated',
                rendering_started: 'Rendering final video',
                completed: 'Video completed',
                failed: 'Video generation failed',
              };
              const label = stageLabel[stage] || `Progress: ${stage}`;
              const payloadText = data.payload && Object.keys(data.payload).length > 0
                ? ` (${JSON.stringify(data.payload)})`
                : '';
              const traceContent = `${label}${payloadText}`;
              const dedupeKey = `${stage}:${payloadText}`;

              if (!seenProgressStages.has(dedupeKey)) {
                seenProgressStages.add(dedupeKey);
                currentTraces.push({
                  type: stage === 'completed' || stage === 'failed' ? 'tool_output' : 'tool_use',
                  toolName: 'AI Director',
                  content: traceContent,
                });
              }
            }

            if (data.error) {
              hasError = true;
              const errorText = typeof data.error === 'string'
                ? data.error
                : 'Agent encountered an internal error. Please try again.';
              setMessages((prev) => {
                const next = [...prev];
                const targetIdx = next.findIndex(m => m.id === agentMsgId);
                if (targetIdx !== -1) {
                  const targetMsg = next[targetIdx];
                  if (targetMsg.role === 'agent' && targetMsg.isThinking && !targetMsg.text) {
                    next.splice(targetIdx, 1);
                    return [...next, { role: 'system', text: `Error: ${errorText}` }];
                  }
                }
                return [...prev, { role: 'system', text: `Error: ${errorText}` }];
              });
              if (userId) {
                dispatchWorkspaceActivity({
                  userId,
                  sessionId: sessionIdRef.current,
                  phase: 'error',
                  agentName: currentAgentName,
                  text: errorText,
                  traces: [...currentTraces],
                });
              }
              return;
            }

            if (data.author && data.author !== 'user' && data.author !== 'system') {
              if (data.author === 'ExecutiveAgent') {
                currentAgentName = agentDisplayName;
              } else {
                currentAgentName = data.author;
              }
            }

            let newText = '';
            if (data.content?.parts) {
              const extractedMetadata = extractMessageMetadataFromParts(data.content.parts);
              if (extractedMetadata) {
                currentMetadata = extractedMetadata;
              }
              for (const part of data.content.parts) {
                if (part.text) newText += part.text;
                if (part.widget && validateWidgetDefinition(part.widget)) {
                  currentWidget = withWorkspaceDefaults(part.widget as WidgetDefinition);
                }
              }
            } else if (typeof data.content === 'string') {
              newText = data.content;
            }

            if (!currentMetadata) {
              currentMetadata = extractMessageMetadataFromEvent(data);
            }

            if (data.widget && validateWidgetDefinition(data.widget)) {
              currentWidget = withWorkspaceDefaults(data.widget as WidgetDefinition);
            }

            if (currentWidget && userId && currentWidget.type !== 'morning_briefing') {
              const isMedia = currentWidget.type === 'image'
                || currentWidget.type === 'video'
                || currentWidget.type === 'video_spec';
              if (!isMedia) {
                const widgetAny = currentWidget as { id?: string };
                if (!widgetAny.id) {
                  const saved = widgetServiceRef.current.saveWidget(userId, sessionIdRef.current, currentWidget, false);
                  if (saved) {
                    widgetAny.id = saved.id;
                  }
                }
              }
              dispatchFocusWidget(currentWidget, userId);
            }

            if (data.custom_event) {
              if (data.custom_event.type === 'tool_call') {
                currentTraces.push({
                  type: 'tool_use',
                  toolName: data.custom_event.name,
                  content: JSON.stringify(data.custom_event.input),
                });
              } else if (data.custom_event.type === 'tool_result') {
                currentTraces.push({
                  type: 'tool_output',
                  toolName: data.custom_event.name,
                  content: 'Completed',
                });
              }
            }

            if (data.status) {
              currentTraces.push({
                type: 'thinking',
                content: data.status,
              });
            }

            if (newText) {
              currentAgentMessage += newText;
            }

            setMessages((prev) => {
              const next = [...prev];
              const targetIdx = next.findIndex(m => m.id === agentMsgId);
              if (targetIdx !== -1) {
                const targetMsg = next[targetIdx];
                if (targetMsg.role === 'agent') {
                  const hasContent = Boolean(currentAgentMessage || currentWidget || currentTraces.length > 0);
                  next[targetIdx] = {
                    ...targetMsg,
                    text: currentAgentMessage || undefined,
                    agentName: currentAgentName,
                    traces: [...currentTraces],
                    ...(currentWidget ? { widget: currentWidget } : {}),
                    ...(currentMetadata ? { metadata: currentMetadata } : {}),
                    isThinking: !hasContent,
                  };
                }
              }
              return next;
            });

            finalAgentText = currentAgentMessage;
            finalAgentName = currentAgentName;
            finalTraces = [...currentTraces];

            if (userId) {
              dispatchWorkspaceActivity({
                userId,
                sessionId: sessionIdRef.current,
                phase: 'running',
                agentName: currentAgentName,
                text: currentAgentMessage || undefined,
                traces: [...currentTraces],
              });
            }
          } catch (e) {
            console.error('[SSE] Error parsing chunk:', e, 'raw data:', msg.data);
          }
        },
        onclose() {
          // normal close
        },
        onerror(err) {
          throw err;
        },
      });
    } catch (err) {
      hasError = true;
      const isNetworkError =
        (err instanceof TypeError && (err.message === 'Failed to fetch' || err.message === 'Load failed'))
        || (err instanceof Error && (err.message.includes('fetch') || err.message.includes('NetworkError')));
      const isUnauthorized = err instanceof Error && err.message.includes('401');

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      let connectionErrorText;
      if (isUnauthorized) {
        connectionErrorText = 'Error: Your session has expired or is invalid. Please refresh the page or log in again.';
      } else if (isNetworkError) {
        connectionErrorText = `Error: Cannot reach the backend at ${apiUrl}. Ensure it's running and NEXT_PUBLIC_API_URL is correct.`;
      } else {
        connectionErrorText = 'Error: Failed to connect to Pikar AI. Please try again.';
      }

      setMessages((prev) => {
        const next = [...prev];
        const targetIdx = next.findIndex(m => m.id === agentMsgId);
        if (targetIdx !== -1) {
          const targetMsg = next[targetIdx];
          if (targetMsg.role === 'agent' && targetMsg.isThinking && !targetMsg.text && !targetMsg.widget) {
            next.splice(targetIdx, 1);
            return [...next, { role: 'system', text: connectionErrorText }];
          }
          if (targetMsg?.role === 'agent' && targetMsg.isThinking) {
            next[targetIdx] = { ...targetMsg, isThinking: false };
            return [...next, { role: 'system', text: connectionErrorText }];
          }
        }
        return [...prev, { role: 'system', text: connectionErrorText }];
      });

      try {
        const { data: { session } } = await supabase.auth.getSession();
        const userId = session?.user?.id;
        if (userId) {
          dispatchWorkspaceActivity({
            userId,
            sessionId: sessionIdRef.current,
            phase: 'error',
            agentName: finalAgentName,
            text: finalAgentText || undefined,
            traces: finalTraces,
          });
        }
      } catch {
        // no-op
      }
    } finally {
      isStreamingRef.current = false;
      setIsStreaming(false);

      setMessages((prev) => {
        const next = [...prev];
        const targetIdx = next.findIndex(m => m.id === agentMsgId);
        if (targetIdx !== -1) {
          const targetMsg = next[targetIdx];
          if (targetMsg.role === 'agent' && targetMsg.isThinking) {
            next[targetIdx] = { ...targetMsg, isThinking: false };
          }
          if (onAgentResponseRef.current && targetMsg.role === 'agent' && targetMsg.text) {
            onAgentResponseRef.current(sessionIdRef.current, targetMsg.text);
          }
        }
        return next;
      });

      try {
        const { data: { session } } = await supabase.auth.getSession();
        const userId = session?.user?.id;
        if (userId && !hasError) {
          dispatchWorkspaceActivity({
            userId,
            sessionId: sessionIdRef.current,
            phase: 'completed',
            agentName: finalAgentName,
            text: finalAgentText || undefined,
            traces: finalTraces,
          });
        }
      } catch {
        // no-op
      }
      abortControllerRef.current = null;

      if (messageQueueRef.current.length > 0) {
        if (hasError) {
          setMessages((prev) => {
            const next = [...prev];
            messageQueueRef.current.forEach(queuedMsg => {
              const targetIdx = next.findIndex(m => m.id === queuedMsg.userMsgId);
              if (targetIdx !== -1) {
                next[targetIdx] = { ...next[targetIdx], isQueued: false };
              }
            });
            return next;
          });
          messageQueueRef.current = [];
        } else {
          const nextMsg = messageQueueRef.current.shift();
          if (nextMsg) {
            setTimeout(() => {
              executeSend(nextMsg.content, nextMsg.agentMode, nextMsg.userMsgId);
            }, 0);
          }
        }
      }
    }
  }, [agentDisplayName, supabase, withWorkspaceDefaults]);

  const sendMessage = useCallback((content: string, agentMode: AgentMode = 'auto') => {
    if (!content.trim()) return;

    const userMsgId = `user-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const userMsg: Message = { id: userMsgId, role: 'user', text: content, isQueued: isStreamingRef.current };

    setMessages((prev) => [...prev, userMsg]);

    if (isStreamingRef.current) {
      messageQueueRef.current.push({ content, agentMode, userMsgId });
      return;
    }

    executeSend(content, agentMode, userMsgId);
  }, [executeSend]);

  const addMessage = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const getSessionId = useCallback(() => sessionIdRef.current, []);

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      isStreamingRef.current = false;
      setIsStreaming(false);
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === 'agent') {
            if (next[i].isThinking) {
              next[i] = { ...next[i], isThinking: false };
            }
            break;
          }
        }
        // Also clear isQueued flag for any user messages that were waiting
        for (let i = 0; i < next.length; i++) {
          if (next[i].isQueued) {
            next[i] = { ...next[i], isQueued: false };
          }
        }
        return [...next, { role: 'system', text: 'Task cancelled by user. Queued messages were aborted.' }];
      });
      // Also clear the queue
      messageQueueRef.current = [];
    }
  }, []);

  return {
    messages,
    sendMessage,
    addMessage,
    isStreaming,
    toggleWidgetMinimized,
    isLoadingHistory,
    pinWidget,
    sessionId: sessionIdRef.current,
    getSessionId,
    stopGeneration,
  };
}
