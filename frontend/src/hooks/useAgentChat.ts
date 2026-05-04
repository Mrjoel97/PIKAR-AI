import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { createClient, getAuthenticatedUser } from '@/lib/supabase/client';
import { WidgetDefinition } from '@/types/widgets';
import {
  WidgetDisplayService,
  isWorkspaceCanvasWidget,
} from '@/services/widgetDisplay';
import { useSessionMap } from '@/contexts/SessionMapContext';
import { useSessionControl, TabCapReachedError } from '@/contexts/SessionControlContext';
import { toast } from 'sonner';
import { useBackgroundStream } from '@/hooks/useBackgroundStream';
import { useStreamCap } from '@/hooks/useStreamCap';
import { loadSessionHistory } from '@/lib/sessionHistory';
import {
  clearPendingChatSession,
  isPendingChatSession,
  markPendingChatSession,
} from '@/lib/pendingChatSessions';
import {
  isFreshClientSession,
  markFreshClientSession,
} from '@/lib/freshClientSessions';
import {
  isRecentlyFailedRestore,
  markFailedRestore,
} from '@/lib/failedRestoreSessions';
import { isAbortLikeError } from '@/lib/abort';
import { showSessionReadyToast } from '@/components/chat/SessionToast';

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
  /** Interaction ID from the feedback loop — set when interaction_complete SSE event is received. */
  interactionId?: string;
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

const HISTORY_AUTH_LOOKUP_TIMEOUT_MS = 2500;
const HISTORY_RESTORE_TIMEOUT_MS = 25000;
const HISTORY_AUTH_RETRY_DELAY_MS = 400;

