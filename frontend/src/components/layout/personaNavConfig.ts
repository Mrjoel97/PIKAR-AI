// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { MAIN_INTERFACE_NAV_ITEMS } from './sidebarNav';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null;

/**
 * Priority nav item hrefs per persona.
 * Items listed here appear first in the sidebar (in this order);
 * remaining items follow in their original MAIN_INTERFACE_NAV_ITEMS order.
 *
 * Command Center (/dashboard/command-center) is always first for every persona.
 */
export const PERSONA_NAV_PRIORITIES: Record<
  Exclude<Persona, null>,
  readonly string[]
> = {
  solopreneur: [
    '/dashboard/command-center',
    '/dashboard/content',
    '/dashboard/sales',
    '/dashboard/finance',
    '/dashboard/workspace',
    '/dashboard/vault',
  ],
  startup: [
    '/dashboard/command-center',
    '/dashboard/sales',
    '/dashboard/content',
    '/dashboard/finance',
    '/dashboard/reports',
    '/dashboard/workspace',
  ],
  sme: [
    '/dashboard/command-center',
    '/dashboard/finance',
    '/dashboard/reports',
    '/dashboard/compliance',
    '/dashboard/approvals',
    '/dashboard/workspace',
  ],
  enterprise: [
    '/dashboard/command-center',
    '/dashboard/compliance',
    '/dashboard/reports',
    '/dashboard/approvals',
    '/dashboard/finance',
    '/dashboard/workspace',
  ],
};

/**
 * Return a reordered copy of MAIN_INTERFACE_NAV_ITEMS based on persona.
 *
 * - Items whose `href` appears in the persona's priority list come first, in
 *   priority order.
 * - Remaining items follow in their original MAIN_INTERFACE_NAV_ITEMS order.
 * - If persona is null (not yet loaded), the default order is returned unchanged.
 *
 * The function is pure and creates a new array every call.
 */
export function getPersonaNavItems(
  persona: Persona,
): typeof MAIN_INTERFACE_NAV_ITEMS {
  if (!persona) {
    return [...MAIN_INTERFACE_NAV_ITEMS];
  }

  const priorities = PERSONA_NAV_PRIORITIES[persona];
  if (!priorities) {
    return [...MAIN_INTERFACE_NAV_ITEMS];
  }

  const prioritySet = new Set(priorities);

  // Gather prioritized items in priority order
  const prioritized: typeof MAIN_INTERFACE_NAV_ITEMS = [];
  for (const href of priorities) {
    const item = MAIN_INTERFACE_NAV_ITEMS.find((n) => n.href === href);
    if (item) {
      prioritized.push(item);
    }
  }

  // Remaining items keep their original order
  const rest = MAIN_INTERFACE_NAV_ITEMS.filter(
    (item) => !prioritySet.has(item.href),
  );

  return [...prioritized, ...rest];
}
