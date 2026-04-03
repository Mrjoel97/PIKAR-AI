// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Centralized feature gating configuration.
 *
 * This is the SINGLE SOURCE OF TRUTH for all feature access decisions across
 * the Pikar AI application. Sidebar navigation, page guards, and backend
 * middleware all derive their gating rules from this file.
 *
 * Access matrix (matches billing page FEATURE_ROWS):
 *
 * | Feature              | Solopreneur | Startup | SME | Enterprise |
 * |----------------------|-------------|---------|-----|------------|
 * | Workflow Engine      |             |    ✓    |  ✓  |     ✓      |
 * | Sales Pipeline & CRM |             |    ✓    |  ✓  |     ✓      |
 * | Reports              |             |    ✓    |  ✓  |     ✓      |
 * | Approvals            |             |    ✓    |  ✓  |     ✓      |
 * | Compliance Suite     |             |         |  ✓  |     ✓      |
 * | Financial Forecasting|             |         |  ✓  |     ✓      |
 * | Custom Workflows     |             |         |     |     ✓      |
 * | SSO & Governance     |             |         |     |     ✓      |
 */

// ============================================================================
// Types
// ============================================================================

/**
 * Persona tier — mirrors PersonaType from services/onboarding.ts.
 * Declared here so this config file is self-contained and importable
 * from any context (including server-side middleware).
 */
export type PersonaTier = 'solopreneur' | 'startup' | 'sme' | 'enterprise';

/**
 * Ordered tier hierarchy — ascending access level.
 * Index 0 = lowest tier, index 3 = highest tier.
 * Used to determine whether a user's tier meets the minimum requirement.
 */
export const TIER_ORDER: readonly PersonaTier[] = [
  'solopreneur',
  'startup',
  'sme',
  'enterprise',
] as const;

/**
 * All gated feature identifiers. Keys are route-path-based to make
 * sidebar and page integration straightforward.
 */
export type FeatureKey =
  | 'workflows'
  | 'sales'
  | 'compliance'
  | 'finance-forecasting'
  | 'custom-workflows'
  | 'governance'
  | 'reports'
  | 'approvals';

// ============================================================================
// Feature Access Record
// ============================================================================

/**
 * Shape of each entry in FEATURE_ACCESS.
 */
export interface FeatureConfig {
  /** User-facing feature name shown in upgrade prompts. */
  label: string;
  /** One-line description shown in the upgrade prompt component. */
  description: string;
  /** Lowest persona tier that can access this feature. */
  minTier: PersonaTier;
  /**
   * Associated dashboard route (matches sidebar href).
   * Only present for features that have a dedicated page.
   */
  route?: string;
}

/**
 * Complete tier-to-feature access mapping.
 *
 * IMPORTANT: Keep this in sync with FEATURE_ROWS in
 * `frontend/src/app/dashboard/billing/page.tsx`.
 * A follow-up plan will have the billing page import from here directly.
 */
export const FEATURE_ACCESS: Record<FeatureKey, FeatureConfig> = {
  workflows: {
    label: 'Workflow Engine',
    description: 'Automate multi-step business processes with the visual workflow builder.',
    minTier: 'startup',
    route: '/dashboard/workflows',
  },
  sales: {
    label: 'Sales Pipeline & CRM',
    description: 'Track leads, manage deals, and automate your entire sales funnel.',
    minTier: 'startup',
    route: '/dashboard/sales',
  },
  reports: {
    label: 'Reports',
    description: 'Access detailed business performance reports and AI-generated insights.',
    minTier: 'startup',
    route: '/dashboard/reports',
  },
  approvals: {
    label: 'Approvals',
    description: 'Manage AI-generated action approvals and review agent recommendations.',
    minTier: 'startup',
    route: '/dashboard/approvals',
  },
  compliance: {
    label: 'Compliance Suite',
    description: 'Automate regulatory compliance tracking and document management.',
    minTier: 'sme',
    route: '/dashboard/compliance',
  },
  'finance-forecasting': {
    label: 'Financial Forecasting',
    description: 'AI-powered financial projections, scenario modelling, and cash flow analysis.',
    minTier: 'sme',
    route: '/dashboard/finance',
  },
  'custom-workflows': {
    label: 'Custom Workflows',
    description: 'Build fully custom automation pipelines tailored to your enterprise processes.',
    minTier: 'enterprise',
    route: '/dashboard/workflows/custom',
  },
  governance: {
    label: 'SSO & Governance',
    description: 'Enterprise single sign-on, role-based access control, and audit trails.',
    minTier: 'enterprise',
    route: '/dashboard/governance',
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Returns true if the user's persona tier has access to the given feature.
 *
 * @param featureKey - The feature to check access for.
 * @param userTier   - The user's current persona tier.
 *
 * @example
 * isFeatureAllowed('workflows', 'solopreneur') // false
 * isFeatureAllowed('workflows', 'startup')     // true
 * isFeatureAllowed('compliance', 'startup')    // false
 * isFeatureAllowed('compliance', 'sme')        // true
 */
export function isFeatureAllowed(
  featureKey: FeatureKey,
  userTier: PersonaTier,
): boolean {
  const config = FEATURE_ACCESS[featureKey];
  const userIndex = TIER_ORDER.indexOf(userTier);
  const minIndex = TIER_ORDER.indexOf(config.minTier);
  return userIndex >= minIndex;
}

/**
 * Returns the minimum persona tier required to access a feature.
 *
 * @param featureKey - The feature to look up.
 */
export function getRequiredTier(featureKey: FeatureKey): PersonaTier {
  return FEATURE_ACCESS[featureKey].minTier;
}

/**
 * Given a dashboard route path, returns the corresponding FeatureKey,
 * or null if the route is not gated.
 *
 * Matches on exact route equality and also on prefix (so
 * `/dashboard/workflows/custom` matches `custom-workflows` before `workflows`).
 * The lookup is ordered by specificity — more-specific routes win.
 *
 * @param route - The pathname to look up (e.g. `/dashboard/sales`).
 */
export function getFeatureKeyForRoute(route: string): FeatureKey | null {
  // Build sorted entries: more-specific routes (longer strings) first.
  const entries = (Object.entries(FEATURE_ACCESS) as [FeatureKey, FeatureConfig][])
    .filter(([, config]) => config.route !== undefined)
    .sort(([, a], [, b]) => (b.route?.length ?? 0) - (a.route?.length ?? 0));

  for (const [key, config] of entries) {
    if (config.route && (route === config.route || route.startsWith(config.route + '/'))) {
      return key;
    }
  }

  return null;
}

/**
 * Returns a Map of route → FeatureKey for all gated features that have
 * an associated route. Used by middleware for O(1) route lookups.
 */
export function getGatedRoutes(): Map<string, FeatureKey> {
  const map = new Map<string, FeatureKey>();
  for (const [key, config] of Object.entries(FEATURE_ACCESS) as [FeatureKey, FeatureConfig][]) {
    if (config.route) {
      map.set(config.route, key);
    }
  }
  return map;
}
