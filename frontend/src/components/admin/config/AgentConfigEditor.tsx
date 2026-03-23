'use client';

import { useCallback, useEffect, useState } from 'react';
import { DiffPanel } from './DiffPanel';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Shape returned by GET /admin/config/agents/{agent_name} */
interface AgentConfigDetail {
  agent_name: string;
  current_instructions: string;
  version: number;
  updated_at: string;
}

/** Shape returned by PUT /admin/config/agents/{agent_name} */
interface SaveResult {
  agent_name: string;
  version: number;
  diff: string;
  status: string;
}

/** Shape returned by POST /admin/config/agents/{agent_name}/preview-diff */
interface DiffPreviewResult {
  diff: string;
}

/** 422 response body for injection attempt */
interface InjectionViolation {
  detail: string | Array<{ msg: string }>;
}

/** Props for AgentConfigEditor */
export interface AgentConfigEditorProps {
  /** Agent identifier (e.g. "financial") */
  agentName: string;
  /** Supabase access_token for Authorization header */
  token: string;
  /** Called after a successful save so parent can refresh version history */
  onSaved?: () => void;
}

/**
 * AgentConfigEditor renders a textarea to view and edit an agent's system instructions.
 *
 * Features:
 * - Loads current instructions from GET /admin/config/agents/{agent_name}
 * - Shows a "Preview Diff" button when text differs from original
 * - Renders a DiffPanel showing the unified diff before committing
 * - Saves via PUT /admin/config/agents/{agent_name}
 * - Rejects injection attempts (HTTP 422) with violation detail
 * - Displays the current version number badge
 */
export function AgentConfigEditor({ agentName, token, onSaved }: AgentConfigEditorProps) {
  const [instructions, setInstructions] = useState('');
  const [originalInstructions, setOriginalInstructions] = useState('');
  const [diff, setDiff] = useState('');
  const [version, setVersion] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingDiff, setIsLoadingDiff] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // ─── Load current instructions ─────────────────────────────────────────────

  const fetchInstructions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setDiff('');
    setSaveSuccess(false);
    try {
      const res = await fetch(`${API_URL}/admin/config/agents/${agentName}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setError(`Failed to load instructions (${res.status})`);
        return;
      }
      const data = (await res.json()) as AgentConfigDetail;
      setInstructions(data.current_instructions);
      setOriginalInstructions(data.current_instructions);
      setVersion(data.version);
    } catch {
      setError('Failed to load instructions. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [agentName, token]);

  useEffect(() => {
    fetchInstructions();
  }, [fetchInstructions]);

  // ─── Preview diff ────────────────────────────────────────────────────────────

  const handlePreviewDiff = useCallback(async () => {
    setIsLoadingDiff(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_URL}/admin/config/agents/${agentName}/preview-diff`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ proposed_instructions: instructions }),
        },
      );
      if (!res.ok) {
        setError(`Preview failed (${res.status})`);
        return;
      }
      const data = (await res.json()) as DiffPreviewResult;
      setDiff(data.diff);
    } catch {
      setError('Preview failed. Check that the backend is running.');
    } finally {
      setIsLoadingDiff(false);
    }
  }, [agentName, token, instructions]);

  // ─── Save changes ────────────────────────────────────────────────────────────

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const res = await fetch(`${API_URL}/admin/config/agents/${agentName}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ new_instructions: instructions }),
      });

      if (res.status === 422) {
        const body = (await res.json()) as InjectionViolation;
        const detail =
          typeof body.detail === 'string'
            ? body.detail
            : Array.isArray(body.detail)
              ? body.detail.map((v) => v.msg).join(', ')
              : 'Injection attempt detected — change rejected.';
        setError(`Security violation: ${detail}`);
        return;
      }

      if (!res.ok) {
        setError(`Save failed (${res.status})`);
        return;
      }

      const data = (await res.json()) as SaveResult;
      setVersion(data.version);
      setOriginalInstructions(instructions);
      setDiff('');
      setSaveSuccess(true);
      onSaved?.();

      // Auto-dismiss success banner after 4 seconds
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch {
      setError('Save failed. Check that the backend is running.');
    } finally {
      setIsSaving(false);
    }
  }, [agentName, token, instructions, onSaved]);

  // ─── Derived state ───────────────────────────────────────────────────────────

  const hasChanges = instructions !== originalInstructions;

  // ─── Render ──────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="bg-gray-800 rounded-lg h-6 w-32 animate-pulse" />
        <div className="bg-gray-800 rounded-lg h-64 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Version badge */}
      {version !== null && (
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            v{version}
          </span>
          <span className="text-xs text-gray-500">Current version</span>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <span className="flex-1">{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="opacity-60 hover:opacity-100 shrink-0"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Success banner */}
      {saveSuccess && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
          Instructions saved successfully. Now at version {version}.
        </div>
      )}

      {/* Textarea */}
      <textarea
        value={instructions}
        onChange={(e) => {
          setInstructions(e.target.value);
          setDiff(''); // clear stale diff when text changes
        }}
        className="w-full min-h-[300px] bg-gray-800 border border-gray-600 text-gray-100 font-mono text-sm rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y placeholder-gray-600"
        placeholder="Agent instructions will appear here..."
        spellCheck={false}
      />

      {/* Action buttons */}
      {hasChanges && (
        <div className="flex items-center gap-3 flex-wrap">
          <button
            type="button"
            onClick={handlePreviewDiff}
            disabled={isLoadingDiff}
            className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-60 disabled:cursor-not-allowed text-gray-100 rounded-lg border border-gray-600 transition-colors flex items-center gap-1.5"
          >
            {isLoadingDiff ? (
              <>
                <SpinnerIcon />
                Generating diff…
              </>
            ) : (
              'Preview Diff'
            )}
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-1.5"
          >
            {isSaving ? (
              <>
                <SpinnerIcon />
                Saving…
              </>
            ) : (
              'Save Changes'
            )}
          </button>

          <button
            type="button"
            onClick={() => {
              setInstructions(originalInstructions);
              setDiff('');
              setError(null);
            }}
            className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg border border-gray-600 transition-colors"
          >
            Discard
          </button>
        </div>
      )}

      {/* Diff panel */}
      {diff && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wide">
            Proposed Changes
          </h4>
          <DiffPanel diff={diff} />
        </div>
      )}
    </div>
  );
}

/** Inline spinner icon */
function SpinnerIcon() {
  return (
    <svg
      className="w-3.5 h-3.5 animate-spin"
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
