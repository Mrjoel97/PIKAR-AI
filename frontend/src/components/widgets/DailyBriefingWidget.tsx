/**
 * DailyBriefingWidget — Inbox intelligence panel.
 *
 * Displays triage items grouped by urgency with approve/dismiss actions,
 * auto-handled log, and FYI section. Supports realtime updates via
 * Supabase channel and keyboard navigation (j/k/a/d).
 */

'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Inbox,
  Loader2,
  RefreshCw,
  RotateCcw,
  Send,
  X,
} from 'lucide-react';
import { WidgetDefinition } from '@/types/widgets';
import { createClient } from '@/lib/supabase/client';
import {
  approveTriageItem,
  dismissTriageItem,
  getBriefingToday,
  refreshBriefing,
  TriageItem,
  BriefingSections,
} from '@/services/briefing';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  definition: WidgetDefinition;
  onAction?: (action: string, data: unknown) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

function formatDate(date: Date): string {
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}

function formatTime(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function avatarLetter(name: string | null, email: string): string {
  if (name && name.trim().length > 0) return name.trim()[0].toUpperCase();
  return email[0].toUpperCase();
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface TriageCardProps {
  item: TriageItem;
  isSelected: boolean;
  onApprove: (id: string, draft?: string) => void;
  onDismiss: (id: string) => void;
}

function TriageCard({ item, isSelected, onApprove, onDismiss }: TriageCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState(item.draft_reply ?? '');
  const [isEditing, setIsEditing] = useState(false);

  const priorityBadge =
    item.priority === 'urgent' ? (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-500/20 text-red-400 border border-red-500/30">
        <AlertCircle className="w-2.5 h-2.5" />
        Urgent
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
        Important
      </span>
    );

  return (
    <div
      className={`rounded-lg border transition-all cursor-pointer ${
        isSelected
          ? 'border-indigo-500/60 bg-slate-800'
          : 'border-slate-700 bg-slate-800/50 hover:bg-slate-800'
      }`}
      onClick={() => setExpanded((e) => !e)}
    >
      {/* Card header */}
      <div className="flex items-start gap-3 p-3">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center text-sm font-semibold text-indigo-300">
          {avatarLetter(item.sender_name, item.sender)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-200 truncate">
              {item.sender_name ?? item.sender}
            </span>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              {priorityBadge}
              {item.category && (
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-700 text-slate-400 border border-slate-600">
                  {item.category}
                </span>
              )}
              <span className="text-[10px] text-slate-500 flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />
                {formatTime(item.received_at)}
              </span>
            </div>
          </div>
          <p className="text-xs font-medium text-slate-300 mt-0.5 truncate">
            {item.subject ?? '(no subject)'}
          </p>
          <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
            {item.snippet}
          </p>
        </div>

        {/* Chevron */}
        <div className="flex-shrink-0 text-slate-500">
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </div>
      </div>

      {/* Expanded reply draft */}
      {expanded && (
        <div
          className="border-t border-slate-700 p-3"
          onClick={(e) => e.stopPropagation()}
        >
          {draft ? (
            <>
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                Draft Reply
              </p>
              <textarea
                className="w-full text-xs text-slate-200 bg-slate-900 border border-slate-600 rounded p-2 resize-y min-h-[80px] focus:outline-none focus:border-indigo-500 transition-colors"
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  setIsEditing(true);
                }}
              />
            </>
          ) : (
            <p className="text-xs text-slate-500 italic mb-2">No draft reply generated.</p>
          )}

          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={() => onApprove(item.id, draft || undefined)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
            >
              <Send className="w-3 h-3" />
              {draft ? 'Approve & Send' : 'Approve'}
            </button>
            {isEditing && (
              <button
                onClick={() => {
                  setDraft(item.draft_reply ?? '');
                  setIsEditing(false);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-600/40 transition-colors"
              >
                Reset
              </button>
            )}
            <button
              onClick={() => onDismiss(item.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors ml-auto"
            >
              <X className="w-3 h-3" />
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function DailyBriefingWidget({ definition, onAction }: Props) {
  const [sections, setSections] = useState<BriefingSections>({
    urgent: [],
    needs_reply: [],
    auto_handled: [],
    fyi: [],
  });
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoHandledOpen, setAutoHandledOpen] = useState(false);
  const [fyiOpen, setFyiOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Flat list of actionable items for keyboard nav
  const actionableItems = [...sections.urgent, ...sections.needs_reply];
  const selectedItem = actionableItems[selectedIndex] ?? null;

  // Refs to preserve stable access in keyboard handler
  const sectionsRef = useRef(sections);
  sectionsRef.current = sections;
  const selectedIndexRef = useRef(selectedIndex);
  selectedIndexRef.current = selectedIndex;

  // ------------------------------------------------------------------
  // Data fetching
  // ------------------------------------------------------------------

  const loadBriefing = useCallback(async () => {
    try {
      setError(null);
      const data = await getBriefingToday();
      setSections(data.sections);
      setCounts(data.counts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load briefing');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBriefing();
  }, [loadBriefing]);

  // ------------------------------------------------------------------
  // Supabase realtime subscription
  // ------------------------------------------------------------------

  useEffect(() => {
    const supabase = createClient();
    const channel = supabase
      .channel('daily_briefing:email_triage')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'email_triage' },
        () => {
          // Re-fetch on any change
          void loadBriefing();
        },
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [loadBriefing]);

  // ------------------------------------------------------------------
  // Actions
  // ------------------------------------------------------------------

  const handleApprove = useCallback(async (id: string, draftText?: string) => {
    // Optimistic removal
    setSections((prev) => ({
      ...prev,
      urgent: prev.urgent.filter((i) => i.id !== id),
      needs_reply: prev.needs_reply.filter((i) => i.id !== id),
    }));
    try {
      await approveTriageItem(id, draftText);
      if (onAction) onAction('approve', { id });
    } catch {
      // Revert on failure
      void loadBriefing();
    }
  }, [onAction, loadBriefing]);

  const handleDismiss = useCallback(async (id: string) => {
    // Optimistic removal
    setSections((prev) => ({
      ...prev,
      urgent: prev.urgent.filter((i) => i.id !== id),
      needs_reply: prev.needs_reply.filter((i) => i.id !== id),
    }));
    try {
      await dismissTriageItem(id);
      if (onAction) onAction('dismiss', { id });
    } catch {
      void loadBriefing();
    }
  }, [onAction, loadBriefing]);

  const handleUndo = useCallback(
    async (id: string) => {
      try {
        const { undoTriageAction } = await import('@/services/briefing');
        await undoTriageAction(id);
        void loadBriefing();
        if (onAction) onAction('undo', { id });
      } catch {
        // silently ignore
      }
    },
    [onAction, loadBriefing],
  );

  const handleRefresh = useCallback(async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await refreshBriefing();
      await loadBriefing();
    } catch {
      // silently ignore
    } finally {
      setRefreshing(false);
    }
  }, [refreshing, loadBriefing]);

  // ------------------------------------------------------------------
  // Keyboard shortcuts
  // ------------------------------------------------------------------

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ignore when typing in inputs/textareas
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }
      const total = sectionsRef.current.urgent.length + sectionsRef.current.needs_reply.length;
      if (e.key === 'j') {
        setSelectedIndex((i) => Math.min(i + 1, Math.max(0, total - 1)));
      } else if (e.key === 'k') {
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'a') {
        const item = [...sectionsRef.current.urgent, ...sectionsRef.current.needs_reply][selectedIndexRef.current];
        if (item) void handleApprove(item.id, item.draft_reply ?? undefined);
      } else if (e.key === 'd') {
        const item = [...sectionsRef.current.urgent, ...sectionsRef.current.needs_reply][selectedIndexRef.current];
        if (item) void handleDismiss(item.id);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleApprove, handleDismiss]);

  // ------------------------------------------------------------------
  // Counts
  // ------------------------------------------------------------------

  const urgentCount = sections.urgent.length;
  const needsReplyCount = sections.needs_reply.length;
  const autoHandledCount = sections.auto_handled.length;
  const fyiCount = sections.fyi.length;
  const hasItems = urgentCount + needsReplyCount + autoHandledCount + fyiCount > 0;

  // Group FYI items by category
  const fyiByCategory: Record<string, TriageItem[]> = {};
  for (const item of sections.fyi) {
    const cat = item.category ?? 'General';
    if (!fyiByCategory[cat]) fyiByCategory[cat] = [];
    fyiByCategory[cat].push(item);
  }

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <div className="w-full bg-slate-900 text-white rounded-lg border border-slate-700 overflow-hidden">
      {/* ------------------------------------------------------------------ */}
      {/* Header */}
      {/* ------------------------------------------------------------------ */}
      <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/60">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Inbox className="w-4 h-4 text-indigo-400" />
              <h3 className="font-semibold text-slate-100 text-sm">
                {getGreeting()}
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{formatDate(new Date())}</p>
          </div>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            aria-label="Refresh briefing"
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Quick stats */}
        {!loading && !error && (
          <div className="flex flex-wrap gap-1.5 mt-2.5">
            {urgentCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-500/20 text-red-400 border border-red-500/30">
                <AlertCircle className="w-3 h-3" />
                {urgentCount} urgent
              </span>
            )}
            {needsReplyCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                {needsReplyCount} needs reply
              </span>
            )}
            {autoHandledCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                {autoHandledCount} auto-handled
              </span>
            )}
            {fyiCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-600/60 text-slate-400 border border-slate-600">
                {fyiCount} fyi
              </span>
            )}
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Body */}
      {/* ------------------------------------------------------------------ */}
      <div className="p-3 space-y-4 max-h-[600px] overflow-y-auto">
        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-10 gap-2 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-sm">Loading briefing…</span>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-900/20 border border-red-700/40 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && !hasItems && (
          <div className="flex flex-col items-center justify-center py-12 gap-2 text-slate-400">
            <CheckCircle2 className="w-10 h-10 text-emerald-500/60" />
            <p className="text-sm font-medium text-slate-300">Inbox zero</p>
            <p className="text-xs text-slate-500">Nothing needs your attention right now.</p>
          </div>
        )}

        {!loading && !error && hasItems && (
          <>
            {/* ------------------------------------------------------------ */}
            {/* Urgent + Needs Reply */}
            {/* ------------------------------------------------------------ */}
            {(urgentCount > 0 || needsReplyCount > 0) && (
              <section>
                <h4 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  Action Required ({urgentCount + needsReplyCount})
                </h4>
                <div className="space-y-2">
                  {[...sections.urgent, ...sections.needs_reply].map((item, idx) => (
                    <TriageCard
                      key={item.id}
                      item={item}
                      isSelected={selectedItem?.id === item.id}
                      onApprove={handleApprove}
                      onDismiss={handleDismiss}
                    />
                  ))}
                </div>

                <p className="text-[10px] text-slate-600 mt-2">
                  Keyboard: <kbd className="px-1 py-0.5 bg-slate-800 border border-slate-600 rounded text-slate-400">j</kbd>/
                  <kbd className="px-1 py-0.5 bg-slate-800 border border-slate-600 rounded text-slate-400">k</kbd> navigate ·{' '}
                  <kbd className="px-1 py-0.5 bg-slate-800 border border-slate-600 rounded text-slate-400">a</kbd> approve ·{' '}
                  <kbd className="px-1 py-0.5 bg-slate-800 border border-slate-600 rounded text-slate-400">d</kbd> dismiss
                </p>
              </section>
            )}

            {/* ------------------------------------------------------------ */}
            {/* Auto-Handled (collapsible) */}
            {/* ------------------------------------------------------------ */}
            {autoHandledCount > 0 && (
              <section>
                <button
                  className="w-full flex items-center justify-between text-left group"
                  onClick={() => setAutoHandledOpen((o) => !o)}
                >
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 group-hover:text-slate-400 transition-colors">
                    Auto-Handled ({autoHandledCount})
                  </h4>
                  {autoHandledOpen ? (
                    <ChevronDown className="w-3 h-3 text-slate-600" />
                  ) : (
                    <ChevronRight className="w-3 h-3 text-slate-600" />
                  )}
                </button>

                {autoHandledOpen && (
                  <div className="mt-2 space-y-1.5">
                    {sections.auto_handled.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-start gap-2 px-3 py-2 rounded-lg bg-slate-800/40 border border-slate-700/50"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-slate-300 truncate">
                            <span className="font-medium">{item.sender_name ?? item.sender}</span>
                            {item.subject && (
                              <span className="text-slate-500"> · {item.subject}</span>
                            )}
                          </p>
                          {item.auto_action_taken && (
                            <p className="text-[10px] text-emerald-500/80 mt-0.5">
                              {item.auto_action_taken}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => handleUndo(item.id)}
                          className="flex-shrink-0 flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-700 hover:bg-slate-600 text-slate-400 hover:text-slate-200 transition-colors"
                          aria-label="Undo auto-action"
                        >
                          <RotateCcw className="w-2.5 h-2.5" />
                          Undo
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* ------------------------------------------------------------ */}
            {/* FYI (collapsible) */}
            {/* ------------------------------------------------------------ */}
            {fyiCount > 0 && (
              <section>
                <button
                  className="w-full flex items-center justify-between text-left group"
                  onClick={() => setFyiOpen((o) => !o)}
                >
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 group-hover:text-slate-400 transition-colors">
                    FYI ({fyiCount})
                  </h4>
                  {fyiOpen ? (
                    <ChevronDown className="w-3 h-3 text-slate-600" />
                  ) : (
                    <ChevronRight className="w-3 h-3 text-slate-600" />
                  )}
                </button>

                {fyiOpen && (
                  <div className="mt-2 space-y-3">
                    {Object.entries(fyiByCategory).map(([category, items]) => (
                      <div key={category}>
                        <p className="text-[10px] font-medium text-slate-600 uppercase tracking-wider mb-1">
                          {category}
                        </p>
                        <div className="space-y-1">
                          {items.map((item) => (
                            <div
                              key={item.id}
                              className="flex items-baseline gap-2 px-2 py-1 rounded hover:bg-slate-800/60 transition-colors"
                            >
                              <span className="flex-shrink-0 w-1 h-1 rounded-full bg-slate-600 mt-1.5" />
                              <p className="text-xs text-slate-400 line-clamp-1">
                                <span className="font-medium text-slate-300">
                                  {item.sender_name ?? item.sender}
                                </span>{' '}
                                {item.subject && `— ${item.subject}`}
                                {item.snippet && (
                                  <span className="text-slate-500"> · {item.snippet}</span>
                                )}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
