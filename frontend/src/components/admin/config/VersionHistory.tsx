'use client';

import { useCallback, useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Shape of a single history entry from GET /admin/config/agents/{agent_name}/history */
interface HistoryEntry {
  id: string;
  config_type: string;
  config_key: string;
  previous_value: string | null;
  new_value: string | null;
  created_at: string;
}

/** Props for VersionHistory */
export interface VersionHistoryProps {
  /** Agent identifier (e.g. "financial") */
  agentName: string;
  /** Supabase access_token for Authorization header */
  token: string;
  /** Called after a successful rollback so the parent can refresh the editor */
  onRollback: () => void;
}

/**
 * Formats an ISO timestamp into a short readable string.
 * E.g. "Mar 23, 2026 01:33 UTC"
 */
function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  });
}

/** Truncates a string to maxLen characters */
function truncate(text: string | null, maxLen = 80): string {
  if (!text) return '(empty)';
  if (text.length <= maxLen) return text;
  return `${text.slice(0, maxLen)}…`;
}

/**
 * VersionHistory renders a collapsible list of configuration change history
 * for a specific agent, with a Restore button for each entry.
 */
export function VersionHistory({ agentName, token, onRollback }: VersionHistoryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restoringId, setRestoringId] = useState<string | null>(null);

  // ─── fetchHistory ────────────────────────────────────────────────────────────

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_URL}/admin/config/agents/${agentName}/history`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) {
        setError(`Failed to load history (${res.status})`);
        return;
      }
      const data = (await res.json()) as HistoryEntry[];
      setHistory(data);
    } catch {
      setError('Failed to load history. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [agentName, token]);

  // Load history the first time the panel is expanded
  useEffect(() => {
    if (isExpanded && history.length === 0 && !isLoading) {
      fetchHistory();
    }
  }, [isExpanded, history.length, isLoading, fetchHistory]);

  // ─── handleRestore ───────────────────────────────────────────────────────────

  const handleRestore = useCallback(
    async (entry: HistoryEntry) => {
      const confirmed = window.confirm(
        'Restore this version? The current instructions will be replaced.',
      );
      if (!confirmed) return;

      setRestoringId(entry.id);
      setError(null);
      try {
        const res = await fetch(
          `${API_URL}/admin/config/agents/${agentName}/rollback`,
          {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ history_id: entry.id }),
          },
        );
        if (!res.ok) {
          setError(`Rollback failed (${res.status})`);
          return;
        }
        // Refresh history list after rollback
        await fetchHistory();
        onRollback();
      } catch {
        setError('Rollback failed. Check that the backend is running.');
      } finally {
        setRestoringId(null);
      }
    },
    [agentName, token, onRollback, fetchHistory],
  );

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      {/* Accordion header */}
      <button
        type="button"
        onClick={() => setIsExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 hover:bg-gray-750 text-gray-200 text-sm font-medium transition-colors"
        aria-expanded={isExpanded}
      >
        <span>Version History</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Accordion body */}
      {isExpanded && (
        <div className="bg-gray-850 border-t border-gray-700">
          {/* Error banner */}
          {error && (
            <div className="px-4 py-3 text-sm text-red-400 bg-red-500/10 border-b border-red-500/20">
              {error}
            </div>
          )}

          {/* Loading skeleton */}
          {isLoading && (
            <div className="p-4 space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="bg-gray-700 rounded h-12 animate-pulse" />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && history.length === 0 && (
            <div className="px-4 py-6 text-center text-gray-500 text-sm">
              No version history available for this agent.
            </div>
          )}

          {/* History list */}
          {!isLoading && history.length > 0 && (
            <ul className="divide-y divide-gray-700">
              {history.map((entry) => (
                <li key={entry.id} className="px-4 py-3 flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-400 mb-1">
                      {formatTimestamp(entry.created_at)}
                    </p>
                    <p className="text-xs text-gray-500 font-mono truncate">
                      <span className="text-red-400">- </span>
                      {truncate(entry.previous_value)}
                    </p>
                    <p className="text-xs text-gray-500 font-mono truncate">
                      <span className="text-green-400">+ </span>
                      {truncate(entry.new_value)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRestore(entry)}
                    disabled={restoringId === entry.id}
                    className="shrink-0 px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-60 disabled:cursor-not-allowed text-gray-200 rounded-lg border border-gray-600 transition-colors flex items-center gap-1"
                  >
                    {restoringId === entry.id ? (
                      <>
                        <SpinnerIcon />
                        Restoring…
                      </>
                    ) : (
                      'Restore'
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

/** Inline spinner icon */
function SpinnerIcon() {
  return (
    <svg
      className="w-3 h-3 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
