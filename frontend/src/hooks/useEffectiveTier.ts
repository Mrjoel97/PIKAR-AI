// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Canonical resolution of a user's effective tier for feature
 * gating. Replaces the divergent paths where PremiumShell read
 * `subscription.tier` but `useFeatureGate` (and Sidebar) read `persona` —
 * which could disagree for a startup-persona user on the free Stripe tier.
 *
 * Resolution order:
 *   1. Subscription tier (canonical, billing-driven). 'free' is aliased to
 *      'solopreneur' so unpaid users get solopreneur access.
 *   2. Persona — used only when SubscriptionProvider is not mounted (e.g.,
 *      surfaces outside /dashboard/* that still want to render the shell).
 *   3. Fallback: 'solopreneur' (lowest tier).
 */

import { useSubscription } from '@/contexts/SubscriptionContext';
import { usePersona } from '@/contexts/PersonaContext';
import type { PersonaTier } from '@/config/featureGating';

export interface EffectiveTierResult {
  /** The tier to use for feature gating. */
  tier: PersonaTier;
  /** True while either provider is still bootstrapping. */
  isLoading: boolean;
}

export function useEffectiveTier(): EffectiveTierResult {
  // Always call both hooks — try/catch only swallows the "outside provider"
  // throw, the hook itself is invoked on every render so the rules of hooks
  // are preserved.
  let subTier: PersonaTier | null = null;
  let subReady = true;
  try {
    const sub = useSubscription();
    const raw = sub.tier;
    subTier = (raw === 'free' ? 'solopreneur' : raw) as PersonaTier;
    subReady = sub.ready;
  } catch {
    // SubscriptionProvider not mounted — fall through to persona.
  }

  let personaTier: PersonaTier | null = null;
  let personaLoading = false;
  try {
    const { persona, isLoading } = usePersona();
    personaTier = persona as PersonaTier | null;
    personaLoading = isLoading;
  } catch {
    // PersonaProvider not mounted either.
  }

  // Subscription is canonical when available — including when the user is on
  // 'free' (mapped to 'solopreneur'). Persona is only the fallback path.
  if (subTier !== null) {
    return { tier: subTier, isLoading: !subReady };
  }

  return {
    tier: personaTier ?? 'solopreneur',
    isLoading: personaLoading,
  };
}
