// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Per-persona, per-widget-type empty state configuration.
 *
 * Each entry provides a headline, description, CTA label, CTA href,
 * and lucide icon name so that empty widgets show actionable,
 * persona-specific guidance rather than generic "No data" messages.
 */

export interface EmptyStateConfig {
  /** Lucide icon name (kebab-case) */
  icon: string;
  /** Short headline displayed prominently */
  headline: string;
  /** Longer description referencing persona objectives/KPIs */
  description: string;
  /** CTA button label */
  ctaLabel: string;
  /** CTA link destination */
  ctaHref: string;
}

type PersonaKey = 'solopreneur' | 'startup' | 'sme' | 'enterprise';
type WidgetType = string;

export const PERSONA_EMPTY_STATES: Record<
  PersonaKey,
  Partial<Record<WidgetType, EmptyStateConfig>>
> = {
  solopreneur: {
    revenue_chart: {
      icon: 'dollar-sign',
      headline: 'Track your cash flow',
      description:
        'Connect Stripe to track your cash flow and see revenue trends at a glance.',
      ctaLabel: 'Connect Stripe',
      ctaHref: '/settings/integrations',
    },
    morning_briefing: {
      icon: 'sun',
      headline: 'Your daily command center',
      description:
        'Once your agents start working, your morning briefing will summarize pending actions and team status.',
      ctaLabel: 'Chat with your agent',
      ctaHref: '/solopreneur',
    },
    kanban_board: {
      icon: 'layout-grid',
      headline: 'Organize your pipeline',
      description:
        'Ask your agent to create a task board to track deals, content, and projects in one view.',
      ctaLabel: 'Create a board',
      ctaHref: '/solopreneur',
    },
    campaign_hub: {
      icon: 'megaphone',
      headline: 'Launch your first campaign',
      description:
        'Plan and track marketing campaigns — from content drafts to published posts — all in one hub.',
      ctaLabel: 'Start a campaign',
      ctaHref: '/dashboard/content',
    },
  },

  startup: {
    revenue_chart: {
      icon: 'trending-up',
      headline: 'Monitor your MRR',
      description:
        'Connect Stripe to track MRR growth, activation rates, and revenue experiments.',
      ctaLabel: 'Connect Stripe',
      ctaHref: '/settings/integrations',
    },
    morning_briefing: {
      icon: 'sun',
      headline: 'Your daily growth pulse',
      description:
        'Your briefing will surface experiment results, pending approvals, and team blockers each morning.',
      ctaLabel: 'Chat with your agent',
      ctaHref: '/startup',
    },
    initiative_dashboard: {
      icon: 'rocket',
      headline: 'Create your first growth experiment',
      description:
        'Launch initiatives to test hypotheses, track progress across phases, and measure what moves the needle.',
      ctaLabel: 'Create initiative',
      ctaHref: '/dashboard/initiatives/new',
    },
    workflow_observability: {
      icon: 'activity',
      headline: 'See your automation health',
      description:
        'Once workflows are running, monitor success rates, failure patterns, and execution times here.',
      ctaLabel: 'Browse templates',
      ctaHref: '/dashboard/workflows/templates',
    },
  },

  sme: {
    revenue_chart: {
      icon: 'bar-chart-3',
      headline: 'Revenue at a glance',
      description:
        'Connect Stripe to monitor revenue health, margins, and period comparisons across your departments.',
      ctaLabel: 'Connect Stripe',
      ctaHref: '/settings/integrations',
    },
    morning_briefing: {
      icon: 'sun',
      headline: 'Your operational briefing',
      description:
        'A daily summary of department performance, pending actions, and system status will appear here.',
      ctaLabel: 'Chat with your agent',
      ctaHref: '/sme',
    },
    department_activity: {
      icon: 'building-2',
      headline: 'Set up departments',
      description:
        'Configure your departments to see real-time activity feeds, decision logs, and workflow triggers.',
      ctaLabel: 'Configure departments',
      ctaHref: '/departments',
    },
    workflow_observability: {
      icon: 'activity',
      headline: 'Monitor process health',
      description:
        'Track workflow execution across departments — success rates, cycle times, and failing steps.',
      ctaLabel: 'Browse templates',
      ctaHref: '/dashboard/workflows/templates',
    },
  },

  enterprise: {
    revenue_chart: {
      icon: 'dollar-sign',
      headline: 'Portfolio revenue view',
      description:
        'Connect Stripe to see consolidated revenue, plan distribution, and cross-portfolio financial health.',
      ctaLabel: 'Connect Stripe',
      ctaHref: '/settings/integrations',
    },
    morning_briefing: {
      icon: 'sun',
      headline: 'Executive daily digest',
      description:
        'Your briefing will cover governance items, approval queues, risk flags, and reporting quality each morning.',
      ctaLabel: 'Chat with your agent',
      ctaHref: '/enterprise',
    },
    department_activity: {
      icon: 'building-2',
      headline: 'Department oversight',
      description:
        'Activate departments to see activity feeds, decision audit trails, and operational pulse across the organization.',
      ctaLabel: 'Configure departments',
      ctaHref: '/departments',
    },
    boardroom: {
      icon: 'users',
      headline: 'Convene the boardroom',
      description:
        'Ask your agent to run a strategic debate — the AI boardroom simulates CMO, CFO, and CEO perspectives on your proposals.',
      ctaLabel: 'Start a debate',
      ctaHref: '/enterprise',
    },
  },
};

/**
 * Look up the empty state config for a given persona + widget type.
 * Returns null when no config exists (caller should render a generic fallback).
 */
export function getPersonaEmptyState(
  persona: string | null,
  widgetType: string,
): EmptyStateConfig | null {
  if (!persona) return null;
  const personaConfig =
    PERSONA_EMPTY_STATES[persona as keyof typeof PERSONA_EMPTY_STATES];
  if (!personaConfig) return null;
  return personaConfig[widgetType] ?? null;
}
