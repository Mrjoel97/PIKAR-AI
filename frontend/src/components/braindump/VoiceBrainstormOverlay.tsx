'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  CheckCircle,
  AlertCircle,
  Loader2,
  Phone,
  PhoneOff,
  RefreshCw,
  X,
  FileText,
} from 'lucide-react';
import type { VoiceTranscriptTurn } from '@/hooks/useVoiceSession';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BrainstormFinalizeResult {
  success: boolean;
  transcript_markdown: string | null;
  transcript_file_path: string | null;
  saved_categories: string[];
  error: string | null;
  summary: {
    title: string;
    key_themes: string[];
    action_item_count: number;
    executive_summary: string;
  } | null;
  analysis_doc_id: string | null;
  analysis_markdown: string | null;
}

export interface VoiceBrainstormOverlayProps {
  isConnected: boolean;
  isAgentSpeaking: boolean;
  transcriptTurns: VoiceTranscriptTurn[];
  remainingSeconds: number | null;
  isWrappingUp: boolean;
  isTimedOut: boolean;
  error: string | null;
  isFinalizingBrainstorm: boolean;
  finalizeResult: BrainstormFinalizeResult | null;
  onEndSession: () => void;
  onRetry: () => void;
  onViewAnalysis: () => void;
  onDismiss: () => void;
}

// ---------------------------------------------------------------------------
// Phase derivation
// ---------------------------------------------------------------------------

type OverlayPhase =
  | 'connecting'
  | 'connection_error'
  | 'active'
  | 'active_disconnected'
  | 'processing'
  | 'summary';

function derivePhase(props: VoiceBrainstormOverlayProps): OverlayPhase {
  if (props.finalizeResult) return 'summary';
  if (props.isFinalizingBrainstorm) return 'processing';
  if (props.isConnected && !props.isFinalizingBrainstorm) return 'active';
  if (props.error && !props.isConnected && props.transcriptTurns.length > 0) return 'active_disconnected';
  if (props.error && !props.isConnected && props.transcriptTurns.length === 0) return 'connection_error';
  return 'connecting';
}

// ---------------------------------------------------------------------------
// Timer helpers
// ---------------------------------------------------------------------------

const WRAPUP_SECONDS = 720;
const FINAL_WARNING_SECONDS = 840;

type TimerPhase = 'normal' | 'wrapup' | 'final';

function getTimerPhase(elapsed: number, effectiveRemaining: number | null): TimerPhase {
  if (effectiveRemaining !== null && effectiveRemaining <= 60) return 'final';
  if (elapsed >= WRAPUP_SECONDS) return 'wrapup';
  return 'normal';
}

