/**
 * Background SSE stream manager for multi-session chat.
 *
 * Uses the pure sseParser to drive fetchEventSource connections that write
 * results into ActiveSessionState entries via refs. Visibility gating ensures
 * that foreground sessions receive immediate React re-renders while background
 * sessions only accumulate data in refs (no re-renders) and queue side effects.
 */

'use client';

import { useCallback, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { createClient } from '@/lib/supabase/client';
import { createAccumulator, parseSSEEvent } from '@/lib/sseParser';
import { useSessionMap } from '@/contexts/SessionMapContext';
import { useSessionControl } from '@/contexts/SessionControlContext';
import type { ActiveSessionState, PendingSessionAction, RawWidgetData } from '@/types/session';
import type { Message, AgentMode, TraceStep } from '@/hooks/useAgentChat';
import { validateWidgetDefinition, type WidgetDefinition } from '@/types/widgets';
import {
  WidgetDisplayService,
  dispatchFocusWidget,
  dispatchWorkspaceActivity,
} from '@/services/widgetDisplay';

// ---------------------------------------------------------------------------
// Workspace-defaults helper (mirrors useAgentChat)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface StartStreamOptions {
  sessionId: string;
  message: string;
  agentMode: AgentMode;
  agentDisplayName?: string;
  onStreamComplete?: (sessionId: string, finalText: string) => void;
  onStreamError?: (sessionId: string, error: string) => void;
  /** User ID — if not provided, will be fetched from Supabase auth. */
  userId?: string;
}

