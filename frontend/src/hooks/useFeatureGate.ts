// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React hook that combines persona context with feature gating config.
 *
 * Usage:
 * ```tsx
 * const { allowed, currentTier, requiredTier, isLoading } = useFeatureGate('workflows');
 * if (!allowed) return <UpgradePrompt featureKey="workflows" />;
 * ```
 */

import {
  isFeatureAllowed,
  getRequiredTier,
  FEATURE_ACCESS,
  type FeatureKey,
  type PersonaTier,
} from '@/config/featureGating';
import { useEffectiveTier } from '@/hooks/useEffectiveTier';

// ============================================================================
// Return type
// ============================================================================

export interface FeatureGateResult {
  /** True if the user's current tier can access this feature. */
  allowed: boolean;
  /** The user's current persona tier, or null while loading. */
  currentTier: PersonaTier | null;
  /** The minimum tier required to access this feature. */
  requiredTier: PersonaTier;
  /** True while the persona is still being fetched from the database. */
  isLoading: boolean;
  /** Human-readable feature name from FEATURE_ACCESS. */
  featureLabel: string;
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Evaluates whether the current user's persona tier has access to a feature.
 *
 * While the persona is loading (`isLoading === true`), `allowed` is always
 * false and `currentTier` is null — callers should render a loading state
 * rather than a hard denial.
 *
 * @param featureKey - The feature identifier to check (see FeatureKey).
 * @returns Gate result with access flag, tier info, and loading state.
 */
export function useFeatureGate(featureKey: FeatureKey): FeatureGateResult {
  const { tier, isLoading } = useEffectiveTier();

  const requiredTier = getRequiredTier(featureKey);
  const featureLabel = FEATURE_ACCESS[featureKey].label;

  if (isLoading) {
    return {
      allowed: false,
      currentTier: null,
      requiredTier,
      isLoading: true,
      featureLabel,
    };
  }

  const allowed = isFeatureAllowed(featureKey, tier);

  return {
    allowed,
    currentTier: tier,
    requiredTier,
    isLoading: false,
    featureLabel,
  };
}
