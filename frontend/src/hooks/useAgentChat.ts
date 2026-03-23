import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { createClient } from '@/lib/supabase/client';
import { WidgetDefinition } from '@/types/widgets';
import {
  WidgetDisplayService,
} from '@/services/widgetDisplay';
import { useSessionMap } from '@/contexts/SessionMapContext';
import { useSessionControl } from '@/contexts/SessionControlContext';
import { useBackgroundStream } from '@/hooks/useBackgroundStream';
import { useStreamCap } from '@/hooks/useStreamCap';
import { loadSessionHistory } from '@/lib/sessionHistory';

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
  metadata?: import('@/lib/chatMetadata').MessageMetadata;
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

// ---------------------------------------------------------------------------
// Default welcome message factory
// ---------------------------------------------------------------------------

function makeWelcomeMessage(agentDisplayName: string): Message {
  return {
    id: 'welcome-message',
    role: 'agent',
    text: `Hello! I am ${agentDisplayName}. How can I help you optimize your business today?`,
    agentName: agentDisplayName,
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

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

  // --- Multi-session infrastructure ---
  const { activeSessions, updateSessionState, addActiveSession } = useSessionMap();
  const { visibleSessionId } = useSessionControl();
  const { startStream, stopStream } = useBackgroundStream();
  const { enforceCapBeforeStream } = useStreamCap();

  const supabase = createClient();
  const widgetServiceRef = useRef(new WidgetDisplayService());

  // --- Session ID resolution ---
  // Prefer visibleSessionId from context, fall back to initialSessionId prop,
  // then generate a new one as last resort.
  const fallbackSessionIdRef = useRef<string>(
    initialSessionId || `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
  );
  const currentSessionId = visibleSessionId || initialSessionId || fallbackSessionIdRef.current;

  // --- Track whether initial session has been announced ---
  const isNewSessionRef = useRef(!initialSessionId);
  const onSessionStartedRef = useRef(onSessionStarted);
  const onAgentResponseRef = useRef(onAgentResponse);

  useEffect(() => {
    onSessionStartedRef.current = onSessionStarted;
  }, [onSessionStarted]);

  useEffect(() => {
    onAgentResponseRef.current = onAgentResponse;
  }, [onAgentResponse]);

  // --- Message queue for sends during streaming ---
  const isStreamingRef = useRef(false);
  const messageQueueRef = useRef<{ content: string; agentMode: AgentMode; userMsgId: string }[]>([]);

  // --- History loading state ---
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const loadingSessionIdRef = useRef<string | null>(null);

  // --- Read messages from session map ---
  const activeSession = activeSessions.get(currentSessionId);
  const messages = useMemo(() => {
    const sessionMessages = activeSession?.messages;
    if (sessionMessages && sessionMessages.length > 0) {
      return sessionMessages;
    }
    // If no messages in the map yet, show the welcome message
    return [makeWelcomeMessage(agentDisplayName)];
  }, [activeSession?.messages, agentDisplayName]);

  const isStreaming = activeSession?.status === 'streaming';

  // Keep the isStreamingRef in sync with derived state
  useEffect(() => {
    isStreamingRef.current = isStreaming;
  }, [isStreaming]);

  // --- Ensure session exists in the map ---
  // When the session is not yet in activeSessions (e.g. fresh load), add it
  // so that startStream can find the ref.
  useEffect(() => {
    if (!currentSessionId) return;
    if (!activeSessions.has(currentSessionId)) {
      addActiveSession(currentSessionId, {
        messages: [makeWelcomeMessage(agentDisplayName)],
      });
    }
  }, [currentSessionId, activeSessions, addActiveSession, agentDisplayName]);

  // --- Update welcome message when customAgentName changes ---
  useEffect(() => {
    if (!customAgentName || !currentSessionId) return;
    const session = activeSessions.get(currentSessionId);
    if (!session || session.messages.length === 0) return;
    const first = session.messages[0];
    if (
      first.role !== 'agent' ||
      !first.text?.includes('How can I help you optimize your business today?')
    ) {
      return;
    }
    const updated = [...session.messages];
    updated[0] = {
      ...first,
      text: `Hello! I am ${customAgentName}. How can I help you optimize your business today?`,
      agentName: customAgentName,
    };
    updateSessionState(currentSessionId, { messages: updated });
  }, [customAgentName, currentSessionId, activeSessions, updateSessionState]);

  // --- Load history when switching to a session with no messages ---
  useEffect(() => {
    if (!initialSessionId) return;

    const session = activeSessions.get(initialSessionId);
    // Only load if the session is new / has only the welcome message
    const needsLoad = !session || session.messages.length === 0 ||
      (session.messages.length === 1 && session.messages[0].id === 'welcome-message');

    if (!needsLoad) return;

    let cancelled = false;
    loadingSessionIdRef.current = initialSessionId;
    setIsLoadingHistory(true);

    (async () => {
      try {
        let { data: { user } } = await supabase.auth.getUser();
        if (!user) {
          await new Promise((r) => setTimeout(r, 400));
          const retry = await supabase.auth.getUser();
          user = retry.data.user;
        }
        if (!user || cancelled) {
          setIsLoadingHistory(false);
          return;
        }

        const historyMessages = await loadSessionHistory(initialSessionId, user.id);

        if (cancelled || loadingSessionIdRef.current !== initialSessionId) {
          setIsLoadingHistory(false);
          return;
        }

        if (historyMessages.length === 0) {
          // No history — ensure the session has a welcome message
          if (!activeSessions.has(initialSessionId)) {
            addActiveSession(initialSessionId, {
              messages: [makeWelcomeMessage(agentDisplayName)],
            });
          }
          setIsLoadingHistory(false);
          return;
        }

        // Restore widget states via WidgetDisplayService
        const service = widgetServiceRef.current;
        const previousStates = new Map<string, boolean>();
        const existingWidgets = service.getSessionWidgets(user.id, initialSessionId);
        existingWidgets.forEach((sw) => {
          if (sw.isMinimized !== undefined) {
            previousStates.set(sw.id, sw.isMinimized);
          }
        });

        service.clearSessionWidgets(user.id, initialSessionId);
        historyMessages.forEach((msg) => {
          const widget = msg.widget;
          const isMedia = widget?.type === 'image' || widget?.type === 'video' || widget?.type === 'video_spec';
          if (widget && !isMedia && widget.type !== 'morning_briefing') {
            const saved = service.saveWidget(user.id, initialSessionId, widget, false);
            if (saved) {
              (widget as any).id = saved.id;
            }
          }
        });

        // Restore minimized states by position
        const prevArr = existingWidgets.filter((sw) => sw.isMinimized !== undefined);
        const currentWidgetMsgs = historyMessages.filter((m) => {
          const w = m.widget;
          if (!w) return false;
          const isMedia = w.type === 'image' || w.type === 'video' || w.type === 'video_spec';
          return !isMedia && w.type !== 'morning_briefing';
        });
        prevArr.forEach((prev, idx) => {
          if (idx < currentWidgetMsgs.length && prev.isMinimized) {
            currentWidgetMsgs[idx].isMinimized = prev.isMinimized;
            const widgetAny = currentWidgetMsgs[idx].widget as any;
            if (widgetAny?.id) {
              service.updateWidgetState(user.id, widgetAny.id, { isMinimized: prev.isMinimized });
            }
          }
        });

        if (!cancelled && loadingSessionIdRef.current === initialSessionId) {
          // Put loaded messages into the session map
          if (activeSessions.has(initialSessionId)) {
            updateSessionState(initialSessionId, { messages: historyMessages });
          } else {
            addActiveSession(initialSessionId, { messages: historyMessages });
          }
        }
      } catch (err) {
        console.error('[useAgentChat] Failed to load history:', err);
      } finally {
        if (loadingSessionIdRef.current === initialSessionId) {
          setIsLoadingHistory(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      loadingSessionIdRef.current = null;
    };
  }, [initialSessionId, supabase, agentDisplayName, activeSessions, addActiveSession, updateSessionState]);

  // ---------------------------------------------------------------------------
  // executeSend — delegates to startStream from useBackgroundStream
  // ---------------------------------------------------------------------------

  const executeSend = useCallback(async (content: string, agentMode: AgentMode, userMsgId: string) => {
    // Un-queue the user message
    const session = activeSessions.get(currentSessionId);
    if (session) {
      const updatedMessages = session.messages.map(m =>
        m.id === userMsgId ? { ...m, isQueued: false } : m
      );
      updateSessionState(currentSessionId, { messages: updatedMessages });
    }

    // Fire onSessionStarted callback for brand-new sessions
    if (isNewSessionRef.current && onSessionStartedRef.current) {
      onSessionStartedRef.current(currentSessionId, content);
      isNewSessionRef.current = false;
    }

    // Enforce the concurrent stream cap
    enforceCapBeforeStream();

    // Start the background stream
    await startStream({
      sessionId: currentSessionId,
      message: content,
      agentMode,
      agentDisplayName,
      onStreamComplete: (sid, finalText) => {
        // Fire the onAgentResponse callback
        if (onAgentResponseRef.current && finalText) {
          onAgentResponseRef.current(sid, finalText);
        }

        // Process the message queue
        if (messageQueueRef.current.length > 0) {
          const nextMsg = messageQueueRef.current.shift();
          if (nextMsg) {
            setTimeout(() => {
              executeSend(nextMsg.content, nextMsg.agentMode, nextMsg.userMsgId);
            }, 0);
          }
        }
      },
      onStreamError: (sid, _errorText) => {
        // On error, clear queued messages' isQueued flags
        if (messageQueueRef.current.length > 0) {
          const sessionNow = activeSessions.get(sid);
          if (sessionNow) {
            const msgs = sessionNow.messages.map(m => {
              if (messageQueueRef.current.some(q => q.userMsgId === m.id)) {
                return { ...m, isQueued: false };
              }
              return m;
            });
            updateSessionState(sid, { messages: msgs });
          }
          messageQueueRef.current = [];
        }
      },
    });
  }, [currentSessionId, activeSessions, updateSessionState, enforceCapBeforeStream, startStream, agentDisplayName]);

  // ---------------------------------------------------------------------------
  // sendMessage — public API
  // ---------------------------------------------------------------------------

  const sendMessage = useCallback((content: string, agentMode: AgentMode = 'auto') => {
    if (!content.trim()) return;

    const userMsgId = `user-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const userMsg: Message = { id: userMsgId, role: 'user', text: content, isQueued: isStreamingRef.current };

    // Append user message to session map
    const session = activeSessions.get(currentSessionId);
    if (session) {
      updateSessionState(currentSessionId, {
        messages: [...session.messages, userMsg],
      });
    }

    if (isStreamingRef.current) {
      messageQueueRef.current.push({ content, agentMode, userMsgId });
      return;
    }

    executeSend(content, agentMode, userMsgId);
  }, [currentSessionId, activeSessions, updateSessionState, executeSend]);

  // ---------------------------------------------------------------------------
  // addMessage — append an arbitrary message
  // ---------------------------------------------------------------------------

  const addMessage = useCallback((message: Message) => {
    const session = activeSessions.get(currentSessionId);
    if (session) {
      updateSessionState(currentSessionId, {
        messages: [...session.messages, message],
      });
    }
  }, [currentSessionId, activeSessions, updateSessionState]);

  // ---------------------------------------------------------------------------
  // toggleWidgetMinimized — operates on visible session's messages
  // ---------------------------------------------------------------------------

  const toggleWidgetMinimized = useCallback((messageIndex: number) => {
    const session = activeSessions.get(currentSessionId);
    if (!session) return;

    const msgs = [...session.messages];
    if (msgs[messageIndex]?.widget) {
      const minimized = !msgs[messageIndex].isMinimized;
      msgs[messageIndex] = { ...msgs[messageIndex], isMinimized: minimized };
      updateSessionState(currentSessionId, { messages: msgs });

      // Persist widget state
      const widgetAny = msgs[messageIndex]?.widget as any;
      const widgetId = widgetAny?.id;
      if (widgetId) {
        (async () => {
          const { data } = await supabase.auth.getUser();
          if (data.user) {
            widgetServiceRef.current.updateWidgetState(data.user.id, widgetId, {
              isMinimized: minimized,
            });
          }
        })();
      }
    }
  }, [currentSessionId, activeSessions, updateSessionState, supabase]);

  // ---------------------------------------------------------------------------
  // pinWidget — uses widgetService
  // ---------------------------------------------------------------------------

  const pinWidget = useCallback(async (messageIndex: number) => {
    const session = activeSessions.get(currentSessionId);
    if (!session) return;
    const msg = session.messages[messageIndex];
    if (!msg?.widget) return;
    if (msg.widget.type === 'image' || msg.widget.type === 'video' || msg.widget.type === 'video_spec') return;
    const { data } = await supabase.auth.getUser();
    if (data.user) {
      const widgetAny = msg.widget as any;
      if (widgetAny.id) {
        widgetServiceRef.current.pinWidget(widgetAny.id, data.user.id);
      } else {
        widgetServiceRef.current.saveWidget(data.user.id, currentSessionId, msg.widget, true);
      }
    }
  }, [currentSessionId, activeSessions, supabase]);

  // ---------------------------------------------------------------------------
  // stopGeneration — delegates to stopStream
  // ---------------------------------------------------------------------------

  const stopGeneration = useCallback(() => {
    stopStream(currentSessionId);

    // Also clear the thinking state on the last agent message and add cancellation notice
    const session = activeSessions.get(currentSessionId);
    if (session) {
      const msgs = [...session.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'agent') {
          if (msgs[i].isThinking) {
            msgs[i] = { ...msgs[i], isThinking: false };
          }
          break;
        }
      }
      // Clear isQueued flags
      for (let i = 0; i < msgs.length; i++) {
        if (msgs[i].isQueued) {
          msgs[i] = { ...msgs[i], isQueued: false };
        }
      }
      msgs.push({ role: 'system', text: 'Task cancelled by user. Queued messages were aborted.' });
      updateSessionState(currentSessionId, { messages: msgs, status: 'idle' });
    }

    messageQueueRef.current = [];
  }, [currentSessionId, activeSessions, updateSessionState, stopStream]);

  // ---------------------------------------------------------------------------
  // getSessionId — for backward compat
  // ---------------------------------------------------------------------------

  const getSessionId = useCallback(() => currentSessionId, [currentSessionId]);

  // ---------------------------------------------------------------------------
  // Return — exact same shape as original
  // ---------------------------------------------------------------------------

  return {
    messages,
    sendMessage,
    addMessage,
    isStreaming,
    toggleWidgetMinimized,
    isLoadingHistory,
    pinWidget,
    sessionId: currentSessionId,
    getSessionId,
    stopGeneration,
  };
}