export interface UseBackgroundStreamReturn {
  startStream: (options: StartStreamOptions) => Promise<void>;
  stopStream: (sessionId: string) => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useBackgroundStream(): UseBackgroundStreamReturn {
  const { getActiveSessionRef, updateSessionState } = useSessionMap();
  const { visibleSessionId } = useSessionControl();

  // Track visibleSessionId in a ref to avoid stale closures inside
  // the long-lived fetchEventSource callbacks.
  const visibleSessionIdRef = useRef<string | null>(visibleSessionId);
  visibleSessionIdRef.current = visibleSessionId;

  const widgetServiceRef = useRef(new WidgetDisplayService());
  const supabase = createClient();

  // ------------------------------------------------------------------
  // stopStream
  // ------------------------------------------------------------------
  const stopStream = useCallback(
    (sessionId: string) => {
      const ref = getActiveSessionRef(sessionId);
      if (!ref?.current) return;

      const session = ref.current;
      if (session.abortController) {
        session.abortController.abort();
      }

      // Write to ref immediately
      ref.current = {
        ...session,
        status: 'idle',
        abortController: null,
      };

      // Also propagate to React state
      updateSessionState(sessionId, {
        status: 'idle',
        abortController: null,
      });
    },
    [getActiveSessionRef, updateSessionState],
  );

  // ------------------------------------------------------------------
  // startStream
  // ------------------------------------------------------------------
  const startStream = useCallback(
    async (options: StartStreamOptions) => {
      const {
        sessionId,
        message,
        agentMode,
        agentDisplayName = 'Pikar AI',
        onStreamComplete,
        onStreamError,
      } = options;

      // ---- Auth ----
      const { data: { session: authSession } } = await supabase.auth.getSession();
      const token = authSession?.access_token;
      if (!token) {
        onStreamError?.(sessionId, 'Your session has expired. Please log in again.');
        updateSessionState(sessionId, { status: 'error' });
        return;
      }
      const userId = options.userId ?? authSession?.user?.id;

      // ---- Session ref ----
      const sessionRef = getActiveSessionRef(sessionId);
      if (!sessionRef?.current) return;

      // ---- AbortController ----
      const abortController = new AbortController();

      // ---- Build initial agent message ----
      const agentMsgId = `agent-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const agentPlaceholder: Message = {
        id: agentMsgId,
        role: 'agent',
        text: '',
        agentName: agentDisplayName,
        isThinking: true,
      };

      // ---- Initialise ref state ----
      const current = sessionRef.current;
      sessionRef.current = {
        ...current,
        status: 'streaming',
        abortController,
        messages: [...current.messages, agentPlaceholder],
        lastUpdatedAt: Date.now(),
      };

      // If visible, push to React state too
      if (visibleSessionIdRef.current === sessionId) {
        updateSessionState(sessionId, {
          status: 'streaming',
          abortController,
          messages: sessionRef.current.messages,
        });
      }

      // ---- Accumulator ----
      const acc = createAccumulator(agentDisplayName);
      let hasError = false;

      // ---- Retry configuration ----
      let retryCount = 0;
      const MAX_RETRIES = 3;
      const RETRY_DELAYS = [1000, 2000, 4000]; // exponential backoff in ms

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // ---- Helper: mark last agent message with reconnecting indicator ----
      const setReconnectingIndicator = (isReconnecting: boolean, attempt: number) => {
        const ref = getActiveSessionRef(sessionId);
        if (!ref?.current) return;
        const messages = [...ref.current.messages];
        const targetIdx = messages.findIndex((m) => m.id === agentMsgId);
        if (targetIdx !== -1 && messages[targetIdx].role === 'agent') {
          const existing = messages[targetIdx];
          messages[targetIdx] = {
            ...existing,
            metadata: {
              ...existing.metadata,
              reconnecting: isReconnecting,
              retryCount: isReconnecting ? attempt : undefined,
            },
          };
          ref.current = { ...ref.current, messages, lastUpdatedAt: Date.now() };
          if (visibleSessionIdRef.current === sessionId) {
            updateSessionState(sessionId, { messages });
          }
        }
      };

      // ---- Retry loop ----
      try {
        while (retryCount <= MAX_RETRIES) {
          let streamErrored = false;
          try {
            await fetchEventSource(`${API_URL}/a2a/app/run_sse`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
              },
              signal: abortController.signal,
              body: JSON.stringify({
                session_id: sessionId,
                user_id: userId,
                new_message: { parts: [{ text: message }] },
                agent_mode: agentMode,
              }),
              openWhenHidden: true,

              async onopen(response) {
                const contentType = response.headers.get('content-type') || '';
                if (response.ok && contentType.startsWith('text/event-stream')) return;
                if (
                  response.status >= 400 &&
                  response.status < 500 &&
                  response.status !== 429
                ) {
                  throw new Error(`Client error: ${response.status}`);
                }
                throw new Error(
                  `Unexpected response: ${response.status} ${response.statusText}`,
                );
              },

              onmessage(msg) {
                if (msg.event === 'ping') return;

                // Clear reconnecting indicator on first message after a retry
                if (retryCount > 0) {
                  setReconnectingIndicator(false, retryCount);
                }

                const parseResult = parseSSEEvent(msg.data, acc, agentDisplayName);
                if (parseResult.skipped) return;

                // ---- Handle error ----
                if (parseResult.errorText) {
                  hasError = true;
                  const ref = getActiveSessionRef(sessionId);
                  if (!ref?.current) return;

                  const errorMsg: Message = { role: 'system', text: `Error: ${parseResult.errorText}` };

                  // Check if the placeholder is still empty
                  const messages = [...ref.current.messages];
                  const placeholderIdx = messages.findIndex((m) => m.id === agentMsgId);
                  if (
                    placeholderIdx !== -1 &&
                    messages[placeholderIdx].role === 'agent' &&
                    messages[placeholderIdx].isThinking &&
                    !messages[placeholderIdx].text
                  ) {
                    messages.splice(placeholderIdx, 1);
                  }
                  messages.push(errorMsg);

                  ref.current = { ...ref.current, messages, lastUpdatedAt: Date.now() };

                  if (visibleSessionIdRef.current === sessionId) {
                    updateSessionState(sessionId, { messages });
                  }

                  // Execute error activity side effect (visibility-gated)
                  if (userId && visibleSessionIdRef.current === sessionId) {
                    const errorPayload = parseResult.sideEffects.find(
                      (e) => e.type === 'error_activity',
                    );
                    if (errorPayload) {
                      const p = errorPayload.payload as Record<string, unknown>;
                      dispatchWorkspaceActivity({
                        userId,
                        sessionId,
                        phase: 'error',
                        agentName: p.agentName as string | undefined,
                        text: p.text as string | undefined,
                        traces: p.traces as { type: 'thinking' | 'tool_use' | 'tool_output'; content: string; toolName?: string }[],
                      });
                    }
                  } else if (userId) {
                    // Queue error activity for background sessions
                    const errorPayload = parseResult.sideEffects.find(
                      (e) => e.type === 'error_activity',
                    );
                    if (errorPayload && ref?.current) {
                      ref.current.pendingActions.push({
                        type: 'workspace_activity',
                        payload: errorPayload.payload,
                      });
                    }
                  }
                  return;
                }

                // ---- Build updated agent message ----
                const ref = getActiveSessionRef(sessionId);
                if (!ref?.current) return;

                // Process widget through workspace defaults + persistence
                let processedWidget: WidgetDefinition | undefined;
                if (parseResult.widgetFound && validateWidgetDefinition(parseResult.widgetFound)) {
                  processedWidget = withWorkspaceDefaults(parseResult.widgetFound as WidgetDefinition);
                }

                const isVisible = visibleSessionIdRef.current === sessionId;

                // Build the updated message
                const updatedMsg: Message = {
                  id: agentMsgId,
                  role: 'agent',
                  text: parseResult.fullText || undefined,
                  agentName: acc.agentName,
                  traces: parseResult.traces,
                  isThinking: parseResult.isThinking,
                  ...(processedWidget ? { widget: processedWidget } : {}),
                  ...(parseResult.metadata ? { metadata: parseResult.metadata } : {}),
                };

                // Update the ref's messages array
                const messages = [...ref.current.messages];
                const targetIdx = messages.findIndex((m) => m.id === agentMsgId);
                if (targetIdx !== -1) {
                  messages[targetIdx] = updatedMsg;
                }

                ref.current = {
                  ...ref.current,
                  messages,
                  lastUpdatedAt: Date.now(),
                };

                if (isVisible) {
                  // Visible session: update React state for re-render
                  requestAnimationFrame(() => {
                    const latestRef = getActiveSessionRef(sessionId);
                    if (latestRef?.current) {
                      updateSessionState(sessionId, {
                        messages: latestRef.current.messages,
                      });
                    }
                  });

                  // Execute side effects immediately for visible session
                  if (userId) {
                    for (const effect of parseResult.sideEffects) {
                      if (effect.type === 'save_widget' && processedWidget) {
                        const isMedia =
                          processedWidget.type === 'image' ||
                          processedWidget.type === 'video' ||
                          processedWidget.type === 'video_spec';
                        if (
                          !isMedia &&
                          processedWidget.type !== 'morning_briefing'
                        ) {
                          const widgetAny = processedWidget as { id?: string };
                          if (!widgetAny.id) {
                            const saved = widgetServiceRef.current.saveWidget(
                              userId,
                              sessionId,
                              processedWidget,
                              false,
                            );
                            if (saved) {
                              widgetAny.id = saved.id;
                            }
                          }
                        }
                      } else if (effect.type === 'focus_widget' && processedWidget) {
                        dispatchFocusWidget(processedWidget, userId);
                      } else if (effect.type === 'workspace_activity') {
                        const p = effect.payload as Record<string, unknown>;
                        dispatchWorkspaceActivity({
                          userId,
                          sessionId,
                          phase: 'running',
                          agentName: p.agentName as string | undefined,
                          text: p.text as string | undefined,
                          traces: p.traces as { type: 'thinking' | 'tool_use' | 'tool_output'; content: string; toolName?: string }[],
                        });
                      }
                    }
                  }
                } else {
                  // Background session: queue side effects, don't trigger re-renders
                  const pending: PendingSessionAction[] = [];
                  const rawWidgets: RawWidgetData[] = [];

                  for (const effect of parseResult.sideEffects) {
                    if (effect.type === 'save_widget' && processedWidget) {
                      rawWidgets.push({
                        widget: processedWidget,
                        messageIndex: targetIdx !== -1 ? targetIdx : messages.length - 1,
                      });
                    } else if (
                      effect.type === 'focus_widget' ||
                      effect.type === 'workspace_activity'
                    ) {
                      pending.push({
                        type: effect.type as 'focus_widget' | 'workspace_activity',
                        payload: effect.payload,
                      });
                    }
                  }

                  if (pending.length > 0 || rawWidgets.length > 0) {
                    ref.current = {
                      ...ref.current,
                      pendingActions: [...ref.current.pendingActions, ...pending],
                      rawWidgets: [...ref.current.rawWidgets, ...rawWidgets],
                    };
                  }
                }
              },

              onclose() {
                // Normal close — handled in finally
              },

              onerror(err) {
                // Always throw so fetchEventSource stops its own internal retry;
                // the outer retry loop handles backoff and reconnection.
                streamErrored = true;
                throw err;
              },
            });

            // fetchEventSource resolved cleanly — break out of the retry loop
            break;
          } catch (innerErr) {
            // User-initiated abort — propagate immediately, no retry
            if (abortController.signal.aborted) {
              throw innerErr;
            }

            // 4xx client errors are not retryable
            const isClientError =
              innerErr instanceof Error &&
              innerErr.message.startsWith('Client error:');
            if (isClientError) {
              throw innerErr;
            }

            retryCount++;

            if (retryCount > MAX_RETRIES) {
              // All retries exhausted — propagate to the outer catch
              throw innerErr;
            }

            // Show inline reconnecting indicator on the last agent message
            if (streamErrored) {
              setReconnectingIndicator(true, retryCount);
            }

            const delayMs = RETRY_DELAYS[retryCount - 1];
            console.warn(
              `[SSE] Stream dropped, retry ${retryCount}/${MAX_RETRIES} in ${delayMs}ms`,
            );

            // Wait with exponential backoff before next attempt
            await new Promise<void>((resolve) =>
              setTimeout(resolve, delayMs),
            );
          }
        }
      } catch (err) {
        hasError = true;
        const ref = getActiveSessionRef(sessionId);
        if (!ref?.current) return;

        const isNetworkError =
          (err instanceof TypeError &&
            (err.message === 'Failed to fetch' || err.message === 'Load failed')) ||
          (err instanceof Error &&
            (err.message.includes('fetch') || err.message.includes('NetworkError')));
        const isUnauthorized = err instanceof Error && err.message.includes('401');
        const isAbort = err instanceof DOMException && err.name === 'AbortError';

        if (isAbort) {
          // User-initiated abort — no error message needed
        } else {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          let errorText: string;
          if (isUnauthorized) {
            errorText =
              'Error: Your session has expired or is invalid. Please refresh the page or log in again.';
          } else if (isNetworkError) {
            errorText = `Error: Cannot reach the backend at ${apiUrl}. Ensure it's running and NEXT_PUBLIC_API_URL is correct.`;
          } else {
            errorText = 'Error: Failed to connect to Pikar AI. Please try again.';
          }

          const messages = [...ref.current.messages];
          const targetIdx = messages.findIndex((m) => m.id === agentMsgId);
          if (
            targetIdx !== -1 &&
            messages[targetIdx].role === 'agent' &&
            messages[targetIdx].isThinking &&
            !messages[targetIdx].text &&
            !messages[targetIdx].widget
          ) {
            messages.splice(targetIdx, 1);
          }
          messages.push({ role: 'system', text: errorText });

          ref.current = { ...ref.current, messages, status: 'error', lastUpdatedAt: Date.now() };

          if (visibleSessionIdRef.current === sessionId) {
            updateSessionState(sessionId, { messages, status: 'error' });
          }

          onStreamError?.(sessionId, errorText);

          if (userId && visibleSessionIdRef.current === sessionId) {
            dispatchWorkspaceActivity({
              userId,
              sessionId,
              phase: 'error',
              agentName: acc.agentName,
              text: acc.agentText || undefined,
              traces: acc.currentTraces as { type: 'thinking' | 'tool_use' | 'tool_output'; content: string; toolName?: string }[],
            });
          } else if (userId && ref?.current) {
            ref.current.pendingActions.push({
              type: 'workspace_activity',
              payload: {
                agentName: acc.agentName,
                text: acc.agentText || undefined,
                traces: acc.currentTraces,
              },
            });
          }
        }
      } finally {
        const ref = getActiveSessionRef(sessionId);
        if (!ref?.current) return;

        // Finalize the agent message — clear isThinking
        const messages = [...ref.current.messages];
        const targetIdx = messages.findIndex((m) => m.id === agentMsgId);
        if (targetIdx !== -1 && messages[targetIdx].role === 'agent') {
          messages[targetIdx] = {
            ...messages[targetIdx],
            isThinking: false,
          };
        }

        const isBackground = visibleSessionIdRef.current !== sessionId;

        ref.current = {
          ...ref.current,
          status: hasError ? 'error' : 'idle',
          abortController: null,
          messages,
          hasUnread: isBackground ? true : ref.current.hasUnread,
          lastUpdatedAt: Date.now(),
        };

        // Always push final state to React — the stream is done
        updateSessionState(sessionId, {
          status: hasError ? 'error' : 'idle',
          abortController: null,
          messages,
          hasUnread: isBackground ? true : ref.current.hasUnread,
        });

        if (userId && !hasError) {
          dispatchWorkspaceActivity({
            userId,
            sessionId,
            phase: 'completed',
            agentName: acc.agentName,
            text: acc.agentText || undefined,
            traces: acc.currentTraces as { type: 'thinking' | 'tool_use' | 'tool_output'; content: string; toolName?: string }[],
          });
        }

        const finalText = targetIdx !== -1 ? (messages[targetIdx].text ?? '') : '';
        onStreamComplete?.(sessionId, finalText);
      }
    },
    [getActiveSessionRef, updateSessionState, supabase, visibleSessionId],
  );

  return { startStream, stopStream };
}
