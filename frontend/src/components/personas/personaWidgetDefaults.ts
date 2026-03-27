// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Per-persona default widget definitions.
 *
 * New users with zero pinned widgets see these curated defaults on their
 * dashboard, giving them immediate value before they start chatting.
 * Once a user pins any widget or dismisses a default, these disappear.
 */

import type { WidgetDefinition, WidgetType } from '@/types/widgets';

type PersonaKey = 'solopreneur' | 'startup' | 'sme' | 'enterprise';

function widget(type: WidgetType, title: string): WidgetDefinition {
  return { type, title, data: {}, dismissible: true };
}

/**
 * Maps each persona to an array of 4 default WidgetDefinitions.
 */
export const PERSONA_DEFAULT_WIDGETS: Record<PersonaKey, WidgetDefinition[]> = {
  solopreneur: [
    widget('revenue_chart', 'Revenue Overview'),
    widget('morning_briefing', 'Morning Briefing'),
    widget('kanban_board', 'Task Board'),
    widget('campaign_hub', 'Campaign Hub'),
  ],
  startup: [
    widget('revenue_chart', 'Revenue Overview'),
    widget('morning_briefing', 'Morning Briefing'),
    widget('initiative_dashboard', 'Initiative Dashboard'),
    widget('workflow_observability', 'Workflow Observability'),
  ],
  sme: [
    widget('department_activity', 'Department Activity'),
    widget('morning_briefing', 'Morning Briefing'),
    widget('revenue_chart', 'Revenue Overview'),
    widget('workflow_observability', 'Workflow Observability'),
  ],
  enterprise: [
    widget('department_activity', 'Department Activity'),
    widget('morning_briefing', 'Morning Briefing'),
    widget('revenue_chart', 'Revenue Overview'),
    widget('boardroom', 'Boardroom'),
  ],
};

/**
 * Returns the default widget set for the given persona key, or an empty
 * array if the persona is null or not recognised.
 */
export function getDefaultWidgetsForPersona(
  persona: string | null,
): WidgetDefinition[] {
  if (!persona) return [];
  return PERSONA_DEFAULT_WIDGETS[persona as PersonaKey] ?? [];
}
