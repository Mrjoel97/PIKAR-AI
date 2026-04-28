'use client'
import React, { useEffect, useRef, useCallback, useLayoutEffect, useMemo, useState } from 'react'
import { Send, Bot, User, Loader2, Paperclip, Mic, MicOff, X, FileText, Image, FileSpreadsheet, File as FileIcon, ChevronDown, Zap, Users, HelpCircle, Plus, Clock, MoreVertical, Trash2, XSquare, Brain, Square, LayoutGrid } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

import remarkGfm from 'remark-gfm'
import { useAgentChat, AgentMode } from '@/hooks/useAgentChat'
import { WidgetContainer } from '@/components/widgets/WidgetRegistry'
import { MessageItem } from './MessageItem'; // NEW import
import { ThoughtProcess } from '@/components/chat/ThoughtProcess'
import { FileDropZone } from '@/components/chat/FileDropZone'
import { SmartUploadToast, SmartUploadResult } from '@/components/chat/SmartUploadToast'
import { useFileUpload } from '@/hooks/useFileUpload'
import { useTextToSpeech } from '@/hooks/useTextToSpeech';

import { SuggestionChips } from './SuggestionChips'
import { WorkflowLauncher } from './WorkflowLauncher'
import { TemplateGallery } from './TemplateGallery'
import { searchWorkflows, type WorkflowMatch, type ContentTemplate } from '@/services/suggestions'
import { createWorkflowTemplate, startWorkflow } from '@/services/workflows'
import { WidgetDisplayService, dispatchFocusWidget, dispatchWorkspaceActivity, dispatchWorkspaceWidget, isWorkspaceCanvasWidget } from '@/services/widgetDisplay'
import { extractMessageMetadataFromEvent } from '@/lib/chatMetadata'
import type { WidgetDefinition } from '@/types/widgets'
import { usePresence } from '@/hooks/usePresence'
import { useRealtimeSession } from '@/hooks/useRealtimeSession'
import { useSessionControl } from '@/contexts/SessionControlContext'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { validateWidgetDefinition } from '@/types/widgets'
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition'
import { useVoiceSession, type VoiceSessionStartMode, type VoiceTranscriptTurn } from '@/hooks/useVoiceSession'
import VoiceBrainstormOverlay, { type BrainstormFinalizeResult } from '@/components/braindump/VoiceBrainstormOverlay'
import { createClient } from '@/lib/supabase/client'
import { usePersona } from '@/contexts/PersonaContext'
import { AGENT_BACKEND_URL } from '@/services/api'

interface ChatInterfaceProps {
  initialSessionId?: string;
  initialPrompt?: string;
  onInitialPromptSent?: () => void;
  className?: string;
  agentName?: string;
  chatHistory?: ChatHistoryItem[];
  onNewChat?: () => void;
  onSelectChat?: (id: string) => void;
  onClearAllChats?: () => void;
  onCloseAllChats?: () => void;
  onCloseChat?: () => void;
  onShowChatHistory?: () => void;
  onSessionStarted?: (sessionId: string, firstMessage: string) => void | Promise<void>;
  onAgentResponse?: (sessionId: string, agentMessage: string) => void | Promise<void>;
  onSessionIdReady?: (id: string) => void;
}

export interface ChatHistoryItem {
  id: string;
  title: string;
  timestamp: Date;
  preview?: string;
}

type BrainstormStartMode = VoiceSessionStartMode

const BRAINSTORM_SESSION_STORAGE_KEY = 'pikar:brainstorm-session:v1'
const BRAINSTORM_SESSION_MAX_AGE_MS = 6 * 60 * 60 * 1000

interface PersistedBrainstormSession {
  sessionId: string
  startMode: BrainstormStartMode
  transcript: string
  transcriptTurns: VoiceTranscriptTurn[]
  updatedAt: number
}

function isVoiceConnectionSupersededError(error: unknown): boolean {
  return error instanceof Error && error.message === 'Voice connection superseded';
}

