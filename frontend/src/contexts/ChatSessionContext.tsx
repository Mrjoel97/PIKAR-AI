'use client';

import React, { createContext, useContext, useState, useEffect, useLayoutEffect, useCallback, useRef } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { dispatchFocusWidget } from '@/services/widgetDisplay';

// Types
export interface ChatSession {
  id: string;
  title: string;
  preview?: string;
  createdAt: Date;
  updatedAt: Date;
}

interface ChatSessionContextType {
  // Current session
  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
  /** True after we've read currentSessionId from localStorage (so chat can safely use/persist id) */
  sessionRestored: boolean;

  // Session history
  sessions: ChatSession[];
  isLoadingSessions: boolean;

  // Actions
  createNewChat: () => void;
  selectChat: (sessionId: string) => void;
  deleteChat: (sessionId: string) => Promise<void>;
  clearAllChats: () => Promise<void>;
  refreshSessions: () => Promise<void>;
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>;
  updateSessionPreview: (sessionId: string, preview: string) => Promise<void>;
  /** Add a session to the list immediately (e.g. when first message is sent) so history/dropdown show it */
  addSessionOptimistic: (session: ChatSession) => void;

  // For ChatInterface callbacks
  goToHistoryPage: () => void;
}

export const ChatSessionContext = createContext<ChatSessionContextType | null>(null);

export function useChatSession() {
  const context = useContext(ChatSessionContext);
  if (!context) {
    throw new Error('useChatSession must be used within a ChatSessionProvider');
  }
  return context;
}

interface ChatSessionProviderProps {
  children: React.ReactNode;
}

const SESSION_STORAGE_KEY = 'pikar_current_session_id';

