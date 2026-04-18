'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview InviteLinkGenerator — admin UI for generating workspace invite links.
 *
 * Lets a workspace admin generate a time-limited share link for a chosen role
 * (editor or viewer). The generated link can be copied to clipboard with one click.
 */

import React, { useState } from 'react';
import { fetchWithAuth } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

interface InviteLinkGeneratorProps {
  /** The workspace ID — sent to the backend to scope the invite. */
  workspaceId: string;
  /** Optional callback fired after a new invite link is generated successfully. */
  onInviteSent?: () => void;
}

type InviteRole = 'editor' | 'viewer';

// ============================================================================
// Component
// ============================================================================

/**
 * A self-contained section that generates and displays workspace invite links.
 *
 * Calls `POST /teams/invites` with the selected role and a 7-day expiry, then
 * renders the returned share URL in a read-only input with a copy-to-clipboard
 * button.
 */
export function InviteLinkGenerator({
  workspaceId,
  onInviteSent,
}: InviteLinkGeneratorProps) {
  const [role, setRole] = useState<InviteRole>('viewer');
  const [generatedLink, setGeneratedLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setGeneratedLink(null);

    try {
      const response = await fetchWithAuth('/teams/invites', {
        method: 'POST',
        body: JSON.stringify({ role, expires_hours: 168 }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const message =
          typeof data?.detail === 'string'
            ? data.detail
            : 'Failed to generate invite link. Please try again.';
        setError(message);
        return;
      }

      const data = await response.json();
      setGeneratedLink(data.share_url ?? data.token ?? '');
      onInviteSent?.();
    } catch {
      setError('Network error — please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!generatedLink) return;
    try {
      await navigator.clipboard.writeText(generatedLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select the input text so the user can copy manually.
    }
  };

  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
      <h2 className="mb-1 text-base font-semibold text-slate-900">
        Invite Team Members
      </h2>
      <p className="mb-5 text-sm text-slate-500">
        Generate a share link and send it to collaborators. Links expire in 7
        days.
      </p>

      {/* Role selector */}
      <div className="mb-5">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
          Invite as
        </p>
        <div className="flex gap-2">
          {(['viewer', 'editor'] as const).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => {
                setRole(r);
                setGeneratedLink(null);
              }}
              className={[
                'rounded-lg border px-4 py-1.5 text-sm font-medium capitalize transition-colors',
                role === r
                  ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-indigo-300 hover:text-indigo-600',
              ].join(' ')}
            >
              {r.charAt(0).toUpperCase() + r.slice(1)}
            </button>
          ))}
        </div>
        <p className="mt-1.5 text-xs text-slate-400">
          {role === 'viewer'
            ? 'Viewer: read-only access to all shared content.'
            : 'Editor: can create and edit initiatives, workflows, and content.'}
        </p>
      </div>

      {/* Generate button */}
      <button
        type="button"
        onClick={handleGenerate}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
      >
        {loading && (
          <svg
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
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
        )}
        {loading ? 'Generating…' : 'Generate Link'}
      </button>

      {/* Error state */}
      {error && (
        <p className="mt-3 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {/* Generated link */}
      {generatedLink && (
        <div className="mt-5">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
            Share link
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              readOnly
              value={generatedLink}
              className="flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              aria-label="Invite link"
            />
            <button
              type="button"
              onClick={handleCopy}
              className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-indigo-300 hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
              aria-label="Copy invite link"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <p className="mt-1.5 text-xs text-slate-400">
            Link expires in 7 days. Each link can only be used once.
          </p>
        </div>
      )}

      {/* Invisible workspace ID anchor for future extensibility */}
      <span data-workspace-id={workspaceId} className="sr-only" />
    </section>
  );
}

export default InviteLinkGenerator;
