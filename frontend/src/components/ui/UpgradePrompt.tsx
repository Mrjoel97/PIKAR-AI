'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Reusable upgrade prompt component for feature gating.
 *
 * Renders a contextual upgrade prompt whenever a user's persona tier does not
 * meet the minimum tier for a feature. Supports three layout variants to fit
 * different rendering contexts: full page, sidebar inline, and card widget.
 *
 * This is SOFT gating only — the CTA links to the billing page plan comparison
 * rather than a payment flow directly.
 *
 * Usage:
 * ```tsx
 * const { allowed } = useFeatureGate('workflows');
 * if (!allowed) return <UpgradePrompt featureKey="workflows" variant="page" />;
 * ```
 */

import Link from 'next/link';
import { Lock } from 'lucide-react';

import { useFeatureGate } from '@/hooks/useFeatureGate';
import { PERSONA_INFO } from '@/services/onboarding';
import { FEATURE_ACCESS, type FeatureKey, type PersonaTier } from '@/config/featureGating';

// ============================================================================
// Types
// ============================================================================

export interface UpgradePromptProps {
  /** Which feature is locked — drives the label, description, and required tier. */
  featureKey: FeatureKey;
  /**
   * Rendering context:
   * - `'page'`    — Full-page centered card, shown when navigating to a gated page.
   * - `'sidebar'` — Compact horizontal inline banner next to a locked nav item.
   * - `'card'`    — Medium card format for dashboard widget tiles.
   */
  variant?: 'page' | 'sidebar' | 'card';
  /** Additional Tailwind classes forwarded to the root element. */
  className?: string;
}

// ============================================================================
// Shimmer placeholder
// ============================================================================

function ShimmerPlaceholder({ variant }: { variant: 'page' | 'sidebar' | 'card' }) {
  if (variant === 'sidebar') {
    return (
      <div className="flex items-center gap-2 px-2 py-1 animate-pulse">
        <div className="h-3 w-3 rounded-full bg-slate-200" />
        <div className="h-3 w-24 rounded bg-slate-200" />
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 animate-pulse space-y-3">
        <div className="h-4 w-4 rounded-full bg-slate-200" />
        <div className="h-4 w-32 rounded bg-slate-200" />
        <div className="h-3 w-full rounded bg-slate-200" />
        <div className="h-8 w-24 rounded-lg bg-slate-200" />
      </div>
    );
  }

  // page
  return (
    <div className="flex flex-col items-center justify-center py-24 animate-pulse space-y-4">
      <div className="h-12 w-12 rounded-full bg-slate-200" />
      <div className="h-6 w-48 rounded bg-slate-200" />
      <div className="h-4 w-72 rounded bg-slate-200" />
      <div className="h-10 w-32 rounded-lg bg-slate-200" />
    </div>
  );
}

// ============================================================================
// Tier label helper
// ============================================================================

function TierBadge({ tier }: { tier: PersonaTier }) {
  const info = PERSONA_INFO[tier];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-gradient-to-r ${info.color} px-2.5 py-0.5 text-xs font-semibold text-white`}
    >
      {info.title}
    </span>
  );
}

// ============================================================================
// Component
// ============================================================================

/**
 * Displays an upgrade prompt for a locked feature.
 *
 * Internally calls `useFeatureGate` so the caller only needs to pass the
 * feature key. Shows a shimmer while loading.
 */
export function UpgradePrompt({
  featureKey,
  variant = 'page',
  className,
}: UpgradePromptProps) {
  const { currentTier, requiredTier, isLoading, featureLabel } = useFeatureGate(featureKey);

  if (isLoading) {
    return <ShimmerPlaceholder variant={variant} />;
  }

  // ── Sidebar variant ──────────────────────────────────────────────────────
  if (variant === 'sidebar') {
    return (
      <div
        className={`flex items-center gap-1.5 px-2 py-1 rounded-lg bg-slate-100 border border-slate-200 text-xs text-slate-500 ${className ?? ''}`}
      >
        <Lock className="h-3 w-3 text-slate-400 shrink-0" />
        <span className="truncate">{featureLabel}</span>
        <Link
          href="/dashboard/billing"
          className="ml-auto shrink-0 font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
        >
          Upgrade
        </Link>
      </div>
    );
  }

  // ── Card variant ─────────────────────────────────────────────────────────
  if (variant === 'card') {
    return (
      <div
        className={`rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-slate-100 p-5 flex flex-col gap-3 ${className ?? ''}`}
      >
        <Lock className="h-5 w-5 text-slate-400" />

        <div>
          <p className="text-sm font-semibold text-slate-800">{featureLabel}</p>
          <p className="mt-0.5 text-xs text-slate-500 leading-relaxed">
            {/* description is shown in full-size variants; card just shows tier info */}
            Available from <TierBadge tier={requiredTier} /> plan and above.
          </p>
        </div>

        {currentTier && (
          <p className="text-xs text-slate-400">
            Your plan: <TierBadge tier={currentTier} />
          </p>
        )}

        <Link
          href="/dashboard/billing"
          className="inline-flex items-center justify-center rounded-lg bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white transition-colors self-start"
        >
          View Plans
        </Link>
      </div>
    );
  }

  // ── Page variant (default) ───────────────────────────────────────────────
  const featureConfig = FEATURE_ACCESS[featureKey];

  return (
    <div
      className={`flex flex-col items-center justify-center min-h-[60vh] px-6 py-16 ${className ?? ''}`}
    >
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-gradient-to-br from-slate-50 to-slate-100 p-8 flex flex-col items-center gap-5 shadow-sm">
        {/* Lock icon */}
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white shadow-md border border-slate-200">
          <Lock className="h-7 w-7 text-slate-400" />
        </div>

        {/* Feature name */}
        <h2 className="text-lg font-semibold text-slate-800 text-center">{featureLabel}</h2>

        {/* Description */}
        <p className="text-sm text-slate-500 text-center leading-relaxed max-w-xs">
          {featureConfig.description}
        </p>

        {/* Tier info */}
        <div className="flex flex-col items-center gap-2 w-full">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span>Required plan:</span>
            <TierBadge tier={requiredTier} />
          </div>
          {currentTier && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <span>Your current plan:</span>
              <TierBadge tier={currentTier} />
            </div>
          )}
        </div>

        {/* CTA */}
        <Link
          href="/dashboard/billing"
          className="mt-2 inline-flex items-center justify-center rounded-lg bg-indigo-600 hover:bg-indigo-700 px-6 py-3 text-sm font-semibold text-white transition-colors shadow-md w-full max-w-[200px]"
        >
          View Plans
        </Link>
      </div>
    </div>
  );
}

export default UpgradePrompt;
