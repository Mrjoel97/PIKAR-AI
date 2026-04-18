// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useCallback, useRef, useEffect } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { createClient } from '@/lib/supabase/client';

/**
 * Data describing a pending confirmation action from the AdminAgent.
 * The token is consumed exactly once server-side (UUID + atomic UPDATE).
 */
export interface ConfirmationData {
  token: string;
  action_details: {
    action: string;
    risk_level: 'low' | 'medium' | 'high';
    description: string;
  };
}

/**
 * A single message in the admin chat thread.
 * Confirmation messages carry a ConfirmationData payload that renders
 * a ConfirmationCard in the chat panel.
 */
export interface AdminMessage {
  id?: string;
  role: 'user' | 'agent' | 'system';
  text?: string;
  confirmation?: ConfirmationData;
  isThinking?: boolean;
}

/**
 * A chat session summary returned by GET /admin/chat/sessions.
 */
export interface AdminChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface UseAdminChatOptions {
  initialSessionId?: string;
}

function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === 'AbortError') ||
    (error instanceof Error && error.name === 'AbortError')
  );
}

export function useAdminChat(options: UseAdminChatOptions = {}) {
  const { initialSessionId } = options;

  const [messages, setMessages] = useState<AdminMessage[]>([
    {
      id: 'welcome',
      role: 'agent',
      text: '',
      isThinking: true,
    },
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string>(
    initialSessionId ?? `admin-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  );
  const [pendingConfirmation, setPendingConfirmation] = useState<ConfirmationData | null>(null);
  const [sessions, setSessions] = useState<AdminChatSession[]>([]);
  const [isConfirming, setIsConfirming] = useState(false);

  const isStreamingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const supabase = createClient();

  /** Retrieve the current user's Bearer token. */
  const getToken = useCallback(async (): Promise<string | null> => {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }, [supabase]);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  /** Fetch the list of admin chat sessions. */
  const loadSessions = useCallback(async () => {
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/admin/chat/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = (await res.json()) as AdminChatSession[];
        setSessions(data);
      }
    } catch {
      // Silently ignore — sessions list is non-critical
    }
  }, [getToken, API_URL]);

  /** Load message history for a given session. */
  const loadHistory = useCallback(async (sessionId: string) => {
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/admin/chat/history/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;

      const rows = (await res.json()) as Array<{
        id: string;
        role: 'user' | 'agent' | 'system';
        content: string;
        metadata?: { requires_confirmation?: boolean; confirmation_data?: ConfirmationData };
        created_at: string;
      }>;

      if (rows.length === 0) return;

      const historyMessages: AdminMessage[] = rows.map((row) => ({
        id: row.id,
        role: row.role,
        text: row.content,
        confirmation: row.metadata?.confirmation_data,
      }));

      setMessages(historyMessages);
      setCurrentSessionId(sessionId);
    } catch {
      // Silently ignore history load failures
    }
  }, [getToken, API_URL]);

  /**
   * Fetch the real-time health status and build a dynamic greeting message.
   * Falls back to a static greeting if the monitoring API is unavailable.
   */
  const fetchGreeting = useCallback(async () => {
    const staticGreeting =
      'Hello! I am the Pikar Admin Agent. How can I help you manage the platform today?';

    try {
      const token = await getToken();
      if (!token) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === 'welcome' ? { ...m, text: staticGreeting, isThinking: false } : m
          )
        );
        return;
      }

      const res = await fetch(`${API_URL}/admin/monitoring/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = (await res.json()) as {
        endpoints: Array<{ name: string; current_status: string }>;
        open_incidents: Array<{ id: string; endpoint: string; incident_type: string }>;
        latest_check_at: string | null;
      };

      const endpoints = data.endpoints ?? [];
      const openIncidents = data.open_incidents ?? [];

      const unhealthy = endpoints.filter(
        (ep) => ep.current_status !== 'healthy' && ep.current_status !== 'unknown'
      );
      const unknown = endpoints.filter((ep) => ep.current_status === 'unknown');
      const healthyCount = endpoints.filter((ep) => ep.current_status === 'healthy').length;

      let statusSummary: string;
      if (openIncidents.length > 0) {
        const affected = [...new Set(openIncidents.map((i) => i.endpoint))].join(', ');
        statusSummary = `There are ${openIncidents.length} active incident(s) affecting ${affected}.`;
      } else if (unhealthy.length > 0) {
        const names = unhealthy.map((ep) => ep.name).join(', ');
        statusSummary = `Warning: ${names} reporting issues.`;
      } else if (unknown.length === endpoints.length) {
        statusSummary = 'No health check data available yet.';
      } else {
        statusSummary = `All ${healthyCount} endpoint(s) are healthy.`;
      }

      const greetingText = `Hello! I'm the Pikar Admin Agent. System status: ${statusSummary} How can I help you today?`;

      setMessages((prev) =>
        prev.map((m) =>
          m.id === 'welcome' ? { ...m, text: greetingText, isThinking: false } : m
        )
      );
    } catch {
      // Graceful degradation — show static greeting if monitoring API is unavailable
      setMessages((prev) =>
        prev.map((m) =>
          m.id === 'welcome' ? { ...m, text: staticGreeting, isThinking: false } : m
        )
      );
    }
  }, [getToken, API_URL]);

  /** Send a message and stream the SSE response. */
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isStreamingRef.current) return;

    setError(null);
    const userMsgId = `user-${Date.now()}`;
    setMessages((prev) => [...prev, { id: userMsgId, role: 'user', text }]);

    const agentMsgId = `agent-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: agentMsgId, role: 'agent', text: '', isThinking: true },
    ]);

    isStreamingRef.current = true;
    setIsStreaming(true);

    try {
      const token = await getToken();
      if (!token) throw new Error('Not authenticated');

      let currentText = '';
      let detectedConfirmation: ConfirmationData | null = null;
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      await fetchEventSource(`${API_URL}/admin/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        signal: abortController.signal,
        openWhenHidden: true,
        body: JSON.stringify({
          session_id: currentSessionId,
          message: text,
        }),
        async onopen(response) {
          const contentType = response.headers.get('content-type') || '';
          if (response.ok && contentType.startsWith('text/event-stream')) return;
          if (response.status === 401) throw new Error('Client error: 401');
          if (response.status === 403) throw new Error('Client error: 403');
          if (response.status >= 400 && response.status < 500) {
            throw new Error(`Client error: ${response.status}`);
          }
          throw new Error(`Server error: ${response.status}`);
        },
        onmessage(msg) {
          if (msg.event === 'ping') return;
          try {
            const data = JSON.parse(msg.data) as {
              text?: string;
              content?: string;
              requires_confirmation?: boolean;
              confirmation_data?: ConfirmationData;
              error?: string;
              session_id?: string;
            };

            if (data.error) {
              setMessages((prev) => {
                const next = [...prev];
                const idx = next.findIndex((m) => m.id === agentMsgId);
                if (idx !== -1) next.splice(idx, 1);
                return [...next, { role: 'system', text: `Error: ${data.error}` }];
              });
              return;
            }

            if (data.session_id && data.session_id !== currentSessionId) {
              setCurrentSessionId(data.session_id);
            }

            const chunk = data.text ?? data.content ?? '';
            if (chunk) currentText += chunk;

            if (data.requires_confirmation && data.confirmation_data) {
              detectedConfirmation = data.confirmation_data;
            }

            setMessages((prev) => {
              const next = [...prev];
              const idx = next.findIndex((m) => m.id === agentMsgId);
              if (idx !== -1) {
                next[idx] = {
                  ...next[idx],
                  text: currentText || undefined,
                  confirmation: detectedConfirmation ?? undefined,
                  isThinking: !currentText && !detectedConfirmation,
                };
              }
              return next;
            });
          } catch {
            // Ignore parse errors on individual chunks
          }
        },
        onclose() {
          // Normal SSE close
        },
        onerror(err) {
          if (abortController.signal.aborted || isAbortError(err)) {
            return;
          }
          throw err;
        },
      });

      if (detectedConfirmation) {
        setPendingConfirmation(detectedConfirmation);
      }
    } catch (err) {
      if (isAbortError(err)) {
        return;
      }

      const isAuth = err instanceof Error && err.message.includes('401');
      const isNetwork =
        err instanceof TypeError &&
        (err.message.includes('fetch') || err.message.includes('Failed to fetch'));

      const errorText = isAuth
        ? 'Session expired. Please refresh the page.'
        : isNetwork
        ? `Cannot reach backend at ${API_URL}. Ensure it is running.`
        : 'Failed to connect to Admin Agent. Please try again.';

      setError(errorText);
      setMessages((prev) => {
        const next = [...prev];
        const idx = next.findIndex((m) => m.id === agentMsgId);
        if (idx !== -1) {
          if (next[idx].isThinking && !next[idx].text) {
            next.splice(idx, 1);
          } else {
            next[idx] = { ...next[idx], isThinking: false };
          }
        }
        return [...next, { role: 'system', text: errorText }];
      });
    } finally {
      isStreamingRef.current = false;
      setIsStreaming(false);
      abortControllerRef.current = null;

      setMessages((prev) => {
        const next = [...prev];
        const idx = next.findIndex((m) => m.id === agentMsgId);
        if (idx !== -1 && next[idx].isThinking) {
          next[idx] = { ...next[idx], isThinking: false };
        }
        return next;
      });
    }
  }, [getToken, API_URL, currentSessionId]);

  /**
   * Submit a confirmation token to execute a pending action.
   * Sends POST /admin/chat with confirmation_token.
   * Clears pendingConfirmation immediately (single-use protection).
   */
  const confirmAction = useCallback(async (token: string) => {
    if (isConfirming) return;
    setIsConfirming(true);
    setPendingConfirmation(null);

    const agentMsgId = `agent-confirm-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: agentMsgId, role: 'agent', text: '', isThinking: true },
    ]);

    isStreamingRef.current = true;
    setIsStreaming(true);

    try {
      const authToken = await getToken();
      if (!authToken) throw new Error('Not authenticated');

      let currentText = '';
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      await fetchEventSource(`${API_URL}/admin/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        signal: abortController.signal,
        openWhenHidden: true,
        body: JSON.stringify({
          session_id: currentSessionId,
          message: '',
          confirmation_token: token,
        }),
        async onopen(response) {
          if (response.ok) return;
          throw new Error(`Server error: ${response.status}`);
        },
        onmessage(msg) {
          if (msg.event === 'ping') return;
          try {
            const data = JSON.parse(msg.data) as { text?: string; content?: string };
            const chunk = data.text ?? data.content ?? '';
            if (chunk) currentText += chunk;
            setMessages((prev) => {
              const next = [...prev];
              const idx = next.findIndex((m) => m.id === agentMsgId);
              if (idx !== -1) {
                next[idx] = { ...next[idx], text: currentText || undefined, isThinking: !currentText };
              }
              return next;
            });
          } catch {
            // Ignore
          }
        },
        onclose() {},
        onerror(err) {
          if (abortController.signal.aborted || isAbortError(err)) {
            return;
          }
          throw err;
        },
      });
    } catch (err) {
      if (isAbortError(err)) {
        return;
      }

      setMessages((prev) => [
        ...prev,
        { role: 'system', text: 'Action confirmation failed. Please try again.' },
      ]);
    } finally {
      isStreamingRef.current = false;
      setIsStreaming(false);
      setIsConfirming(false);
      abortControllerRef.current = null;
      setMessages((prev) => {
        const next = [...prev];
        const idx = next.findIndex((m) => m.id === agentMsgId);
        if (idx !== -1 && next[idx].isThinking) {
          next[idx] = { ...next[idx], isThinking: false };
        }
        return next;
      });
    }
  }, [getToken, API_URL, currentSessionId, isConfirming]);

  /** Cancel a pending confirmation without executing it. */
  const rejectAction = useCallback(() => {
    setPendingConfirmation(null);
    setMessages((prev) => [...prev, { role: 'system', text: 'Action cancelled.' }]);
  }, []);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (initialSessionId) {
      loadHistory(initialSessionId);
    } else {
      loadSessions();
      fetchGreeting();
    }
  }, [initialSessionId, loadHistory, loadSessions, fetchGreeting]);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    confirmAction,
    rejectAction,
    pendingConfirmation,
    isConfirming,
    sessions,
    loadHistory,
    currentSessionId,
  };
}