export function ChatSessionProvider({ children }: ChatSessionProviderProps) {
  const router = useRouter();
  const supabase = createClient();

  // Restore last active session from localStorage so the chat survives page reloads.
  // Initialize as null; we restore from localStorage in useEffect so SSR/hydration don't lose the value.
  const [currentSessionId, setCurrentSessionIdRaw] = useState<string | null>(null);
  const [sessionRestored, setSessionRestored] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);

  // Restore session id from localStorage before paint (client-only) so chat always gets correct initialSessionId.
  useLayoutEffect(() => {
    try {
      const stored = localStorage.getItem(SESSION_STORAGE_KEY);
      if (stored) setCurrentSessionIdRaw(stored);
    } catch {
      // ignore
    }
    setSessionRestored(true);
  }, []);

  // Track if we've initialized
  const initializedRef = useRef(false);

  // Wrap setCurrentSessionId to also persist to localStorage
  const setCurrentSessionId = useCallback((id: string | null) => {
    setCurrentSessionIdRaw(id);
    try {
      if (id) {
        localStorage.setItem(SESSION_STORAGE_KEY, id);
      } else {
        localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    } catch {
      // localStorage not available (SSR, private browsing, etc.) — ignore
    }
  }, []);

  // Get current user
  useEffect(() => {
    const getUser = async () => {
      const { data } = await supabase.auth.getUser();
      if (data.user) {
        setUserId(data.user.id);
      }
    };
    getUser();
  }, [supabase]);

  // Fetch sessions from database
  const fetchSessions = useCallback(async () => {
    if (!userId) return;

    try {
      setIsLoadingSessions(true);

      const { data, error } = await supabase
        .from('sessions')
        .select('session_id, state, created_at, updated_at')
        .eq('user_id', userId)
        .eq('app_name', 'agents')
        .order('updated_at', { ascending: false });

      if (error) {
        console.error('Error fetching sessions:', error);
        return;
      }

      // Transform to ChatSession format
      const chatSessions: ChatSession[] = (data || []).map((session: { session_id: string; state?: { title?: string; lastMessage?: string }; created_at: string; updated_at: string }) => ({
        id: session.session_id,
        title: session.state?.title || extractTitleFromSessionId(session.session_id),
        preview: session.state?.lastMessage || undefined,
        createdAt: new Date(session.created_at),
        updatedAt: new Date(session.updated_at),
      }));

      // For sessions missing a title (only have date fallback), fetch first user message
      const sessionsNeedingTitle = chatSessions.filter(
        s => !s.title || s.title.startsWith('Chat from') || s.title === 'Untitled Chat'
      );

      if (sessionsNeedingTitle.length > 0) {
        const sessionIds = sessionsNeedingTitle.map(s => s.id);

        // Fetch first user message for each session (user_id for RLS and correct rows)
        const { data: firstMessages } = await supabase
          .from('session_events')
          .select('session_id, event_data')
          .in('session_id', sessionIds)
          .eq('app_name', 'agents')
          .eq('user_id', userId)
          .is('superseded_by', null)
          .order('event_index', { ascending: true });

        if (firstMessages) {
          // Group by session and pick the first user message (support multiple event_data shapes)
          const titleMap = new Map<string, string>();
          for (const event of firstMessages) {
            if (titleMap.has(event.session_id)) continue;
            const eventData = event.event_data;
            if (!eventData) continue;
            // ADK may store source as 'user', or role/author as 'user'/'human'
            const isUser = eventData.source === 'user' || eventData.role === 'user' || eventData.author === 'user' || eventData.source === 'human';
            if (!isUser) continue;
            let text = '';
            if (eventData.content?.parts && Array.isArray(eventData.content.parts)) {
              text = eventData.content.parts.map((p: any) => (p?.text ?? '')).join('');
            } else if (typeof eventData.content === 'string') {
              text = eventData.content;
            } else if (eventData.text) {
              text = eventData.text;
            }
            const trimmed = (text || '').trim();
            if (trimmed) {
              const title = trimmed.length > 60 ? trimmed.substring(0, 60) + '...' : trimmed;
              titleMap.set(event.session_id, title);
            }
          }

          // Update sessions with extracted titles
          for (const session of chatSessions) {
            const extractedTitle = titleMap.get(session.id);
            if (extractedTitle && (!session.title || session.title.startsWith('Chat from') || session.title === 'Untitled Chat')) {
              session.title = extractedTitle;

              // Also persist the title to DB so we don't need to re-fetch next time
              // Fire and forget - don't block the UI
              supabase
                .from('sessions')
                .select('state')
                .eq('session_id', session.id)
                .eq('user_id', userId)
                .eq('app_name', 'agents')
                .single()
                .then(({ data: sessionRow }: { data: { state?: { title?: string } } | null }) => {
                  const currentState = sessionRow?.state || {};
                  supabase
                    .from('sessions')
                    .update({ state: { ...currentState, title: extractedTitle }, updated_at: new Date().toISOString() })
                    .eq('session_id', session.id)
                    .eq('user_id', userId)
                    .eq('app_name', 'agents')
                    .then(() => { });
                });
            }
          }
        }

        // Also fetch last messages for preview for sessions missing it
        const sessionsNeedingPreview = chatSessions.filter(s => !s.preview);
        if (sessionsNeedingPreview.length > 0) {
          const previewIds = sessionsNeedingPreview.map(s => s.id);
          const { data: lastMessages } = await supabase
            .from('session_events')
            .select('session_id, event_data')
            .in('session_id', previewIds)
            .eq('app_name', 'agents')
            .is('superseded_by', null)
            .order('event_index', { ascending: false });

          if (lastMessages) {
            const previewMap = new Map<string, string>();
            for (const event of lastMessages) {
              if (previewMap.has(event.session_id)) continue;
              const eventData = event.event_data;
              if (!eventData) continue;
              const isAgent = eventData.source === 'model' || eventData.source === 'agent' || (eventData.source && eventData.source !== 'user' && eventData.source !== 'system') || eventData.role === 'agent' || eventData.author === 'model';
              if (!isAgent) continue;
              let text = '';
              if (eventData.content?.parts && Array.isArray(eventData.content.parts)) {
                text = eventData.content.parts.map((p: any) => (p?.text ?? '')).join('');
              } else if (typeof eventData.content === 'string') {
                text = eventData.content;
              } else if (eventData.text) {
                text = eventData.text;
              }
              const trimmed = (text || '').trim();
              if (trimmed) {
                previewMap.set(event.session_id, trimmed.length > 100 ? trimmed.substring(0, 100) + '...' : trimmed);
              }
            }

            for (const session of chatSessions) {
              const preview = previewMap.get(session.id);
              if (preview && !session.preview) {
                session.preview = preview;
              }
            }
          }
        }
      }

      setSessions(chatSessions);

      // Auto-select the most recent session on first load if none selected
      if (!initializedRef.current && chatSessions.length > 0 && !currentSessionId) {
        // Don't auto-select, let user start fresh or pick from history
        initializedRef.current = true;
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setIsLoadingSessions(false);
    }
  }, [userId, supabase, currentSessionId]);

  // Load sessions when user is available
  useEffect(() => {
    if (userId) {
      fetchSessions();
    }
  }, [userId, fetchSessions]);

  // Create a new chat session
  const createNewChat = useCallback(() => {
    // Generate a new session ID
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    setCurrentSessionId(newSessionId);
    // Clear workspace focus so old content doesn't linger
    dispatchFocusWidget(null, userId ?? '');
  }, [userId, setCurrentSessionId]);

  // Select an existing chat
  const selectChat = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
  }, []);

  // Delete a chat session
  const deleteChat = useCallback(async (sessionId: string) => {
    if (!userId) return;

    try {
      // Delete session events first
      await supabase
        .from('session_events')
        .delete()
        .eq('session_id', sessionId);

      await supabase
        .from('workspace_items')
        .delete()
        .eq('session_id', sessionId)
        .eq('user_id', userId);

      // Delete the session
      const { error } = await supabase
        .from('sessions')
        .delete()
        .eq('session_id', sessionId)
        .eq('user_id', userId);

      if (error) {
        console.error('Error deleting session:', error);
        throw error;
      }

      // Update local state
      setSessions(prev => prev.filter(s => s.id !== sessionId));

      // If deleted current session, clear it
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
      throw err;
    }
  }, [userId, supabase, currentSessionId]);

  // Clear all chats
  const clearAllChats = useCallback(async () => {
    if (!userId) return;

    try {
      // Delete all session events for user
      await supabase
        .from('session_events')
        .delete()
        .eq('user_id', userId);

      await supabase
        .from('workspace_items')
        .delete()
        .eq('user_id', userId);

      // Delete all sessions for user
      const { error } = await supabase
        .from('sessions')
        .delete()
        .eq('user_id', userId);

      if (error) {
        console.error('Error clearing sessions:', error);
        throw error;
      }

      // Clear local state
      setSessions([]);
      setCurrentSessionId(null);
    } catch (err) {
      console.error('Failed to clear all sessions:', err);
      throw err;
    }
  }, [userId, supabase]);

  const AGENTS_APP_NAME = 'agents';

  // Update session title
  const updateSessionTitle = useCallback(async (sessionId: string, title: string) => {
    if (!userId) return;

    try {
      // First get current state
      const { data: session } = await supabase
        .from('sessions')
        .select('state')
        .eq('session_id', sessionId)
        .eq('user_id', userId)
        .eq('app_name', AGENTS_APP_NAME)
        .single();

      const currentState = session?.state || {};

      // Update with new title
      const { error } = await supabase
        .from('sessions')
        .update({
          state: { ...currentState, title },
          updated_at: new Date().toISOString()
        })
        .eq('session_id', sessionId)
        .eq('user_id', userId)
        .eq('app_name', AGENTS_APP_NAME);

      if (error) {
        console.error('Error updating session title:', error);
        throw error;
      }

      // Update local state
      setSessions(prev => prev.map(s =>
        s.id === sessionId ? { ...s, title } : s
      ));
    } catch (err) {
      console.error('Failed to update session title:', err);
      throw err;
    }
  }, [userId, supabase]);

  // Update session preview (last message)
  const updateSessionPreview = useCallback(async (sessionId: string, preview: string) => {
    if (!userId || !preview) return;

    try {
      const safePreview = typeof preview === 'string' ? preview : JSON.stringify(preview);
      const truncatedPreview = safePreview.length > 100 ? safePreview.substring(0, 100) + '...' : safePreview;

      // Get current state
      const { data: session } = await supabase
        .from('sessions')
        .select('state')
        .eq('session_id', sessionId)
        .eq('user_id', userId)
        .eq('app_name', AGENTS_APP_NAME)
        .single();

      const currentState = session?.state || {};

      // Update with new preview
      const { error } = await supabase
        .from('sessions')
        .update({
          state: { ...currentState, lastMessage: truncatedPreview },
          updated_at: new Date().toISOString()
        })
        .eq('session_id', sessionId)
        .eq('user_id', userId)
        .eq('app_name', AGENTS_APP_NAME);

      if (error) {
        console.error('Error updating session preview:', error.message || error);
        return;
      }

      // Update local state
      setSessions(prev => prev.map(s =>
        s.id === sessionId ? { ...s, preview: truncatedPreview } : s
      ));
    } catch (err: any) {
      console.error('Failed to update session preview:', err.message || err);
    }
  }, [userId, supabase]);

  /** Add session to list immediately so it appears in history/dropdown before server round-trip */
  const addSessionOptimistic = useCallback((session: ChatSession) => {
    setSessions(prev => {
      const exists = prev.some(s => s.id === session.id);
      if (exists) return prev.map(s => s.id === session.id ? { ...session, updatedAt: s.updatedAt > session.updatedAt ? s.updatedAt : session.updatedAt } : s);
      return [session, ...prev];
    });
  }, []);

  // Navigate to history page
  const goToHistoryPage = useCallback(() => {
    router.push('/dashboard/history');
  }, [router]);

  const value: ChatSessionContextType = {
    currentSessionId,
    setCurrentSessionId,
    sessionRestored,
    sessions,
    isLoadingSessions,
    createNewChat,
    selectChat,
    deleteChat,
    clearAllChats,
    refreshSessions: fetchSessions,
    updateSessionTitle,
    updateSessionPreview,
    addSessionOptimistic,
    goToHistoryPage,
  };

  return (
    <ChatSessionContext.Provider value={value}>
      {children}
    </ChatSessionContext.Provider>
  );
}

// Helper function to extract a readable title from session ID
function extractTitleFromSessionId(sessionId: string): string {
  // session-1234567890123-abcdefg -> "Chat from Jan 1, 2024"
  const match = sessionId.match(/session-(\d+)/);
  if (match) {
    const timestamp = parseInt(match[1], 10);
    const date = new Date(timestamp);
    if (!isNaN(date.getTime())) {
      return `Chat from ${date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
      })}`;
    }
  }
  return 'Untitled Chat';
}