// History-restore failures are now tracked via the localStorage-backed
// `failedRestoreSessions` helper (imported at the top of this file) with
// a 5-minute TTL. The persistent marker handles two distinct dedup scopes
// that previously needed separate solutions: (a) multiple useAgentChat
// instances mounted in parallel across persona dashboards (an in-memory
// Set solved this for a single page load) and (b) reload-loops where the
// user lands on a stuck session id from `pikar_current_session_id` and
// pays the 25-second timeout on every page load. The TTL ensures Supabase
// has a chance to recover without users being permanently locked out.

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(message)), timeoutMs);
    promise.then(
      (value) => {
        window.clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        window.clearTimeout(timer);
        reject(error);
      },
    );
  });
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
  const { activeSessions, updateSessionState, addActiveSession, getActiveSessionRef, sessions } = useSessionMap();
  const { visibleSessionId, selectChat, sessionRestored, sessionsLoaded, setVisibleSessionId } = useSessionControl();
  const { startStream, stopStream } = useBackgroundStream();
  const { enforceCapBeforeStream } = useStreamCap();
  const supabase = useMemo(() => createClient(), []);

  const widgetServiceRef = useRef(new WidgetDisplayService());

  // --- Session ID resolution ---
  // Prefer visibleSessionId from context, fall back to initialSessionId prop,
  // then generate a new one as last resort.
  const fallbackSessionIdRef = useRef<string>((() => {
    if (initialSessionId) return initialSessionId;
    const id = `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    // Mark synchronously at mint time so the restore effect sees it on its
    // very first run — no race with React state propagation. See
    // freshClientSessions.ts for the full rationale.
    markFreshClientSession(id);
    return id;
  })());
  const currentSessionId = visibleSessionId || initialSessionId || fallbackSessionIdRef.current;
  const usesFallbackSessionId =
    !visibleSessionId &&
    !initialSessionId &&
    currentSessionId === fallbackSessionIdRef.current;
  const historySessionId = visibleSessionId || initialSessionId || null;

  // --- Track whether initial session has been announced ---
  const isNewSessionRef = useRef(!initialSessionId);
  const onSessionStartedRef = useRef(onSessionStarted);
  const onAgentResponseRef = useRef(onAgentResponse);
  const selectChatRef = useRef(selectChat);
  const sessionsRef = useRef(sessions);
  const agentDisplayNameRef = useRef(agentDisplayName);
  // Stable ref that mirrors activeSessions so effects that only need to READ
  // the map (history loading, welcome-message check) can do so without listing
  // activeSessions itself as a dependency — preventing unrelated session-map
  // updates from restarting those effects.
  const activeSessionsRef = useRef(activeSessions);

  useEffect(() => {
    onSessionStartedRef.current = onSessionStarted;
  }, [onSessionStarted]);

  useEffect(() => {
    onAgentResponseRef.current = onAgentResponse;
  }, [onAgentResponse]);

  useEffect(() => {
    selectChatRef.current = selectChat;
  }, [selectChat]);

  useEffect(() => {
    sessionsRef.current = sessions;
  }, [sessions]);

  useEffect(() => {
    agentDisplayNameRef.current = agentDisplayName;
  }, [agentDisplayName]);

  useEffect(() => {
    activeSessionsRef.current = activeSessions;
  }, [activeSessions]);

  const getLatestSession = useCallback(
    (sessionId: string = currentSessionId) =>
      getActiveSessionRef(sessionId)?.current ?? activeSessionsRef.current.get(sessionId) ?? null,
    [currentSessionId, getActiveSessionRef],
  );

  // Ensure the first live chat session is treated as the visible session.
  // Without this, the first stream can behave like a background session and
  // the user won't see real-time placeholders or streamed updates.
  useEffect(() => {
    if (!sessionRestored) {
      return;
    }
    if (!visibleSessionId && currentSessionId) {
      if (usesFallbackSessionId) {
        markPendingChatSession(currentSessionId);
      }
      try {
        selectChat(currentSessionId);
      } catch (err) {
        // Auto-promote shouldn't crash the UI when the tab cap is hit.
        // The session continues to work as a background session — the user
        // simply doesn't get a tab pill until they close another tab.
        if (!(err instanceof TabCapReachedError)) throw err;
      }
    }
  }, [visibleSessionId, currentSessionId, selectChat, sessionRestored, usesFallbackSessionId]);

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
        skipHistoryRestore: usesFallbackSessionId,
      });
    }
  }, [currentSessionId, activeSessions, addActiveSession, agentDisplayName, usesFallbackSessionId]);

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
  //
  // IMPORTANT: This effect intentionally omits `activeSessions` from its
  // dependency list and reads the map through `activeSessionsRef.current`
  // instead. `activeSessions` is a new Map instance on every session-map
  // update (including unrelated sessions), so listing it here caused the
  // effect to cancel and restart the history fetch whenever any other session
  // received a message — producing a visible loading loop.
  //
  // `activeSessionsRef` is kept in sync by a dedicated sync effect above;
  // reading from it here is safe because we only gate on it at the start
  // (to decide whether we need to load) and at the end (to decide whether
  // to call addActiveSession or updateSessionState, both of which are
  // stable callbacks).
  useEffect(() => {
    if (!historySessionId) return;
    if (isRecentlyFailedRestore(historySessionId)) return;

    const session = activeSessionsRef.current.get(historySessionId);
    // Only load if the session is new / has only the welcome message
    const needsLoad = !session || session.messages.length === 0 ||
      (session.messages.length === 1 && session.messages[0].id === 'welcome-message');

    if (!needsLoad) return;

    // Once the persisted-sessions list has loaded for the current user, we
    // CAN authoritatively short-circuit when the historySessionId isn't in
    // it — that means the session was either abandoned without a send (so
    // there are zero events to restore) or doesn't belong to this user.
    // Either way, asking Supabase for it is wasted latency that turns into
    // a 25-second timeout on slow connections. We gate this on the
    // `sessionsLoaded` flag so we never short-circuit during the brief
    // async window before refreshSessions resolves (the original race that
    // made earlier versions of this effect mis-skip legitimately persisted
    // sessions on hard reload). The `skipHistoryRestore` flag and the
    // pending-session localStorage marker remain as the primary signals
    // for sessions created in the current tab.
    const isKnownPersistedSession = sessionsRef.current.some(
      (s) => s.id === historySessionId,
    );

    if (
      session?.skipHistoryRestore ||
      isPendingChatSession(historySessionId) ||
      isFreshClientSession(historySessionId) ||
      (sessionsLoaded && !isKnownPersistedSession)
    ) {
      if (!session || session.messages.length === 0) {
        const welcomeMessages = [makeWelcomeMessage(agentDisplayName)];
        if (activeSessionsRef.current.has(historySessionId)) {
          updateSessionState(historySessionId, {
            messages: welcomeMessages,
          });
        } else {
          addActiveSession(historySessionId, { messages: welcomeMessages });
        }
      }
      return;
    }

    let cancelled = false;
    loadingSessionIdRef.current = historySessionId;
    setIsLoadingHistory(true);

    const restoreWelcomeState = (reason: string, error?: unknown) => {
      console.warn(`[useAgentChat] Falling back to a fresh chat for ${historySessionId}: ${reason}`, error);
      markFailedRestore(historySessionId);

      // If the failed session is the one persisted in localStorage as the
      // user's "current" session, forget it. Without this, every reload
      // re-attaches the user to the same broken session and pays the 25-
      // second restore timeout again. We do this in TWO layers because
      // the React state path can miss the case where one useAgentChat
      // instance has the stuck id as `visibleSessionId` and another has
      // it via `initialSessionId` prop (only the first instance's check
      // matches, leaving localStorage unchanged for the second).
      //
      //   1. Direct localStorage write — bypasses React state and is
      //      idempotent across instances; whichever instance's restore
      //      times out first wins. Belt-and-suspenders against any
      //      mismatch between React state and persisted state.
      //   2. setVisibleSessionId(null) — keeps the in-memory state in
      //      sync so the current render switches to the fallback session
      //      immediately rather than waiting for the next reload.
      //
      // The session row + events are NOT deleted from Supabase; only
      // "this is your current tab" pointer is removed. The user can
      // re-open the session from the sidebar if Supabase recovers.
      try {
        if (
          typeof window !== 'undefined' &&
          window.localStorage.getItem('pikar_current_session_id') === historySessionId
        ) {
          window.localStorage.removeItem('pikar_current_session_id');
        }
      } catch {
        // localStorage unavailable — ignore
      }
      if (historySessionId === visibleSessionId) {
        setVisibleSessionId(null);
      }

      if (cancelled || loadingSessionIdRef.current !== historySessionId) {
        return;
      }

      const welcomeMessages = [makeWelcomeMessage(agentDisplayNameRef.current)];
      if (activeSessionsRef.current.has(historySessionId)) {
        updateSessionState(historySessionId, { messages: welcomeMessages });
      } else {
        addActiveSession(historySessionId, { messages: welcomeMessages });
      }
    };

    (async () => {
      try {
        let user = await getAuthenticatedUser({
          timeoutMs: HISTORY_AUTH_LOOKUP_TIMEOUT_MS,
        });
        if (!user) {
          await new Promise((r) => setTimeout(r, HISTORY_AUTH_RETRY_DELAY_MS));
          user = await getAuthenticatedUser({
            timeoutMs: HISTORY_AUTH_LOOKUP_TIMEOUT_MS,
          });
        }
        if (cancelled) {
          return;
        }
        if (!user) {
          restoreWelcomeState('no authenticated user was available for history restore');
          return;
        }

        const historyMessages = await withTimeout(
          loadSessionHistory(historySessionId, user.id),
          HISTORY_RESTORE_TIMEOUT_MS,
          'Session history restore timed out',
        );

        if (cancelled || loadingSessionIdRef.current !== historySessionId) {
          return;
        }

        if (historyMessages.length === 0) {
          // No history — ensure the session has a welcome message
          if (!activeSessionsRef.current.has(historySessionId)) {
            addActiveSession(historySessionId, {
              messages: [makeWelcomeMessage(agentDisplayNameRef.current)],
            });
          }
          return;
        }

        // Restore widget states via WidgetDisplayService
        const service = widgetServiceRef.current;
        const previousStates = new Map<string, boolean>();
        const existingWidgets = service.getSessionWidgets(user.id, historySessionId);
        existingWidgets.forEach((sw) => {
          if (sw.isMinimized !== undefined) {
            previousStates.set(sw.id, sw.isMinimized);
          }
        });

        service.clearSessionWidgets(user.id, historySessionId);
        historyMessages.forEach((msg) => {
          const widget = msg.widget;
          if (widget && isWorkspaceCanvasWidget(widget)) {
            const saved = service.saveWidget(user.id, historySessionId, widget, false);
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
          return !isMedia && isWorkspaceCanvasWidget(w);
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

        if (!cancelled && loadingSessionIdRef.current === historySessionId) {
          // Put loaded messages into the session map
          if (activeSessionsRef.current.has(historySessionId)) {
            updateSessionState(historySessionId, { messages: historyMessages });
          } else {
            addActiveSession(historySessionId, { messages: historyMessages });
          }
        }
      } catch (err) {
        if (isAbortLikeError(err)) {
          console.warn(
            `[useAgentChat] Session history restore aborted for ${historySessionId}; preserving the current session state.`,
            err,
          );
          return;
        }
        restoreWelcomeState('history restore failed', err);
      } finally {
        if (loadingSessionIdRef.current === historySessionId) {
          loadingSessionIdRef.current = null;
          setIsLoadingHistory(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      loadingSessionIdRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    // activeSessions intentionally excluded — see comment above.
    // sessionsLoaded IS included so the effect re-evaluates when the
    // persisted-sessions list finishes its first load and we can
    // authoritatively short-circuit stale-but-unknown session ids.
  }, [historySessionId, addActiveSession, updateSessionState, sessionsLoaded]);

  // ---------------------------------------------------------------------------
  // executeSend — delegates to startStream from useBackgroundStream
  // ---------------------------------------------------------------------------

  const executeSend = useCallback(async (content: string, agentMode: AgentMode, userMsgId: string) => {
    // Un-queue the user message
    const session = getLatestSession(currentSessionId);
    if (session) {
      const updatedMessages = session.messages.map(m =>
        m.id === userMsgId ? { ...m, isQueued: false } : m
      );
      updateSessionState(currentSessionId, { messages: updatedMessages });
    }

    clearPendingChatSession(currentSessionId);

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

        // Show toast notification for background sessions
        if (sid !== currentSessionId) {
          const sessionMeta = sessionsRef.current.find((s) => s.id === sid);
          const title = sessionMeta?.title || `Session ${sid.slice(0, 8)}`;
          showSessionReadyToast(sid, title, (targetId) => {
            try {
              selectChatRef.current(targetId);
            } catch (err) {
              if (err instanceof TabCapReachedError) {
                toast.error(
                  `Tab limit reached (${err.cap}). Close a tab to open this session.`,
                );
                return;
              }
              throw err;
            }
          });
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
          const sessionNow = getLatestSession(sid);
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
  }, [currentSessionId, getLatestSession, updateSessionState, enforceCapBeforeStream, startStream, agentDisplayName]);

  // ---------------------------------------------------------------------------
  // sendMessage — public API
  // ---------------------------------------------------------------------------

  const sendMessage = useCallback((content: string, agentMode: AgentMode = 'auto') => {
    if (!content.trim()) return;

    const userMsgId = `user-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const userMsg: Message = { id: userMsgId, role: 'user', text: content, isQueued: isStreamingRef.current };

    // Append user message to session map
    const session = getLatestSession(currentSessionId);
    if (session) {
      updateSessionState(currentSessionId, {
        messages: [...session.messages, userMsg],
      });
    } else {
      try {
        selectChat(currentSessionId);
      } catch (err) {
        if (err instanceof TabCapReachedError) {
          toast.error(
            `Tab limit reached (${err.cap}). Close a tab to open a new chat.`,
          );
          return;
        }
        throw err;
      }
      addActiveSession(currentSessionId, {
        messages: [...[makeWelcomeMessage(agentDisplayName)], userMsg],
      });
    }

    if (isStreamingRef.current) {
      messageQueueRef.current.push({ content, agentMode, userMsgId });
      return;
    }

    if (session) {
      executeSend(content, agentMode, userMsgId);
      return;
    }

    // Give the session map a tick to materialize the new session ref before streaming.
    setTimeout(() => {
      executeSend(content, agentMode, userMsgId);
    }, 0);
  }, [currentSessionId, getLatestSession, updateSessionState, addActiveSession, executeSend, agentDisplayName, selectChat]);

  // ---------------------------------------------------------------------------
  // addMessage — append an arbitrary message
  // ---------------------------------------------------------------------------

  const addMessage = useCallback((message: Message) => {
    const session = getLatestSession(currentSessionId);
    if (session) {
      updateSessionState(currentSessionId, {
        messages: [...session.messages, message],
      });
    } else {
      selectChat(currentSessionId);
      addActiveSession(currentSessionId, {
        messages: [...[makeWelcomeMessage(agentDisplayName)], message],
      });
    }
  }, [currentSessionId, getLatestSession, updateSessionState, addActiveSession, agentDisplayName, selectChat]);

  // ---------------------------------------------------------------------------
  // toggleWidgetMinimized — operates on visible session's messages
  // ---------------------------------------------------------------------------

  const toggleWidgetMinimized = useCallback((messageIndex: number) => {
    const session = getLatestSession(currentSessionId);
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
  }, [currentSessionId, getLatestSession, updateSessionState, supabase]);

  // ---------------------------------------------------------------------------
  // pinWidget — uses widgetService
  // ---------------------------------------------------------------------------

  const pinWidget = useCallback(async (messageIndex: number) => {
    const session = getLatestSession(currentSessionId);
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
  }, [currentSessionId, getLatestSession, supabase]);

  // ---------------------------------------------------------------------------
  // stopGeneration — delegates to stopStream
  // ---------------------------------------------------------------------------

  const stopGeneration = useCallback(() => {
    stopStream(currentSessionId);

    // Also clear the thinking state on the last agent message and add cancellation notice
    const session = getLatestSession(currentSessionId);
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
  }, [currentSessionId, getLatestSession, updateSessionState, stopStream]);

  // ---------------------------------------------------------------------------
  // getSessionId — for backward compat
  // ---------------------------------------------------------------------------

  const getSessionId = useCallback(() => currentSessionId, [currentSessionId]);

  // ---------------------------------------------------------------------------
  // App Builder autopilot — DOM event bridge
  // ---------------------------------------------------------------------------
  // The canvas widget converts iframe postMessages into two CustomEvents that
  // the chat hook subscribes to:
  //   - pikar-app-builder-questioning-complete  →  send a directive that the
  //     Executive translates into a start_app_builder_autopilot tool call.
  //   - pikar-app-builder-narration  →  inject a synthetic agent message
  //     into the current chat so the user sees orchestrator progress
  //     interleaved with the chat scrollback.

  useEffect(() => {
    function handleQuestioningComplete(e: Event) {
      const detail = (e as CustomEvent<{ projectId: string }>).detail;
      if (!detail?.projectId) return;
      sendMessage(
        `The user just completed the app-builder questioning wizard for project ${detail.projectId}. Call start_app_builder_autopilot now with that project_id and the current session_id.`,
      );
    }
    window.addEventListener(
      'pikar-app-builder-questioning-complete',
      handleQuestioningComplete,
    );
    return () =>
      window.removeEventListener(
        'pikar-app-builder-questioning-complete',
        handleQuestioningComplete,
      );
  }, [sendMessage]);

  useEffect(() => {
    function handleNarration(e: Event) {
      const detail = (e as CustomEvent<{ message: string; kind: string }>).detail;
      if (!detail?.message) return;
      addMessage({
        id: `autopilot-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        role: 'agent',
        text: detail.message,
        agentName: 'App Builder',
      });
    }
    window.addEventListener('pikar-app-builder-narration', handleNarration);
    return () =>
      window.removeEventListener(
        'pikar-app-builder-narration',
        handleNarration,
      );
  }, [addMessage]);

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
