'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview GatedPage wrapper component.
 *
 * Wraps a page's children and checks feature access before rendering.
 * If the current user's tier does not meet the feature's minimum tier,
 * renders a full-page UpgradePrompt instead of the page content.
 *
 * Usage:
 * ```tsx
 * export default function WorkflowsPage() {
 *   return (
 *     <GatedPage featureKey="workflows">
 *       <WorkflowsContent />
 *     </GatedPage>
 *   );
 * }
 * ```
 */

import React from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { UpgradePrompt } from '@/components/ui/UpgradePrompt';
import { useFeatureGate } from '@/hooks/useFeatureGate';
import { type FeatureKey } from '@/config/featureGating';

// ============================================================================
// Types
// ============================================================================

interface GatedPageProps {
  /** The feature identifier to gate on. */
  featureKey: FeatureKey;
  /** Page content to render when access is allowed. */
  children: React.ReactNode;
}

// ============================================================================
// Loading shimmer
// ============================================================================

function GatedPageShimmer() {
  return (
    <PremiumShell>
      <div className="flex flex-col gap-6 p-6 animate-pulse">
        <div className="h-8 w-48 rounded-xl bg-slate-100" />
        <div className="h-4 w-72 rounded bg-slate-100" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded-[28px] bg-slate-100" />
          ))}
        </div>
        <div className="h-64 rounded-[28px] bg-slate-100" />
      </div>
    </PremiumShell>
  );
}

// ============================================================================
// Component
// ============================================================================

/**
 * Renders children when the current user's tier allows access to the feature.
 * Shows a full-page UpgradePrompt when access is denied.
 * Shows a loading shimmer while the persona is being fetched.
 */
export function GatedPage({ featureKey, children }: GatedPageProps) {
  const gate = useFeatureGate(featureKey);

  if (gate.isLoading) {
    return <GatedPageShimmer />;
  }

  if (!gate.allowed) {
    return (
      <PremiumShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <UpgradePrompt featureKey={featureKey} variant="page" />
        </div>
      </PremiumShell>
    );
  }

  return <>{children}</>;
}

export default GatedPage;
