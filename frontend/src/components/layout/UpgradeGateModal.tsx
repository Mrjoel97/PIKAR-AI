'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Reusable upgrade prompt modal component.
 *
 * Shown when a user on a restricted tier attempts to access a gated feature,
 * either by clicking a locked nav item or via a 403 API response intercepted
 * in fetchWithAuth.
 */

import React from 'react';
import { Lock, X, ArrowUpRight } from 'lucide-react';
import { FEATURE_ACCESS } from '@/config/featureGating';
import type { FeatureKey } from '@/config/featureGating';

// ============================================================================
// Types
// ============================================================================

/** Props for the UpgradeGateModal. */
export interface UpgradeGateModalProps {
  /** Whether the modal is visible. */
  isOpen: boolean;
  /** Callback fired when the user dismisses the modal. */
  onClose: () => void;
  /** Feature key from the 403 response (e.g. "compliance"). */
  feature: string;
  /** The user's current tier. */
  currentTier: string;
  /** The minimum tier required to access the feature. */
  requiredTier: string;
}

// ============================================================================
// Tier display helpers
// ============================================================================

/** Capitalises the first letter of a tier name for display purposes. */
function formatTierName(tier: string): string {
  if (!tier) return '';
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

// ============================================================================
// Component
// ============================================================================

/**
 * Modal shown when a user tries to access a feature above their current tier.
 *
 * - Non-enterprise gates: "Upgrade to {tier}" CTA → `/dashboard/billing`
 * - Enterprise gates: "Contact us" CTA → `/dashboard/billing`
 *
 * The Stripe checkout price-ID lookup is intentionally deferred to the billing
 * page so this component remains free of hardcoded price constants.
 */
export function UpgradeGateModal({
  isOpen,
  onClose,
  feature,
  requiredTier,
}: UpgradeGateModalProps) {
  if (!isOpen) return null;

  // Look up feature metadata from the gating config.
  const featureConfig = FEATURE_ACCESS[feature as FeatureKey] ?? null;
  const featureLabel = featureConfig?.label ?? feature;
  const featureDescription =
    featureConfig?.description ??
    `This feature requires the ${formatTierName(requiredTier)} plan.`;

  const isEnterprise = requiredTier === 'enterprise';

  const handleCtaClick = () => {
    window.location.href = '/dashboard/billing';
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only close when clicking the backdrop itself, not its children.
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    /* Backdrop overlay */
    <div
      data-testid="upgrade-gate-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="upgrade-gate-title"
    >
      {/* Modal card */}
      <div className="relative w-full max-w-md rounded-2xl bg-white shadow-[0_20px_60px_-10px_rgba(0,0,0,0.25)] ring-1 ring-slate-900/5 overflow-hidden">

        {/* Close button */}
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all duration-150"
        >
          <X size={16} />
        </button>

        {/* Header */}
        <div className="px-6 pt-7 pb-5 text-center">
          {/* Lock icon in gradient circle */}
          <div className="mx-auto mb-4 h-14 w-14 rounded-2xl bg-gradient-to-br from-teal-50 to-cyan-100 flex items-center justify-center ring-1 ring-teal-200/60">
            <Lock className="h-6 w-6 text-teal-600" />
          </div>

          <h2
            id="upgrade-gate-title"
            className="text-xl font-bold text-slate-900 font-outfit tracking-tight"
          >
            Unlock {featureLabel}
          </h2>

          <p className="mt-2 text-sm text-slate-500 leading-relaxed">
            {featureDescription}
          </p>
        </div>

        {/* Tier badge */}
        <div className="mx-6 mb-5 flex items-center justify-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700 ring-1 ring-teal-200/60">
            <ArrowUpRight size={12} />
            Available on the{' '}
            <span className="capitalize">{requiredTier}</span> plan
          </span>
        </div>

        {/* Actions */}
        <div className="px-6 pb-6 flex flex-col gap-2.5">
          {isEnterprise ? (
            <button
              onClick={handleCtaClick}
              className="w-full rounded-xl bg-gradient-to-r from-teal-600 to-cyan-600 px-4 py-3 text-sm font-semibold text-white shadow-[0_4px_14px_-4px_rgba(20,184,166,0.5)] hover:shadow-[0_6px_20px_-4px_rgba(20,184,166,0.6)] hover:from-teal-500 hover:to-cyan-500 transition-all duration-200 active:scale-[0.98]"
            >
              Contact us
            </button>
          ) : (
            <button
              onClick={handleCtaClick}
              className="w-full rounded-xl bg-gradient-to-r from-teal-600 to-cyan-600 px-4 py-3 text-sm font-semibold text-white shadow-[0_4px_14px_-4px_rgba(20,184,166,0.5)] hover:shadow-[0_6px_20px_-4px_rgba(20,184,166,0.6)] hover:from-teal-500 hover:to-cyan-500 transition-all duration-200 active:scale-[0.98]"
            >
              Upgrade to{' '}
              <span className="capitalize">{requiredTier}</span>
            </button>
          )}

          <button
            onClick={onClose}
            className="w-full rounded-xl px-4 py-2.5 text-sm font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition-all duration-200"
          >
            Maybe later
          </button>
        </div>
      </div>
    </div>
  );
}

export default UpgradeGateModal;