export function ChatInterface({
  initialSessionId,
  initialPrompt,
  onInitialPromptSent,
  className,
  agentName,
  chatHistory = [],
  onNewChat,
  onSelectChat,
  onClearAllChats,
  onCloseAllChats,
  onCloseChat,
  onShowChatHistory,
  onSessionStarted,
  onAgentResponse,
  onSessionIdReady,
}: ChatInterfaceProps) {
  const initialPromptSentRef = useRef(false);
  const sessionIdNotifiedRef = useRef(false);
  const handledTranscriptVersionRef = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const widgetService = useRef(new WidgetDisplayService());

  const { messages, sendMessage, stopGeneration, addMessage, isStreaming, toggleWidgetMinimized, isLoadingHistory, getSessionId } = useAgentChat({
    initialSessionId,
    customAgentName: agentName,
    onSessionStarted,
    onAgentResponse
  });

  // Multi-session hooks
  const { visibleSessionId } = useSessionControl();
  const { activeSessions, updateSessionState } = useSessionMap();

  // Ref to the scrollable messages container for save/restore
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const { uploadFile, uploadFileToVault, isUploading: isFileUploadUploading, uploadError } = useFileUpload();
  const [isBrainDumpUploading, setIsBrainDumpUploading] = useState(false);
  const [isFinalizingBrainstorm, setIsFinalizingBrainstorm] = useState(false);
  const [isBrainstorming, setIsBrainstorming] = useState(false);
  const [finalizeResult, setFinalizeResult] = useState<BrainstormFinalizeResult | null>(null);

  // Smart upload (Context Sniffer) state
  const [smartUploadResult, setSmartUploadResult] = useState<SmartUploadResult | null>(null);
  const [isSmartUploading, setIsSmartUploading] = useState(false);
  // Keep the original file around so we can still use the regular upload for the agent message
  const [smartUploadFile, setSmartUploadFile] = useState<File | null>(null);

  // Stable ref for auto-finalize (used by both client timer and server timeout)
  const isFinalizingRef = useRef(false);
  const concludeRef = useRef<() => void>(() => {});
  const isBrainstormingRef = useRef(isBrainstorming);
  const brainstormStartModeRef = useRef<BrainstormStartMode>('resume');
  const brainstormConnectRequestRef = useRef(0);
  const restoreAttemptedRef = useRef(false);
  useEffect(() => { isBrainstormingRef.current = isBrainstorming; }, [isBrainstorming]);

  // Gemini Live API voice session for brainstorming
  const voiceSession = useVoiceSession({
    onSessionTimeout: useCallback(() => {
      // Server says 15:00 — auto-finalize if not already in progress
      if (isBrainstormingRef.current && !isFinalizingRef.current) {
        concludeRef.current();
      }
    }, []),
  });

  // TTS Hook — auto-start listening when agent finishes speaking during brainstorming
  const { speak, stop: stopSpeaking, isSpeaking } = useTextToSpeech({
    onEnd: () => {
      if (isBrainstormingRef.current) {
        // Small delay to avoid mic picking up tail-end of TTS audio
        setTimeout(() => {
          if (isBrainstormingRef.current) {
            startRecordingRef.current?.();
          }
        }, 800);
      }
    }
  });
  const lastSpokenMessageIndexRef = useRef<number>(-1);
  const startRecordingRef = useRef<(() => void) | null>(null);
  const isUploading = isFileUploadUploading || isBrainDumpUploading || isFinalizingBrainstorm;

  const [input, setInput] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);

  // Persona context for suggestion chips
  const { persona } = usePersona();

  // Workflow NL discovery state
  const [workflowMatches, setWorkflowMatches] = useState<WorkflowMatch[]>([]);
  const [showTemplateGallery, setShowTemplateGallery] = useState(false);
  const workflowDismissTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Agent mode state
  const [agentMode, setAgentMode] = useState<AgentMode>('auto');
  const [isAgentModeOpen, setIsAgentModeOpen] = useState(false);
  const agentModeRef = useRef<HTMLDivElement>(null);

  // History dropdown state
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const historyRef = useRef<HTMLDivElement>(null);

  // More options dropdown state
  const [isMoreOptionsOpen, setIsMoreOptionsOpen] = useState(false);
  const moreOptionsRef = useRef<HTMLDivElement>(null);

  // Mobile full-screen detection
  const [isMobileChat, setIsMobileChat] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 768px)');
    const update = () => setIsMobileChat(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  // Agent mode options
  const agentModeOptions: { value: AgentMode; label: string; icon: React.ReactElement<{ size?: number | string; className?: string }>; description: string }[] = [
    { value: 'auto', label: 'Auto', icon: <Zap size={10} />, description: 'Agent works independently until done' },
    { value: 'collab', label: 'Collab', icon: <Users size={10} />, description: 'Agent asks for approval & insights' },
    { value: 'ask', label: 'Ask', icon: <HelpCircle size={10} />, description: 'Ask about progress, chats & reports' },
  ];

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (agentModeRef.current && !agentModeRef.current.contains(event.target as Node)) {
        setIsAgentModeOpen(false);
      }
      if (historyRef.current && !historyRef.current.contains(event.target as Node)) {
        setIsHistoryOpen(false);
      }
      if (moreOptionsRef.current && !moreOptionsRef.current.contains(event.target as Node)) {
        setIsMoreOptionsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Send initial prompt when opened from onboarding / command center handoff.
  useEffect(() => {
    initialPromptSentRef.current = false;
  }, [initialPrompt, initialSessionId, visibleSessionId]);

  useEffect(() => {
    const hasOnlyWelcomeMessage =
      messages.length === 1 && messages[0]?.id === 'welcome-message';
    if (initialPrompt && !initialPromptSentRef.current && !isLoadingHistory && (messages.length === 0 || hasOnlyWelcomeMessage)) {
      initialPromptSentRef.current = true;
      sendMessage(initialPrompt, agentMode);
      onInitialPromptSent?.();
    }
  }, [initialPrompt, isLoadingHistory, messages, sendMessage, agentMode, onInitialPromptSent]);

  // Speech recognition hook
  const {
    isRecording,
    isTranscribing: isSpeechTranscribing,
    toggleRecording,
    startRecording,
    transcript: speechTranscript,
    transcriptVersion: speechTranscriptVersion,
    interimTranscript,
    error: speechError,
    isSupported: isSpeechSupported
  } = useSpeechRecognition();

  // Keep startRecording ref in sync for TTS callback
  useEffect(() => { startRecordingRef.current = startRecording; }, [startRecording]);

  // Append a finished backend transcript once per completed recording.
  useEffect(() => {
    if (!speechTranscript.trim()) return;
    if (speechTranscriptVersion <= handledTranscriptVersionRef.current) return;

    handledTranscriptVersionRef.current = speechTranscriptVersion;
    if (isBrainstorming) {
      sendMessage(speechTranscript, 'collab');
    } else {
      setInput(prev => prev ? `${prev} ${speechTranscript}` : speechTranscript);
    }
  }, [speechTranscript, speechTranscriptVersion, isBrainstorming, sendMessage]);

  // NEW: Get user info for presence
  const supabase = useMemo(() => createClient(), []);
  const [currentUserId, setCurrentUserId] = useState<string>('');
  const sessionIdRef = useRef<string>(initialSessionId || getSessionId() || '');

  useEffect(() => {
    supabase.auth.getUser().then(({ data }: any) => {
      if (data.user) setCurrentUserId(data.user.id);
    });
  }, [supabase]);

  useEffect(() => {
    // Keep ref in sync
    const id = getSessionId();
    if (id) sessionIdRef.current = id;
  }, [getSessionId, messages]);

  const clearPersistedBrainstormSession = useCallback(() => {
    if (typeof window === 'undefined') return;
    window.sessionStorage.removeItem(BRAINSTORM_SESSION_STORAGE_KEY);
  }, []);


  const handleViewInWorkspace = useCallback((widget: WidgetDefinition) => {
    if (currentUserId) {
      dispatchFocusWidget(widget, currentUserId);
    } else {
      console.warn('No user ID available to view widget in workspace');
    }
  }, [currentUserId]);

  // TTS Effect: Speak agent responses when brainstorming (fallback when voice session is NOT connected)
  useEffect(() => {
    // Skip TTS when Gemini Live voice session handles audio directly
    if (voiceSession.isConnected) return;

    if (!isBrainstorming) {
      stopSpeaking();
      return;
    }

    // Only speak when streaming is finished to ensure full sentence
    if (!isStreaming && messages.length > 0) {
      const lastIndex = messages.length - 1;
      const lastMsg = messages[lastIndex];

      if (lastMsg.role === 'agent' && lastMsg.text && lastIndex > lastSpokenMessageIndexRef.current) {
        speak(lastMsg.text);
        lastSpokenMessageIndexRef.current = lastIndex;
      }
    }
  }, [isBrainstorming, isStreaming, messages, speak, stopSpeaking, voiceSession.isConnected]);

  const buildVoiceTranscriptText = useCallback(() => {
    const turns = voiceSession.transcriptTurns ?? [];
    if (turns.length > 0) {
      return turns
        .map((t) => `${t.speaker.toUpperCase()}: ${t.text}`)
        .join('\n\n');
    }

    if (voiceSession.userTranscript || voiceSession.agentTranscript) {
      const userParts = voiceSession.userTranscript ? `USER: ${voiceSession.userTranscript}` : '';
      const agentParts = voiceSession.agentTranscript ? `AGENT: ${voiceSession.agentTranscript}` : '';
      return [userParts, agentParts].filter(Boolean).join('\n\n');
    }

    return messages
      .slice(-20)
      .filter((m) => typeof m.text === 'string' && m.text.trim().length > 0)
      .map((m) => `${m.role.toUpperCase()}: ${m.text}`)
      .join('\n\n');
  }, [messages, voiceSession.agentTranscript, voiceSession.transcriptTurns, voiceSession.userTranscript]);

  useEffect(() => {
    if (restoreAttemptedRef.current || typeof window === 'undefined') return;
    restoreAttemptedRef.current = true;

    const raw = window.sessionStorage.getItem(BRAINSTORM_SESSION_STORAGE_KEY);
    if (!raw) return;

    let saved: PersistedBrainstormSession | null = null;
    try {
      saved = JSON.parse(raw) as PersistedBrainstormSession;
    } catch {
      clearPersistedBrainstormSession();
      return;
    }

    if (
      !saved?.sessionId
      || !Array.isArray(saved.transcriptTurns)
      || typeof saved.updatedAt !== 'number'
      || (Date.now() - saved.updatedAt) > BRAINSTORM_SESSION_MAX_AGE_MS
    ) {
      clearPersistedBrainstormSession();
      return;
    }

    brainstormStartModeRef.current = saved.startMode === 'fresh' ? 'fresh' : 'resume';
    sessionIdRef.current = saved.sessionId;
    setFinalizeResult(null);
    setIsBrainstorming(true);
    lastSpokenMessageIndexRef.current = messages.length - 1;

    const requestId = ++brainstormConnectRequestRef.current;

    void voiceSession.connect(saved.sessionId, {
      startMode: 'resume',
      initialTurns: saved.transcriptTurns,
      resumeTranscript: saved.transcript,
    }).catch((error: any) => {
      if (
        brainstormConnectRequestRef.current !== requestId
        || isVoiceConnectionSupersededError(error)
      ) {
        return;
      }
      voiceSession.disconnect();
      setIsBrainstorming(false);
      clearPersistedBrainstormSession();
      addMessage({
        role: 'system',
        text: `We could not restore your live brainstorm session${error?.message ? ` (${error.message})` : ''}. Please start it again.`,
      });
    });
  }, [addMessage, clearPersistedBrainstormSession, messages.length, voiceSession]);

  useEffect(() => {
    if (!isBrainstorming || isFinalizingBrainstorm || finalizeResult || typeof window === 'undefined') {
      return;
    }

    const sessionId = sessionIdRef.current || getSessionId();
    if (!sessionId) return;

    const persistedSession: PersistedBrainstormSession = {
      sessionId,
      startMode: brainstormStartModeRef.current,
      transcript: buildVoiceTranscriptText(),
      transcriptTurns: voiceSession.transcriptTurns ?? [],
      updatedAt: Date.now(),
    };

    window.sessionStorage.setItem(
      BRAINSTORM_SESSION_STORAGE_KEY,
      JSON.stringify(persistedSession),
    );
  }, [
    buildVoiceTranscriptText,
    finalizeResult,
    getSessionId,
    isBrainstorming,
    isFinalizingBrainstorm,
    voiceSession.agentTranscript,
    voiceSession.transcriptTurns,
    voiceSession.userTranscript,
  ]);

  const finalizeBrainstormSession = useCallback(async (payload: {
    sessionId: string;
    transcript: string;
    turns: Array<{ speaker: string; text: string; ts_ms?: number }>;
  }) => {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
    if (!token) throw new Error('Authentication required to finalize brainstorm session');

    const maxRetries = 3;
    let lastError = '';
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const response = await fetch(`${AGENT_BACKEND_URL}/ws/voice/finalize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            session_id: payload.sessionId,
            turns: payload.turns,
            transcript: payload.transcript,
            context: 'Finalize Source: Discuss with Agent',
          }),
        });

        const data = await response.json().catch(() => ({}));
        if (response.ok && data?.success) {
          return data as {
            success: boolean;
            validation_plan?: string;
            transcript_file_path?: string;
            saved_categories?: string[];
            summary?: { title: string; key_themes: string[]; action_item_count: number; executive_summary: string };
            analysis_doc_id?: string;
            analysis_markdown?: string;
          };
        }
        lastError = data?.error || data?.detail || `HTTP ${response.status}`;
      } catch (err: any) {
        lastError = err.message || 'Network error';
      }
      // Exponential back-off: 1s, 2s
      if (attempt < maxRetries - 1) {
        await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
      }
    }
    throw new Error(lastError || 'Failed to finalize brainstorm session after retries');
  }, [supabase]);

  // 15-minute client-side fallback timer (safety net if server timeout doesn't arrive)
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isBrainstorming) {
      timer = setTimeout(() => {
        if (isBrainstormingRef.current && !isFinalizingRef.current) {
          handleConcludeBrainstorming();
        }
      }, 900000);
    }
    return () => { if (timer) clearTimeout(timer); };
  }, [isBrainstorming]);

  const handleStartBrainstorming = useCallback(async (startMode: BrainstormStartMode = 'resume') => {
    const requestId = ++brainstormConnectRequestRef.current;
    setFinalizeResult(null);
    setIsBrainstorming(true);
    lastSpokenMessageIndexRef.current = messages.length - 1; // Don't read past messages

    // Try to connect Gemini Live voice session
    const sessionId = getSessionId() || `brainstorm_${Date.now()}`;
    brainstormStartModeRef.current = startMode;
    sessionIdRef.current = sessionId;
    try {
      await voiceSession.connect(sessionId, { startMode });
      // Voice session handles the conversation directly via Gemini Live
      // No need to send a text message — the agent greets via audio
    } catch (error: any) {
      if (
        brainstormConnectRequestRef.current !== requestId
        || isVoiceConnectionSupersededError(error)
      ) {
        return;
      }
      voiceSession.disconnect();
      setIsBrainstorming(false);
      addMessage({
        role: 'system',
        text: `Live voice brainstorming could not connect${error?.message ? ` (${error.message})` : ''}. Falling back to text brainstorming for this session.`,
      });
      // Fallback to text-based brainstorming if voice fails
      const modeInstruction = startMode === 'fresh'
        ? 'The user explicitly chose to start a fresh brainstorm. Use the onboarding/business context you already know, but do not anchor on the previous brainstorm thread unless the user asks you to.'
        : 'The user wants to continue from their saved onboarding context and latest brainstorm context if available.';
      sendMessage(
        `[System: User has started a dedicated BRAINSTORMING SESSION. ${modeInstruction} Use the remembered onboarding/business context, the user's saved agent identity, and any relevant Knowledge Vault context before asking questions. Do not ask a blank-slate opener like "What do you have in mind?" Instead, acknowledge what you already know and ask one focused follow-up question. Do not create an initiative yet.]`,
        'collab',
      );
    }
  }, [addMessage, sendMessage, messages.length, getSessionId, voiceSession]);

  const handleConcludeBrainstorming = useCallback(async () => {
    // Dedup guard — prevents double-finalize from client timer + server timeout race
    if (isFinalizingRef.current) return;
    isFinalizingRef.current = true;

    clearPersistedBrainstormSession();
    setIsBrainstorming(false);
    stopSpeaking();
    brainstormConnectRequestRef.current += 1;

    const transcript = buildVoiceTranscriptText();
    const transcriptTurns = (voiceSession.transcriptTurns ?? []).map((t) => ({
      speaker: t.speaker,
      text: t.text,
      ts_ms: t.tsMs,
    }));
    const sessionId = getSessionId() || sessionIdRef.current || `brainstorm_${Date.now()}`;

    voiceSession.disconnect();

    if (!transcript.trim()) {
      isFinalizingRef.current = false;
      setFinalizeResult({
        success: false,
        transcript_markdown: null,
        transcript_file_path: null,
        saved_categories: [],
        error: 'No conversation was captured. Try speaking after the agent greets you.',
        summary: null,
        analysis_doc_id: null,
        analysis_markdown: null,
      });
      return;
    }

    addMessage({
      role: 'system',
      text: 'Brainstorm session finalized. Saving transcript and generating your comprehensive analysis...',
    });

    setIsFinalizingBrainstorm(true);
    try {
      const result = await finalizeBrainstormSession({
        sessionId,
        transcript,
        turns: transcriptTurns,
      });

      // Set finalizeResult for the overlay summary card
      setFinalizeResult(result as BrainstormFinalizeResult);

      addMessage({
        role: 'system',
        text: `Saved to Brain Dumps (${(result.saved_categories || []).join(', ') || 'Brain Dump Analysis'}). You can review them in the workspace.`,
      });

      // Push analysis widget to workspace if we have markdown content
      if (result.analysis_markdown && result.analysis_doc_id && currentUserId) {
        const analysisWidget: WidgetDefinition = {
          type: 'braindump_analysis',
          title: result.summary?.title || 'Brain Dump Analysis',
          data: {
            markdown: result.analysis_markdown,
            documentId: result.analysis_doc_id,
            sessionId,
            title: result.summary?.title || 'Brain Dump Analysis',
            keyThemes: result.summary?.key_themes || [],
            actionItemCount: result.summary?.action_item_count || 0,
          },
          workspace: {
            mode: 'focus',
            sessionId,
          },
        };
        const saved = widgetService.current.saveWidget(currentUserId, sessionId, analysisWidget, false);
        if (saved) {
          (analysisWidget as WidgetDefinition & { id?: string }).id = saved.id;
        }
        dispatchWorkspaceWidget(analysisWidget, currentUserId, {
          sessionId,
          setActive: true,
          mode: 'focus',
          persistent: false,
        });
      }

      // Show summary card in chat
      if (result.summary) {
        const themes = (result.summary.key_themes || []).join(' · ');
        const summaryText = [
          `**🧠 Brain Dump Analysis: ${result.summary.title}**`,
          '',
          result.summary.executive_summary || '',
          '',
          themes ? `**Key themes:** ${themes}` : '',
          result.summary.action_item_count > 0 ? `**${result.summary.action_item_count} action items** identified` : '',
        ].filter(Boolean).join('\n');

        addMessage({
          role: 'agent',
          text: summaryText,
          agentName: agentName || 'Pikar AI',
        });
      } else {
        addMessage({
          role: 'agent',
          text: 'Your brainstorming session was finalized and saved. Ask me to continue with validation or research when you are ready.',
          agentName: agentName || 'Pikar AI',
        });
      }
    } catch (error) {
      console.error('Failed to finalize brainstorming session:', error);
      setFinalizeResult({
        success: false,
        transcript_markdown: transcript || null,
        transcript_file_path: null,
        saved_categories: [],
        error: 'Analysis generation failed. Your transcript was saved.',
        summary: null,
        analysis_doc_id: null,
        analysis_markdown: null,
      });
      addMessage({
        role: 'system',
        text: 'Automatic finalize processing failed. Falling back to agent-driven analysis...',
      });
      if (transcript) {
        sendMessage(`[System: User has CONCLUDED the brainstorming session.\n\nHere is the transcript of the session:\n\n${transcript}\n\nContext: User ID: ${currentUserId}\n\nPlease analyze this using 'process_brainstorm_conversation' and generate a Validation Plan.]`, 'auto');
      }
    } finally {
      setIsFinalizingBrainstorm(false);
      isFinalizingRef.current = false;
    }
  }, [addMessage, agentName, buildVoiceTranscriptText, clearPersistedBrainstormSession, currentUserId, finalizeBrainstormSession, getSessionId, sendMessage, stopSpeaking, voiceSession]);

  // Keep concludeRef in sync so the onSessionTimeout callback can call latest version
  useEffect(() => { concludeRef.current = handleConcludeBrainstorming; }, [handleConcludeBrainstorming]);

  const handleCancelBrainstorming = useCallback(() => {
    clearPersistedBrainstormSession();
    setIsBrainstorming(false);
    stopSpeaking();
    brainstormConnectRequestRef.current += 1;

    const transcript = buildVoiceTranscriptText();
    if (transcript) {
      addMessage({
        role: 'system',
        text: `[Voice Session Transcript (Canceled)]\n${transcript}`,
      });
    }
    voiceSession.disconnect();
  }, [addMessage, buildVoiceTranscriptText, clearPersistedBrainstormSession, stopSpeaking, voiceSession]);

  // Persist session id to context when chat mounts without one (so navigation doesn't lose the chat)
  useEffect(() => {
    if (initialSessionId != null && initialSessionId !== '') return;
    if (sessionIdNotifiedRef.current) return;
    const id = getSessionId();
    if (id) {
      sessionIdNotifiedRef.current = true;
      onSessionIdReady?.(id);
    }
  }, [initialSessionId, getSessionId, onSessionIdReady]);

  // Derive the effective session ID for subscriptions — prefer visibleSessionId
  // (which changes on session switch without remount) over the static initialSessionId.
  const effectiveRealtimeSessionId = visibleSessionId || initialSessionId || getSessionId() || '';

  // NEW: Realtime session updates
  useRealtimeSession({
    sessionId: effectiveRealtimeSessionId,
    userId: currentUserId,
    onNewEvent: (event) => {
      // Skip if we're actively streaming - SSE already handles current session updates
      // This prevents duplicate messages from both SSE and Realtime adding the same content
      if (isStreaming) {
        console.log('Skipping realtime event during SSE streaming to prevent duplicates');
        return;
      }

      console.log('New session event received:', event);

      // Parse event content similar to useAgentChat logic
      let text = '';
      const eventData = event.event_data || event; // Handle flattened or nested structure

      if (eventData.content?.parts) {
        text = eventData.content.parts.map((p: any) => p.text || '').join('');
      } else if (typeof eventData.content === 'string') {
        text = eventData.content;
      }
      const metadata = extractMessageMetadataFromEvent(eventData);
      const isUserMessage = eventData.source === 'user' || eventData.author === 'user' || eventData.role === 'user';

      if (isUserMessage) {
        return;
      }

      // Only add messages from OTHER sessions or async agent updates not caught by SSE
      if (text || eventData.widget || metadata) {
        addMessage({
          role: 'agent',
          text: text,
          // Use custom agent name from props/context for agent messages, not the internal ADK agent name
          agentName: agentName || eventData.source,
          metadata,
          widget: eventData.widget
        });
      }
    },
  });

  // NEW: Presence tracking — uses dynamic session ID for channel switching
  const { onlineUsers } = usePresence(
    effectiveRealtimeSessionId ? `chat:${effectiveRealtimeSessionId}` : null,
    currentUserId,
    'User' // Could fetch from user profile
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ---------------------------------------------------------------------------
  // Multi-session: scroll position save/restore when visibleSessionId changes
  // ---------------------------------------------------------------------------
  const prevVisibleSessionRef = useRef<string | null>(null);

  useEffect(() => {
    const container = scrollContainerRef.current;
    const prevId = prevVisibleSessionRef.current;

    // Save scroll position for the session we're leaving
    if (prevId && prevId !== visibleSessionId && container) {
      updateSessionState(prevId, { scrollTop: container.scrollTop });
    }

    // Restore scroll position for the session we're switching to
    if (visibleSessionId) {
      const session = activeSessions.get(visibleSessionId);
      if (session && session.scrollTop >= 0 && container) {
        requestAnimationFrame(() => {
          if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = session.scrollTop;
          }
        });
      }
    }

    prevVisibleSessionRef.current = visibleSessionId;
  }, [visibleSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Multi-session: clear hasUnread when session becomes visible
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (visibleSessionId) {
      const session = activeSessions.get(visibleSessionId);
      if (session?.hasUnread) {
        updateSessionState(visibleSessionId, { hasUnread: false, lastUpdatedAt: Date.now() });
      }
    }
  }, [visibleSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Multi-session: process pending actions and deferred widgets on switch
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!visibleSessionId) return;
    const session = activeSessions.get(visibleSessionId);
    if (!session) return;

    // Process deferred widgets that arrived while the session was in the background
    if (session.rawWidgets.length > 0) {
      const widgets = [...session.rawWidgets];
      // Clear first to prevent re-processing on re-renders
      updateSessionState(visibleSessionId, { rawWidgets: [] });
      for (const raw of widgets) {
        const def = raw.widget as import('@/types/widgets').WidgetDefinition;
        if (validateWidgetDefinition(def) && currentUserId && isWorkspaceCanvasWidget(def)) {
          widgetService.current.saveWidget(
            currentUserId,
            visibleSessionId,
            def,
            false, // not pinned
          );
        }
      }
    }

    // Flush pending actions (e.g. focus last widget)
    if (session.pendingActions.length > 0) {
      const actions = [...session.pendingActions];
      updateSessionState(visibleSessionId, { pendingActions: [] });
      const lastFocus = actions.reverse().find(a => a.type === 'focus_widget');
      if (lastFocus && currentUserId) {
        const widget = lastFocus.payload as import('@/types/widgets').WidgetDefinition;
        if (isWorkspaceCanvasWidget(widget)) {
          dispatchFocusWidget(widget, currentUserId);
        }
      }
      const lastWorkspaceActivity = actions.find(a => a.type === 'workspace_activity');
      if (lastWorkspaceActivity && currentUserId) {
        const payload = lastWorkspaceActivity.payload as {
          agentName?: string;
          text?: string;
          traces?: Array<{ type: 'thinking' | 'tool_use' | 'tool_output'; content: string; toolName?: string }>;
        };
        dispatchWorkspaceActivity({
          userId: currentUserId,
          sessionId: visibleSessionId,
          phase: 'running',
          agentName: payload.agentName,
          text: payload.text,
          traces: payload.traces,
        });
      }
    }
  }, [visibleSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = async () => {
    // Allow sending if there's text OR attached files
    // Block sending during history load to prevent messages going to wrong session
    if ((!input.trim() && attachedFiles.length === 0) || isUploading || isLoadingHistory) return;

    let messageToSend = input.trim();
    const fileContents: string[] = [];
    const failedFiles: string[] = [];

    // If there are attached files, upload them all and collect their content.
    // Previously, a single failed upload would silently `return` and the send
    // button appeared dead. Now we surface every failure as a visible system
    // message and still send the user's typed text + any successfully extracted
    // attachments, so the user always gets feedback.
    if (attachedFiles.length > 0) {
      for (const file of attachedFiles) {
        const result = await uploadFile(file);
        if (result) {
          fileContents.push(`**Attached File: ${result.filename}**\n${result.content}`);
        } else {
          failedFiles.push(file.name);
        }
      }

      if (failedFiles.length > 0) {
        const detail = uploadError
          ? ` Reason: ${uploadError}`
          : ' The backend rejected the file (it may be unsupported, too large, or temporarily unavailable).';
        addMessage({
          role: 'system',
          text:
            failedFiles.length === 1
              ? `Could not process attachment "${failedFiles[0]}".${detail} Try a different file or remove the attachment and send the message again.`
              : `Could not process ${failedFiles.length} attachments: ${failedFiles
                  .map((n) => `"${n}"`)
                  .join(', ')}.${detail}`,
        });
      }

      // Always clear attachments after a send attempt — failed files will not
      // succeed on a retry without user action, and stale chips would confuse
      // the next send.
      setAttachedFiles([]);

      // If every attachment failed AND there is no typed message, abort the
      // send (we already showed the failure message above).
      if (fileContents.length === 0 && !messageToSend) {
        return;
      }

      // Combine user's message with whatever attachments DID extract.
      if (fileContents.length > 0) {
        if (messageToSend) {
          messageToSend = `${messageToSend}\n\n---\n${fileContents.join('\n\n---\n')}`;
        } else if (fileContents.length === 1) {
          messageToSend = `Please analyze and summarize the following document:\n\n---\n${fileContents[0]}`;
        } else {
          messageToSend = `Please analyze and summarize the following ${fileContents.length} documents:\n\n---\n${fileContents.join('\n\n---\n')}`;
        }
      }
    }

    if (messageToSend) {
      sendMessage(messageToSend, agentMode);

      // Workflow NL discovery: detect intent-like phrases and search in parallel
      const lower = messageToSend.toLowerCase();
      const isWorkflowIntent =
        lower.startsWith('i want to') ||
        lower.startsWith('i need to') ||
        lower.startsWith('help me') ||
        lower.startsWith('how do i') ||
        lower.startsWith('can you');

      if (isWorkflowIntent) {
        // Clear any previous auto-dismiss timer
        if (workflowDismissTimerRef.current) {
          clearTimeout(workflowDismissTimerRef.current);
        }
        searchWorkflows(messageToSend)
          .then((matches) => {
            const good = matches.filter((m) => m.match_score >= 0.4);
            if (good.length > 0) {
              setWorkflowMatches(good);
              // Auto-dismiss after 15 seconds
              workflowDismissTimerRef.current = setTimeout(() => {
                setWorkflowMatches([]);
              }, 15_000);
            }
          })
          .catch(() => {
            // Silently ignore — workflow search is supplementary
          });
      } else {
        // Any non-intent message dismisses the launcher
        setWorkflowMatches([]);
      }
    }

    setInput('');
    // Reset textarea height after sending
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  // Auto-resize textarea as user types - expands up to max height, then scrolls
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';
      // Set to scrollHeight, but cap at max height (300px ~12 lines)
      const maxHeight = 300;
      const newHeight = Math.min(textarea.scrollHeight, maxHeight);
      textarea.style.height = `${newHeight}px`;
    }
  }, []);

  // Compute the displayed text value
  const displayedText = input;

  // Adjust height when displayed text changes
  useLayoutEffect(() => {
    adjustTextareaHeight();
  }, [displayedText, adjustTextareaHeight]);

  // Handle keyboard shortcuts: Enter to send, Shift+Enter for new line
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isUploading && !isSpeechTranscribing && !isRecording) {
      e.preventDefault();
      handleSend();
    }
  };

  const messagesRef = useRef(messages);
  const toggleWidgetMinimizedRef = useRef(toggleWidgetMinimized);

  useEffect(() => {
    messagesRef.current = messages;
    toggleWidgetMinimizedRef.current = toggleWidgetMinimized;
  }, [messages, toggleWidgetMinimized]);

  // Stable handler for widget actions
  const handleWidgetAction = useCallback(async (messageIndex: number, action: string, payload?: unknown) => {
    const msg = messagesRef.current[messageIndex];
    if (action === 'pin' && msg.widget) {
      // Do not pin image/video to command center — they stay in chat and Knowledge Vault only
      if (msg.widget.type === 'image' || msg.widget.type === 'video' || msg.widget.type === 'video_spec') return;
      const { data } = await supabase.auth.getUser();
      if (data.user) {
        const wAny = msg.widget as any;
        if (wAny.id) {
          widgetService.current.pinWidget(wAny.id, data.user.id);
        } else {
          const saved = widgetService.current.saveWidget(data.user.id, initialSessionId || 'default', msg.widget, true);
          if (saved) {
            (msg.widget as any).id = saved.id;
          }
        }
      }
    }
    if (action === 'open_app_builder') {
      const p = (payload || {}) as { targetPath?: string };
      window.location.href =
        typeof p.targetPath === 'string' && p.targetPath ? p.targetPath : '/app-builder';
      return;
    }
    if (action === 'open_app_builder_project') {
      const p = (payload || {}) as { projectId?: string; targetPath?: string };
      const targetPath =
        typeof p.targetPath === 'string' && p.targetPath
          ? p.targetPath
          : (p.projectId ? `/app-builder/${p.projectId}` : '/app-builder');
      window.location.href = targetPath;
      return;
    }
    if (action === 'save_workflow') {
      try {
        const p = (payload || {}) as { nodes?: Array<{ data?: { label?: string } }>; edges?: unknown[] };
        const nodes = p.nodes || [];
        const steps = nodes.map((node, idx) => ({
          name: node?.data?.label || `Step ${idx + 1}`,
          tool: 'create_task',
          description: `Generated from workflow builder node ${idx + 1}`,
          required_approval: false,
        }));
        const body = {
          name: msg?.widget?.title ? `${msg.widget.title} Draft` : 'Workflow Builder Draft',
          description: 'Generated from workflow builder widget',
          category: 'custom',
          phases: [{ name: 'Builder Flow', steps }],
          is_generated: true,
        };
        const created = await createWorkflowTemplate(body);
        window.location.href = `/dashboard/workflows/editor/${created.id}`;
        return;
      } catch (error) {
        console.error('Failed to save workflow from widget action', error);
      }
    }
    if (action === 'expand_workflow') {
      try {
        localStorage.setItem('workflow_builder_draft', JSON.stringify(payload || {}));
      } catch {
        // Ignore localStorage failures and continue navigation.
      }
      window.location.href = '/dashboard/workflows/editor/new?source=widget';
      return;
    }
    console.log('Widget action:', { messageIndex, action, payload });
  }, [initialSessionId, supabase]); // Only depends on initialSessionId and stable Supabase client

  // Stable wrapper for toggle
  const handleToggleWidget = useCallback((index: number) => {
    toggleWidgetMinimizedRef.current(index);
  }, []);

  const handleWidgetDismiss = useCallback((index: number) => {
    console.log('Widget dismissed at index:', index);
  }, []);

  // Smart upload: call /upload/smart to detect content type and get a summary
  const handleSmartUpload = useCallback(async (file: File) => {
    if (isStreaming || isUploading) return;

    setIsSmartUploading(true);
    setSmartUploadFile(file);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const { data: { session: authSession } } = await supabase.auth.getSession();
      const token = authSession?.access_token;

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const headers: HeadersInit = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/upload/smart`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const detail = await response.text().catch(() => '');
        throw new Error(detail || `Smart upload failed: ${response.statusText}`);
      }

      const data: SmartUploadResult = await response.json();
      setSmartUploadResult(data);
    } catch (err) {
      console.error('Smart upload failed, falling back to attach:', err);
      // Fallback: just attach the file normally so the user can still
      // send it via the regular handleSend path. Add a system message so
      // they know the smart-upload context detection step was skipped (the
      // preview/Add-to-Vault toast won't appear in this case).
      setAttachedFiles(prev => {
        const exists = prev.some(f => f.name === file.name && f.size === file.size);
        if (exists) return prev;
        return [...prev, file];
      });
      addMessage({
        role: 'system',
        text: `"${file.name}" was attached, but smart preview is unavailable right now. ${
          err instanceof Error ? err.message : 'Send the message and the agent will read the file directly.'
        }`,
      });
      setSmartUploadFile(null);
    } finally {
      setIsSmartUploading(false);
    }
  }, [isStreaming, isUploading, supabase, addMessage]);

  // Smart upload action handlers
  const handleSmartUploadAddToVault = useCallback(async () => {
    if (!smartUploadResult || !smartUploadFile) return;

    const result = await uploadFileToVault(smartUploadFile);
    const filename = smartUploadResult.filename;
    if (result) {
      addMessage({
        role: 'system',
        text: `${filename} was saved to your Knowledge Vault.${result.processed ? ` It is now searchable with ${result.embedding_count} chunk${result.embedding_count === 1 ? '' : 's'}.` : ' It was stored, but this format could not be made searchable yet.'}`,
      });
    } else {
      // Vault upload failed — previously this branch was silent, so the
      // toast simply disappeared and the user assumed nothing happened.
      addMessage({
        role: 'system',
        text: `Could not save "${filename}" to the Knowledge Vault.${
          uploadError ? ` Reason: ${uploadError}` : ' The backend rejected the upload.'
        } Try again, or attach the file directly to your message.`,
      });
    }
    setSmartUploadResult(null);
    setSmartUploadFile(null);
  }, [smartUploadResult, smartUploadFile, uploadFileToVault, uploadError, addMessage]);

  const handleSmartUploadAnalyzeNow = useCallback(async () => {
    if (!smartUploadResult || !smartUploadFile) return;

    // Upload the file to get full content
    const result = await uploadFile(smartUploadFile);
    const filename = smartUploadResult.filename;
    const detectedType = smartUploadResult.detected_type;
    const summary = smartUploadResult.summary;

    if (!result) {
      // Full content upload failed — surface it explicitly instead of
      // silently sending only the smart-upload preview, which would make
      // the agent answer based on a tiny snippet without telling the user.
      addMessage({
        role: 'system',
        text: `Could not extract the full content of "${filename}".${
          uploadError ? ` Reason: ${uploadError}` : ''
        } Sending the smart-upload preview only.`,
      });
    }

    const message = result
      ? `I've uploaded ${filename} (${detectedType}). Please analyze this file:\n\n---\n**File: ${result.filename}**\n${result.content}\n\n---\nPreview: ${summary}`
      : `I've uploaded ${filename} (${detectedType}). Please analyze this file.\n\nPreview: ${summary}`;

    sendMessage(message, agentMode);
    setSmartUploadResult(null);
    setSmartUploadFile(null);
  }, [smartUploadResult, smartUploadFile, uploadFile, uploadError, addMessage, sendMessage, agentMode]);

  const handleSmartUploadDismiss = useCallback(() => {
    // On dismiss, just attach the file normally so it's not lost
    if (smartUploadFile) {
      setAttachedFiles(prev => {
        const exists = prev.some(f => f.name === smartUploadFile.name && f.size === smartUploadFile.size);
        if (exists) return prev;
        return [...prev, smartUploadFile];
      });
    }
    setSmartUploadResult(null);
    setSmartUploadFile(null);
  }, [smartUploadFile]);

  // Handle file selection - try smart upload first, fall back to basic attach
  const handleFileAttach = (file: File) => {
    if (isStreaming || isUploading) return;

    // If a smart upload toast is already showing, dismiss it first
    if (smartUploadResult) {
      handleSmartUploadDismiss();
    }

    // Try the smart upload endpoint to detect content type
    handleSmartUpload(file);
  };

  // Handle multiple files at once (for file input with multiple)
  const handleFilesAttach = (files: FileList) => {
    if (isStreaming || isUploading) return;
    const newFiles = Array.from(files);

    // Single file: route through smart upload for Context Sniffer UX
    if (newFiles.length === 1) {
      handleFileAttach(newFiles[0]);
      return;
    }

    // Multiple files: attach directly (smart toast for each would be confusing)
    setAttachedFiles(prev => {
      const combined = [...prev];
      for (const file of newFiles) {
        const exists = combined.some(f => f.name === file.name && f.size === file.size);
        if (!exists) {
          combined.push(file);
        }
      }
      return combined;
    });
  };

  // Remove a specific attached file by index
  const handleRemoveAttachment = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Clear all attachments
  const handleClearAllAttachments = () => {
    setAttachedFiles([]);
  };

  // Get appropriate icon for file type
  const getFileIcon = (file: File) => {
    const type = file.type;
    if (type.startsWith('image/')) return <Image size={16} className="text-blue-500" />;
    if (type.includes('spreadsheet') || type.includes('excel') || file.name.endsWith('.csv')) {
      return <FileSpreadsheet size={16} className="text-green-500" />;
    }
    if (type.includes('pdf') || type.includes('document') || type.includes('text')) {
      return <FileText size={16} className="text-red-500" />;
    }
    return <FileIcon size={16} className="text-slate-500" />;
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <>
    <div className={className || `${isMobileChat ? 'fixed inset-0 z-50 h-[100dvh]' : 'relative h-[600px] rounded-2xl shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] border border-slate-100/80'} bg-white overflow-hidden w-full max-w-full`}>
      <FileDropZone onFileDrop={handleFileAttach} onFilesDrop={(files) => { if (files.length === 1) { handleFileAttach(files[0]); } else { files.forEach(f => { setAttachedFiles(prev => { const exists = prev.some(pf => pf.name === f.name && pf.size === f.size); return exists ? prev : [...prev, f]; }); }); } }} disabled={isStreaming || isUploading}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="bg-slate-50/60 p-2 border-b border-slate-100/80 flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-teal-500 to-cyan-500 flex items-center justify-center text-white font-bold text-xs shadow-lg shadow-teal-500/20">
              {agentName ? agentName.charAt(0).toUpperCase() : <Bot size={14} />}
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-sm text-slate-800 font-outfit leading-tight">
                {agentName || 'Pikar AI'}
              </h3>
              <p className="text-[10px] text-slate-500 leading-tight block mt-0.5">
                {agentName ? 'Personal Agent' : 'Executive Assistant & Orchestrator'}
              </p>
            </div>
            {/* Online users indicator */}
            {onlineUsers.length > 1 && (
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span>{onlineUsers.length} online</span>
              </div>
            )}

            {/* Header Action Icons */}
            <div className="flex items-center gap-1">
              {/* New Chat Button */}
              <button
                onClick={onNewChat}
                className="p-1 rounded-md text-slate-500 hover:text-teal-600 hover:bg-slate-100 transition-colors"
                title="New Chat"
              >
                <Plus size={14} />
              </button>

              {/* Chat History Dropdown */}
              <div ref={historyRef} className="relative">
                <button
                  onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                  className={`p-1 rounded-md transition-colors ${isHistoryOpen
                    ? 'text-teal-600 bg-teal-50'
                    : 'text-slate-500 hover:text-teal-600 hover:bg-slate-100'
                    }`}
                  title="Chat History"
                >
                  <Clock size={14} />
                </button>

                {/* History Dropdown Menu */}
                {isHistoryOpen && (
                  <div className="absolute right-0 top-full mt-2 w-72 max-w-[calc(100vw-2rem)] bg-white border border-slate-100/80 rounded-2xl shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden z-50">
                    <div className="p-3 border-b border-slate-100/80">
                      <h4 className="text-sm font-semibold text-slate-700">Chat History</h4>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      {chatHistory.length > 0 ? (
                        chatHistory.map((chat) => {
                          const isPlaceholderTitle = !chat.title || chat.title.startsWith('Chat from') || chat.title === 'Untitled Chat';
                          const headline = !isPlaceholderTitle ? chat.title : (chat.preview ? chat.preview.replace(/\n/g, ' ').slice(0, 60) + (chat.preview.length > 60 ? '…' : '') : 'New conversation');
                          return (
                            <button
                              key={chat.id}
                              onClick={() => {
                                onSelectChat?.(chat.id);
                                setIsHistoryOpen(false);
                              }}
                              className="w-full p-3 text-left hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-b-0"
                            >
                              <p className="text-sm font-bold text-slate-900 line-clamp-2 leading-snug">
                                {headline}
                              </p>
                              {chat.preview && !isPlaceholderTitle && (
                                <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">
                                  {chat.preview}
                                </p>
                              )}
                              <p className="text-[10px] text-slate-400 mt-1">
                                {chat.timestamp.toLocaleDateString()} {chat.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </p>
                            </button>
                          );
                        })
                      ) : (
                        <div className="p-4 text-center text-sm text-slate-500">
                          No chat history yet
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* More Options Dropdown */}
              <div ref={moreOptionsRef} className="relative">
                <button
                  onClick={() => setIsMoreOptionsOpen(!isMoreOptionsOpen)}
                  className={`p-1 rounded-md transition-colors ${isMoreOptionsOpen
                    ? 'text-teal-600 bg-teal-50'
                    : 'text-slate-500 hover:text-teal-600 hover:bg-slate-100'
                    }`}
                  title="More Options"
                >
                  <MoreVertical size={14} />
                </button>

                {/* More Options Dropdown Menu */}
                {isMoreOptionsOpen && (
                  <div className="absolute right-0 top-full mt-2 w-48 bg-white border border-slate-100/80 rounded-2xl shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden z-50">
                    <button
                      onClick={() => {
                        onClearAllChats?.();
                        setIsMoreOptionsOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left text-sm text-slate-700 hover:bg-red-50 hover:text-red-600 transition-colors"
                    >
                      <Trash2 size={16} className="text-slate-500" />
                      Clear All Chats
                    </button>
                    <button
                      onClick={() => {
                        onCloseAllChats?.();
                        setIsMoreOptionsOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 transition-colors border-t border-slate-100"
                    >
                      <XSquare size={16} className="text-slate-500" />
                      Close All Chats
                    </button>
                    <button
                      onClick={() => {
                        onCloseChat?.();
                        setIsMoreOptionsOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 transition-colors border-t border-slate-100"
                    >
                      <X size={16} className="text-slate-500" />
                      Close Chat
                    </button>
                    <button
                      onClick={() => {
                        onShowChatHistory?.();
                        setIsMoreOptionsOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 transition-colors border-t border-slate-100"
                    >
                      <Clock size={16} className="text-slate-500" />
                      Show Chat History
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {isLoadingHistory && (
            <div className="absolute inset-0 z-10 bg-white/50 flex items-center justify-center backdrop-blur-sm">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
                <span className="text-sm font-medium text-slate-600">Loading conversation...</span>
              </div>
            </div>
          )}

          {/* Messages */}
          <div ref={scrollContainerRef} className="flex-1 overflow-y-auto overflow-x-hidden px-3 sm:px-4 py-4 space-y-6 bg-slate-50/50 max-w-full">
            {messages.map((msg, i) => (
              <MessageItem
                key={msg.id || `${msg.role}-${i}-${msg.text?.slice(0, 20) || 'empty'}`}
                msg={msg}
                index={i}
                onToggleWidgetMinimized={handleToggleWidget}
                onWidgetAction={handleWidgetAction}
                onWidgetDismiss={handleWidgetDismiss}
                onViewInWorkspace={handleViewInWorkspace}
                onSendMessage={(text) => sendMessage(text, agentMode)}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="px-3 sm:px-4 py-3 bg-white border-t border-slate-100/80 safe-area-bottom max-w-full overflow-visible">
            {/* Smart Upload Toast — Context Sniffer */}
            {smartUploadResult && (
              <SmartUploadToast
                result={smartUploadResult}
                onAddToVault={handleSmartUploadAddToVault}
                onAnalyzeNow={handleSmartUploadAnalyzeNow}
                onDismiss={handleSmartUploadDismiss}
                isProcessing={isFileUploadUploading}
              />
            )}

            {isUploading && (
              <div className="mb-3 flex items-center gap-2 rounded-2xl border border-teal-100 bg-teal-50 px-3 py-2 text-sm text-teal-800">
                <Loader2 size={16} className="animate-spin text-teal-600" />
                <span>
                  {isFinalizingBrainstorm
                    ? 'Finalizing your brain dump session...'
                    : 'Processing your file while keeping the chat visible...'}
                </span>
              </div>
            )}

            {/* Smart Upload Loading */}
            {isSmartUploading && (
              <div className="mb-2 flex items-center gap-2 p-2 bg-indigo-50 rounded-lg border border-indigo-200">
                <Loader2 size={14} className="animate-spin text-indigo-500" />
                <span className="text-xs font-medium text-indigo-600">Detecting content type...</span>
              </div>
            )}

            {/* Attachments Preview */}
            {attachedFiles.length > 0 && (
              <div className="mb-2 space-y-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-slate-500">
                    {attachedFiles.length} file{attachedFiles.length > 1 ? 's' : ''} attached
                  </span>
                  {attachedFiles.length > 1 && (
                    <button
                      onClick={handleClearAllAttachments}
                      className="text-xs text-slate-400 hover:text-red-500 transition-colors"
                    >
                      Clear all
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {attachedFiles.map((file, index) => (
                    <div
                      key={`${file.name}-${index}`}
                      className="flex items-center gap-2 px-2 py-1.5 bg-slate-100 rounded-lg border border-slate-200 max-w-[200px]"
                    >
                      {getFileIcon(file)}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-slate-700 truncate">
                          {file.name}
                        </p>
                        <p className="text-[10px] text-slate-500">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRemoveAttachment(index)}
                        className="p-0.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors flex-shrink-0"
                        title="Remove attachment"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recording Indicator */}
            {(isRecording || isSpeechTranscribing) && (
              <div className="mb-2 flex items-center gap-2 p-2 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="relative flex h-3 w-3">
                    <span className={`absolute inline-flex h-full w-full rounded-full ${isSpeechTranscribing ? 'bg-teal-400 opacity-60' : 'animate-ping bg-red-400 opacity-75'}`}></span>
                    <span className={`relative inline-flex rounded-full h-3 w-3 ${isSpeechTranscribing ? 'bg-teal-500' : 'bg-red-500'}`}></span>
                  </span>
                  <span className={`text-sm font-medium ${isSpeechTranscribing ? 'text-teal-600' : 'text-red-600'}`}>
                    {isSpeechTranscribing ? 'Transcribing...' : 'Recording...'}
                  </span>
                </div>
                {(speechTranscript || interimTranscript) && !isSpeechTranscribing && (
                  <span className="text-sm text-red-500 italic truncate flex-1">
                    &ldquo;{[speechTranscript, interimTranscript].filter(Boolean).join(' ')}&rdquo;
                  </span>
                )}
                {isSpeechTranscribing ? (
                  <Loader2 className="w-4 h-4 animate-spin text-teal-500 ml-auto" />
                ) : (
                  <button
                    onClick={toggleRecording}
                    className="text-xs text-red-600 hover:text-red-800 font-medium flex-shrink-0 ml-auto"
                  >
                    Stop
                  </button>
                )}
              </div>
            )}

            {/* Speech Error */}
            {speechError && !isRecording && !isSpeechTranscribing && (
              <div className="mb-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
                <p className="text-sm text-amber-600">{speechError}</p>
              </div>
            )}

            {/* Dynamic Suggestions + Browse Templates */}
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <SuggestionChips
                  persona={persona || 'solopreneur'}
                  visible={!isRecording && !isSpeechTranscribing && !isUploading && !isStreaming && input.trim().length === 0 && messages.length === 0}
                  onSelect={(text) => sendMessage(text, agentMode)}
                />
              </div>
              {!isRecording && !isSpeechTranscribing && !isUploading && !isStreaming && messages.length === 0 && (
                <button
                  type="button"
                  onClick={() => setShowTemplateGallery((v) => !v)}
                  className={`flex-shrink-0 mb-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    showTemplateGallery
                      ? 'bg-teal-600 text-white'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 shadow-sm'
                  }`}
                >
                  <LayoutGrid size={12} />
                  <span className="hidden sm:inline">Templates</span>
                </button>
              )}
            </div>

            {/* Template Gallery overlay */}
            {showTemplateGallery && (
              <TemplateGallery
                onSelectTemplate={(t: ContentTemplate) => {
                  sendMessage(t.example_prompt, agentMode);
                  setShowTemplateGallery(false);
                }}
                onClose={() => setShowTemplateGallery(false)}
              />
            )}

            {/* Workflow NL matches */}
            {workflowMatches.length > 0 && (
              <WorkflowLauncher
                matches={workflowMatches}
                onLaunch={(templateName) => {
                  startWorkflow(templateName, '').catch(() => {
                    // Silently ignore errors -- the agent chat will show status
                  });
                  addMessage({
                    role: 'system',
                    text: `Starting workflow: ${templateName}...`,
                  });
                  setWorkflowMatches([]);
                }}
                onDismiss={() => setWorkflowMatches([])}
              />
            )}

            {/* Unified Input Container - icons inside at bottom */}
            <div className={`relative bg-slate-50 border rounded-2xl transition ${isRecording
              ? 'border-red-300 bg-red-50/50'
              : 'border-slate-100/80'
              }`}>
              {/* Textarea */}
              <textarea
                ref={textareaRef}
                id="chat-input-text"
                name="chat-input"
                value={displayedText}
                onChange={(e) => !isRecording && setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isUploading || isSpeechTranscribing}
                readOnly={isRecording || isSpeechTranscribing}
                rows={1}
                className="w-full bg-transparent px-4 pt-3 pb-10 outline-none focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0 disabled:opacity-50 disabled:cursor-not-allowed text-black resize-none overflow-y-auto leading-6"
                placeholder={
                  isRecording
                    ? "Listening... speak now"
                    : isSpeechTranscribing
                      ? "Transcribing voice input..."
                      : attachedFiles.length > 0
                      ? "Add a message or just send the files..."
                      : "Type your message..."
                }
                style={{ minHeight: '60px', maxHeight: '300px' }}
              />

              {/* Bottom toolbar - inside the container */}
              <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-2 py-2">
                {/* Left side: Agent Mode Dropdown */}
                <div ref={agentModeRef} className="relative">
                  <button
                    onClick={() => setIsAgentModeOpen(!isAgentModeOpen)}
                    className="flex items-center gap-1.5 px-2.5 py-2 bg-slate-100 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200 transition-colors"
                    title="Select agent mode"
                  >
                    {agentModeOptions.find(o => o.value === agentMode)?.icon}
                    <span className="hidden sm:inline">{agentModeOptions.find(o => o.value === agentMode)?.label}</span>
                    <ChevronDown size={12} className={`transition-transform ${isAgentModeOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {/* Dropdown Menu */}
                  {isAgentModeOpen && (
                    <div className="absolute bottom-full left-0 mb-2 w-44 max-w-[calc(100vw-2rem)] bg-white border border-slate-100/80 rounded-2xl shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden z-50">
                      {agentModeOptions.map((option) => (
                        <button
                          key={option.value}
                          onClick={() => {
                            setAgentMode(option.value);
                            setIsAgentModeOpen(false);
                          }}
                          className={`w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-slate-50 transition-colors ${agentMode === option.value ? 'bg-teal-50 text-teal-700' : 'text-slate-700'
                            }`}
                        >
                          <span className={agentMode === option.value ? 'text-teal-600' : 'text-slate-500'}>
                            {option.icon}
                          </span>
                          <div>
                            <p className="font-medium text-xs">{option.label}</p>
                            <p className="text-[10px] text-slate-500">{option.description}</p>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Right side: File, Mic, Send buttons */}
                <div className="flex items-center gap-1">
                  {/* Brain Dump Menu (Dropdown) */}
                  <BrainDumpMenu
                    isBrainstorming={isBrainstorming}
                    onStartBrainstorming={handleStartBrainstorming}
                    onConcludeBrainstorming={handleConcludeBrainstorming}
                    onCancelBrainstorming={handleCancelBrainstorming}
                    disabled={isStreaming || isUploading || isRecording || isSpeechTranscribing}
                    voiceConnected={voiceSession.isConnected}
                    voiceAgentSpeaking={voiceSession.isAgentSpeaking}
                    remainingSeconds={voiceSession.remainingSeconds}
                    isWrappingUp={voiceSession.isWrappingUp}
                  />

                  <input
                    id="chat-file-input"
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        handleFilesAttach(e.target.files);
                      }
                      e.target.value = '';
                    }}
                  />

                  <button
                    onClick={() => document.getElementById('chat-file-input')?.click()}
                    className={`p-2 rounded-lg transition-colors flex items-center justify-center ${attachedFiles.length > 0
                      ? 'text-teal-500 bg-teal-50'
                      : 'text-slate-400 hover:text-teal-500 hover:bg-slate-100'
                      }`}
                    title="Attach files"
                    disabled={isRecording}
                  >
                    <Paperclip size={16} />
                  </button>

                  {isSpeechSupported ? (
                    <button
                      onClick={toggleRecording}
                      disabled={isStreaming || isUploading || isSpeechTranscribing || voiceSession.isConnected}
                      className={`p-2 rounded-lg transition-colors flex items-center justify-center ${isRecording
                        ? 'bg-red-500 text-white hover:bg-red-600'
                        : 'text-slate-400 hover:text-teal-500 hover:bg-slate-100'
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                      title={isRecording ? "Stop recording" : voiceSession.isConnected ? "Live brainstorm voice is using the microphone" : "Start voice input"}
                    >
                      {isRecording ? (
                        <MicOff size={16} className="animate-pulse" />
                      ) : (
                        <Mic size={16} />
                      )}
                    </button>
                  ) : (
                    <button
                      disabled
                      className="p-2 rounded-lg text-slate-300 cursor-not-allowed flex items-center justify-center"
                      title="Voice input not supported in this browser"
                    >
                      <Mic size={16} />
                    </button>
                  )}

                  {isStreaming ? (
                    <button
                      onClick={stopGeneration}
                      className="p-2 text-white bg-red-600 rounded-lg shadow hover:bg-red-700 transition flex items-center justify-center min-h-[36px] min-w-[36px] relative group"
                      title="Stop Generation"
                    >
                      <Square size={16} fill="currentColor" />
                      <span className="absolute bottom-full mb-1 left-1/2 transform -translate-x-1/2 scale-0 group-hover:scale-100 transition whitespace-nowrap bg-gray-800 text-white text-xs py-1 px-2 rounded opacity-0 group-hover:opacity-100 pointer-events-none">
                        Stop
                      </span>
                    </button>
                  ) : (
                    <button
                      onClick={handleSend}
                      disabled={(!input.trim() && attachedFiles.length === 0) || isUploading || isRecording || isSpeechTranscribing}
                      className="p-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-sm cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center"
                    >
                      {isUploading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    </button>
                  )}
                </div>
              </div>
            </div>
            <p className="text-center text-xs text-slate-400 mt-2">
              Pikar AI can make mistakes. Consider checking important information. Press Shift+Enter for new line.
            </p>
          </div>
        </div>
      </FileDropZone >

    </div >

      {/* Voice Brainstorm Overlay — portal renders to document.body */}
      {(isBrainstorming || isFinalizingBrainstorm || finalizeResult) && (
        <VoiceBrainstormOverlay
          isConnected={voiceSession.isConnected}
          isAgentSpeaking={voiceSession.isAgentSpeaking}
          transcriptTurns={voiceSession.transcriptTurns}
          remainingSeconds={voiceSession.remainingSeconds}
          isWrappingUp={voiceSession.isWrappingUp}
          isTimedOut={voiceSession.isTimedOut}
          error={voiceSession.error}
          isFinalizingBrainstorm={isFinalizingBrainstorm}
          finalizeResult={finalizeResult}
          onEndSession={handleConcludeBrainstorming}
          onRetry={handleStartBrainstorming}
          onViewAnalysis={() => {
            setFinalizeResult(null);
          }}
          onDismiss={() => {
            setFinalizeResult(null);
            handleCancelBrainstorming();
          }}
        />
      )}
    </>
  )

}

function BrainDumpMenu({
  isBrainstorming,
  onStartBrainstorming,
  onConcludeBrainstorming,
  onCancelBrainstorming,
  disabled,
  voiceConnected = false,
  voiceAgentSpeaking = false,
  remainingSeconds = null,
  isWrappingUp = false,
}: {
  isBrainstorming: boolean;
  onStartBrainstorming: (mode: BrainstormStartMode) => void;
  onConcludeBrainstorming: () => void;
  onCancelBrainstorming: () => void;
  disabled: boolean;
  voiceConnected?: boolean;
  voiceAgentSpeaking?: boolean;
  remainingSeconds?: number | null;
  isWrappingUp?: boolean;
}) {
  const [brainstormDuration, setBrainstormDuration] = useState(0);
  const brainstormTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [isStartMenuOpen, setIsStartMenuOpen] = useState(false);
  const startMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isStartMenuOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (startMenuRef.current && !startMenuRef.current.contains(event.target as Node)) {
        setIsStartMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isStartMenuOpen]);

  // Brainstorm session timer
  useEffect(() => {
    if (isBrainstorming) {
      setBrainstormDuration(0);
      brainstormTimerRef.current = setInterval(() => setBrainstormDuration(p => p + 1), 1000);
    } else {
      if (brainstormTimerRef.current) {
        clearInterval(brainstormTimerRef.current);
        brainstormTimerRef.current = null;
      }
      setBrainstormDuration(0);
    }
    return () => {
      if (brainstormTimerRef.current) {
        clearInterval(brainstormTimerRef.current);
        brainstormTimerRef.current = null;
      }
    };
  }, [isBrainstorming]);

  // Local countdown from server's remainingSeconds (ticks down each second)
  const [localCountdown, setLocalCountdown] = useState<number | null>(null);
  useEffect(() => {
    if (remainingSeconds !== null) setLocalCountdown(remainingSeconds);
  }, [remainingSeconds]);
  useEffect(() => {
    if (localCountdown === null || localCountdown <= 0) return;
    const t = setTimeout(() => setLocalCountdown(prev => prev !== null ? Math.max(0, prev - 1) : null), 1000);
    return () => clearTimeout(t);
  }, [localCountdown]);

  const effectiveRemaining = localCountdown ?? remainingSeconds;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Timer phase: normal (teal) → wrapping up (amber) → final warning (red+pulse)
  const isFinalWarning = effectiveRemaining !== null && effectiveRemaining <= 60;
  const timerPhase = isFinalWarning ? 'final' : isWrappingUp ? 'wrapup' : 'normal';

  const barBg = {
    normal: 'bg-teal-50 border-teal-200',
    wrapup: 'bg-amber-50 border-amber-300',
    final: 'bg-red-50 border-red-300 animate-pulse',
  }[timerPhase];

  const barColor = {
    normal: 'bg-teal-500',
    wrapup: 'bg-amber-500',
    final: 'bg-red-500',
  }[timerPhase];

  const timerTextColor = {
    normal: 'text-teal-600',
    wrapup: 'text-amber-600',
    final: 'text-red-600',
  }[timerPhase];

  // Active voice session — show waveform, timer, Finalize & Stop buttons
  if (isBrainstorming) {
    return (
      <div className={`flex items-center gap-1.5 p-1 px-2 rounded-lg border ${barBg}`}>
        {/* Audio waveform pulse indicator */}
        <div className="flex items-center gap-[2px] h-4 mr-0.5">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className={`w-[3px] rounded-full transition-all duration-300 ${voiceAgentSpeaking
                  ? `${barColor} animate-pulse`
                  : voiceConnected
                    ? 'bg-emerald-400'
                    : 'bg-slate-300'
                }`}
              style={{
                height: voiceAgentSpeaking
                  ? `${6 + Math.sin(Date.now() / 200 + i * 1.2) * 6}px`
                  : voiceConnected
                    ? `${4 + (i % 2) * 3}px`
                    : '4px',
                animationDelay: `${i * 80}ms`,
              }}
            />
          ))}
        </div>

        {/* Connection status dot */}
        <div className={`w-1.5 h-1.5 rounded-full ${voiceConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'
          }`} title={voiceConnected ? 'Voice connected' : 'Connecting...'} />

        {/* Session duration timer / countdown */}
        <span className={`text-[10px] font-mono font-bold tabular-nums min-w-[3ch] ${timerTextColor}`}>
          {isFinalWarning && effectiveRemaining !== null
            ? `0:${String(Math.max(0, effectiveRemaining)).padStart(2, '0')}`
            : formatTime(brainstormDuration)}
        </span>

        {isWrappingUp && !isFinalWarning && (
          <span className="text-[9px] text-amber-600 font-medium">Wrapping up...</span>
        )}

        <button
          onClick={onConcludeBrainstorming}
          className="p-1 px-2.5 text-xs font-bold text-white bg-teal-600 rounded-lg shadow hover:bg-teal-700 transition flex items-center gap-1.5"
          title="Conclude Session & Analyze"
        >
          <Brain size={14} /> Finalize
        </button>
        <button
          onClick={onCancelBrainstorming}
          className="p-1 px-2 text-xs font-bold text-slate-700 bg-white border border-slate-200 rounded-lg shadow hover:bg-slate-50 transition flex items-center gap-1"
          title="Stop without Finalizing"
        >
          <Square size={12} fill="currentColor" />
        </button>
      </div>
    );
  }

  // Default: Single-click button to start voice discussion
  return (
    <div ref={startMenuRef} className="relative">
      <button
        onClick={() => {
          if (!disabled) setIsStartMenuOpen((open) => !open);
        }}
        disabled={disabled}
        className="p-1.5 rounded-lg transition-colors text-slate-400 hover:text-teal-500 hover:bg-teal-50 disabled:opacity-40 disabled:cursor-not-allowed"
        title="Discuss with Agent — start a voice conversation"
      >
        <Brain size={18} />
      </button>

      {isStartMenuOpen && (
        <div className="absolute bottom-full right-0 mb-2 w-72 max-w-[calc(100vw-2rem)] rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] z-50">
          <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Brainstorm Start
          </p>
          <button
            onClick={() => {
              setIsStartMenuOpen(false);
              onStartBrainstorming('resume');
            }}
            className="w-full rounded-xl px-3 py-2.5 text-left transition hover:bg-teal-50"
          >
            <span className="block text-sm font-semibold text-slate-800">Continue from context</span>
            <span className="mt-0.5 block text-xs text-slate-500">
              Uses onboarding details and your latest brainstorm thread so the agent can pick up where you left off.
            </span>
          </button>
          <button
            onClick={() => {
              setIsStartMenuOpen(false);
              onStartBrainstorming('fresh');
            }}
            className="mt-1 w-full rounded-xl px-3 py-2.5 text-left transition hover:bg-slate-50"
          >
            <span className="block text-sm font-semibold text-slate-800">Start fresh</span>
            <span className="mt-0.5 block text-xs text-slate-500">
              Keeps your saved onboarding profile, but starts a brand-new brain dump without the last brainstorm thread.
            </span>
          </button>
        </div>
      )}
    </div>
  );
}