const TIMER_COLORS: Record<TimerPhase, { text: string; bar: string; bg: string }> = {
  normal: { text: 'text-teal-400', bar: 'bg-teal-500', bg: 'bg-teal-500/20' },
  wrapup: { text: 'text-amber-400', bar: 'bg-amber-500', bg: 'bg-amber-500/20' },
  final: { text: 'text-red-400', bar: 'bg-red-500', bg: 'bg-red-500/20' },
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PulsingBrainAvatar({ isAgentSpeaking, phase }: { isAgentSpeaking: boolean; phase: TimerPhase }) {
  const ringColor = TIMER_COLORS[phase].bar;
  return (
    <div className="relative flex items-center justify-center">
      {/* Outer pulsing ring */}
      <div
        className={`absolute h-24 w-24 rounded-full ${ringColor} transition-all duration-500 ${
          isAgentSpeaking ? 'opacity-40 scale-110 animate-pulse' : 'opacity-15 scale-100'
        }`}
      />
      <div
        className={`absolute h-20 w-20 rounded-full ${ringColor} transition-all duration-500 ${
          isAgentSpeaking ? 'opacity-30 scale-105 animate-pulse' : 'opacity-10 scale-100'
        }`}
        style={{ animationDelay: '150ms' }}
      />
      {/* Brain icon */}
      <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/30">
        <Brain className="h-8 w-8 text-white" />
      </div>
    </div>
  );
}

function TranscriptPanel({ turns }: { turns: VoiceTranscriptTurn[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns.length]);

  if (turns.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-white/30 italic">
        Conversation will appear here...
      </div>
    );
  }

  return (
    <div className="max-h-[40vh] space-y-2.5 overflow-y-auto overscroll-contain px-1 py-2 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/10">
      {turns.map((turn, i) => {
        const isUser = turn.speaker === 'user';
        return (
          <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed ${
                isUser
                  ? 'bg-teal-500/20 text-teal-100'
                  : 'bg-white/10 text-white/80'
              }`}
            >
              <span className={`text-[10px] font-semibold uppercase tracking-wider ${isUser ? 'text-teal-400' : 'text-white/40'}`}>
                {isUser ? 'You' : 'Pikar'}
              </span>
              <p className="mt-0.5">{turn.text}</p>
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase views
// ---------------------------------------------------------------------------

function ConnectingView() {
  return (
    <motion.div
      key="connecting"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="flex flex-col items-center gap-6"
    >
      <div className="relative">
        <div className="absolute inset-0 h-20 w-20 animate-ping rounded-full bg-violet-500/20" />
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/30">
          <Brain className="h-10 w-10 text-white" />
        </div>
      </div>
      <div className="text-center">
        <p className="text-lg font-medium text-white">Connecting...</p>
        <p className="mt-1 text-sm text-white/40">Setting up your brainstorm session</p>
      </div>
    </motion.div>
  );
}

function ConnectionErrorView({
  error,
  onRetry,
  onDismiss,
}: {
  error: string;
  onRetry: () => void;
  onDismiss: () => void;
}) {
  return (
    <motion.div
      key="error"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="flex flex-col items-center gap-5"
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-500/20">
        <AlertCircle className="h-8 w-8 text-red-400" />
      </div>
      <div className="text-center">
        <p className="text-lg font-medium text-white">Connection Failed</p>
        <p className="mt-1 max-w-xs text-sm text-white/50">{error}</p>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-teal-500"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </button>
        <button
          onClick={onDismiss}
          className="rounded-2xl px-5 py-2.5 text-sm font-medium text-white/60 transition hover:text-white hover:bg-white/10"
        >
          Cancel
        </button>
      </div>
    </motion.div>
  );
}

function ActiveConversationView({
  isAgentSpeaking,
  transcriptTurns,
  elapsed,
  timerPhase,
  effectiveRemaining,
  isWrappingUp,
  error,
  isDisconnected,
  onEndSession,
}: {
  isAgentSpeaking: boolean;
  transcriptTurns: VoiceTranscriptTurn[];
  elapsed: number;
  timerPhase: TimerPhase;
  effectiveRemaining: number | null;
  isWrappingUp: boolean;
  error: string | null;
  isDisconnected: boolean;
  onEndSession: () => void;
}) {
  const isFinalWarning = effectiveRemaining !== null && effectiveRemaining <= 60;
  const colors = TIMER_COLORS[timerPhase];

  const timerDisplay = isFinalWarning && effectiveRemaining !== null
    ? `0:${String(Math.max(0, effectiveRemaining)).padStart(2, '0')}`
    : formatTime(elapsed);

  return (
    <motion.div
      key="active"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="flex w-full max-w-lg flex-col items-center gap-5"
    >
      {/* Disconnect / wrap-up banner */}
      <AnimatePresence>
        {isDisconnected && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="w-full rounded-2xl bg-amber-500/20 border border-amber-500/30 px-4 py-2.5 text-center text-sm text-amber-300"
          >
            Connection lost — you can still end and save your session
          </motion.div>
        )}
        {!isDisconnected && isWrappingUp && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`w-full rounded-2xl border px-4 py-2.5 text-center text-sm ${
              isFinalWarning
                ? 'bg-red-500/20 border-red-500/30 text-red-300 animate-pulse'
                : 'bg-amber-500/20 border-amber-500/30 text-amber-300'
            }`}
          >
            {isFinalWarning ? '1 minute remaining' : 'Wrapping up — summarize your key points'}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Avatar */}
      <PulsingBrainAvatar isAgentSpeaking={isAgentSpeaking} phase={timerPhase} />

      {/* Status line */}
      <div className="flex items-center gap-2.5">
        <div className={`h-2 w-2 rounded-full ${isDisconnected ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'}`} />
        <span className="text-xs text-white/50">
          {isDisconnected ? 'Disconnected' : isAgentSpeaking ? 'Speaking...' : 'Listening...'}
        </span>
        <span className={`font-mono text-sm font-bold tabular-nums ${colors.text} ${timerPhase === 'final' ? 'animate-pulse' : ''}`}>
          {timerDisplay}
        </span>
      </div>

      {/* Transcript */}
      <div className="w-full rounded-[20px] bg-white/5 border border-white/10 p-3">
        <TranscriptPanel turns={transcriptTurns} />
      </div>

      {/* End Session */}
      <button
        onClick={onEndSession}
        className="inline-flex items-center gap-2 rounded-2xl bg-rose-600 px-6 py-3 text-sm font-medium text-white shadow-lg shadow-rose-600/20 transition hover:bg-rose-500 active:scale-95"
      >
        <PhoneOff className="h-4 w-4" />
        End Session
      </button>
    </motion.div>
  );
}

function ProcessingView({ transcriptTurns }: { transcriptTurns: VoiceTranscriptTurn[] }) {
  return (
    <motion.div
      key="processing"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="flex w-full max-w-lg flex-col items-center gap-5"
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-violet-500/20">
        <Loader2 className="h-8 w-8 text-violet-400 animate-spin" />
      </div>
      <div className="text-center">
        <p className="text-lg font-medium text-white">Generating your analysis...</p>
        <p className="mt-1 text-sm text-white/40">This usually takes a few seconds</p>
      </div>
      {transcriptTurns.length > 0 && (
        <div className="w-full rounded-[20px] bg-white/5 border border-white/10 p-3 opacity-40">
          <TranscriptPanel turns={transcriptTurns} />
        </div>
      )}
    </motion.div>
  );
}

function SummaryView({
  result,
  onDismiss,
}: {
  result: BrainstormFinalizeResult;
  onDismiss: () => void;
}) {
  // Auto-dismiss on success after 3 seconds
  useEffect(() => {
    if (!result.success) return;
    const timer = setTimeout(onDismiss, 3000);
    return () => clearTimeout(timer);
  }, [result.success, onDismiss]);

  if (!result.success) {
    return (
      <motion.div
        key="summary-error"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="flex flex-col items-center gap-5"
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-500/20">
          <AlertCircle className="h-8 w-8 text-red-400" />
        </div>
        <div className="text-center">
          <p className="text-lg font-medium text-white">{result.error || 'Session could not be saved'}</p>
        </div>
        <div className="flex items-center gap-3">
          {result.transcript_markdown && (
            <button
              onClick={onDismiss}
              className="inline-flex items-center gap-2 rounded-2xl bg-white/10 px-5 py-2.5 text-sm font-medium text-white/80 transition hover:bg-white/20"
            >
              <FileText className="h-4 w-4" />
              View Transcript
            </button>
          )}
          <button
            onClick={onDismiss}
            className="rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-teal-500"
          >
            Close
          </button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      key="summary-success"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="flex flex-col items-center gap-4 cursor-pointer"
      onClick={onDismiss}
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/20">
        <CheckCircle className="h-8 w-8 text-emerald-400" />
      </div>
      <div className="text-center">
        <p className="text-lg font-medium text-white">Session Complete</p>
        {result.summary?.title && (
          <p className="mt-1 text-sm font-medium text-white/70">{result.summary.title}</p>
        )}
        <p className="mt-2 text-xs text-white/40">Your analysis is ready in chat</p>
      </div>
      {/* Progress bar showing auto-dismiss countdown */}
      <div className="h-1 w-32 overflow-hidden rounded-full bg-white/10">
        <motion.div
          className="h-full bg-emerald-500"
          initial={{ width: '100%' }}
          animate={{ width: '0%' }}
          transition={{ duration: 3, ease: 'linear' }}
        />
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main overlay
// ---------------------------------------------------------------------------

export default function VoiceBrainstormOverlay(props: VoiceBrainstormOverlayProps) {
  const phase = derivePhase(props);

  // Elapsed timer (counts up every second while active)
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (phase === 'active' || phase === 'active_disconnected') {
      if (!timerRef.current) {
        timerRef.current = setInterval(() => setElapsed((p) => p + 1), 1000);
      }
    } else if (phase === 'processing' || phase === 'summary') {
      // Keep timer frozen but don't clear elapsed
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    } else {
      // Connecting / error — reset
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setElapsed(0);
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [phase]);

  // Local countdown from server's remainingSeconds
  const [localCountdown, setLocalCountdown] = useState<number | null>(null);
  useEffect(() => {
    if (props.remainingSeconds !== null) setLocalCountdown(props.remainingSeconds);
  }, [props.remainingSeconds]);
  useEffect(() => {
    if (localCountdown === null || localCountdown <= 0) return;
    const t = setTimeout(() => setLocalCountdown((p) => (p !== null ? Math.max(0, p - 1) : null)), 1000);
    return () => clearTimeout(t);
  }, [localCountdown]);

  const effectiveRemaining = localCountdown ?? props.remainingSeconds;
  const timerPhase = getTimerPhase(elapsed, effectiveRemaining);

  // Warn before browser navigation during active session
  useEffect(() => {
    if (phase !== 'active' && phase !== 'active_disconnected') return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [phase]);

  // Portal target
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  const overlay = (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg px-4">
        <AnimatePresence mode="wait">
          {phase === 'connecting' && <ConnectingView />}

          {phase === 'connection_error' && (
            <ConnectionErrorView
              error={props.error || 'Connection failed'}
              onRetry={props.onRetry}
              onDismiss={props.onDismiss}
            />
          )}

          {(phase === 'active' || phase === 'active_disconnected') && (
            <ActiveConversationView
              isAgentSpeaking={props.isAgentSpeaking}
              transcriptTurns={props.transcriptTurns}
              elapsed={elapsed}
              timerPhase={timerPhase}
              effectiveRemaining={effectiveRemaining}
              isWrappingUp={props.isWrappingUp}
              error={props.error}
              isDisconnected={phase === 'active_disconnected'}
              onEndSession={props.onEndSession}
            />
          )}

          {phase === 'processing' && (
            <ProcessingView transcriptTurns={props.transcriptTurns} />
          )}

          {phase === 'summary' && props.finalizeResult && (
            <SummaryView
              result={props.finalizeResult}
              onDismiss={props.onDismiss}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );

  return createPortal(overlay, document.body);
}
