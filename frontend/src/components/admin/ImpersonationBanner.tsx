// frontend/src/components/admin/ImpersonationBanner.tsx
'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useImpersonation } from '@/contexts/ImpersonationContext';

/** Formats milliseconds remaining as MM:SS string. */
function formatTimeRemaining(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/**
 * ImpersonationBanner renders a non-dismissible sticky banner at the top of the
 * impersonation view. It shows the target user's email and persona, a countdown
 * timer, and an Exit Impersonation button.
 *
 * Color and label behavior:
 * - Interactive mode: always bg-red-600 from activation, shows "INTERACTIVE MODE"
 * - Read-only mode: bg-amber-600 normally, transitions to bg-red-600 at < 5 min,
 *   shows "READ ONLY"
 *
 * This banner has NO close/dismiss button — it is always visible during impersonation.
 */
export function ImpersonationBanner() {
  const impersonation = useImpersonation();

  if (!impersonation) {
    return null;
  }

  const {
    targetUserEmail,
    targetPersona,
    timeRemainingMs,
    mode,
    exitImpersonation,
  } = impersonation;

  const isInteractive = mode === 'interactive';
  const isWarning = timeRemainingMs < 5 * 60 * 1000;

  // Interactive mode: always red. Read-only: amber → red at <5 min.
  const bannerBg = isInteractive || isWarning ? 'bg-red-600' : 'bg-amber-600';
  const ringOffsetColor = isInteractive || isWarning
    ? 'focus:ring-offset-red-600'
    : 'focus:ring-offset-amber-600';
  const modeLabel = isInteractive ? 'INTERACTIVE MODE' : 'READ ONLY';

  return (
    <div
      className={`${bannerBg} text-white px-4 py-2 flex items-center justify-between sticky top-0 z-[9999] transition-colors duration-300`}
      role="alert"
      aria-label="Impersonation mode active"
    >
      <span className="text-sm font-medium">
        {isInteractive && (
          <span className="mr-2 inline-flex items-center" aria-hidden="true">
            &#9888;
          </span>
        )}
        Viewing as:{' '}
        <strong>{targetUserEmail}</strong>
        {targetPersona && (
          <span className="ml-1 opacity-90">({targetPersona} persona)</span>
        )}{' '}
        &mdash; {modeLabel}
      </span>

      <div className="flex items-center gap-4">
        <span className="text-sm font-mono tabular-nums" aria-label="Session time remaining">
          {formatTimeRemaining(timeRemainingMs)}
        </span>

        <button
          type="button"
          onClick={exitImpersonation}
          className={`bg-white text-gray-900 text-xs font-semibold px-3 py-1 rounded hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 ${ringOffsetColor}`}
        >
          Exit Impersonation
        </button>
      </div>
    </div>
  );
}
