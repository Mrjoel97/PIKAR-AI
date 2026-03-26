// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

export interface QuickAction {
  label: string;
  href: string;
  icon: string;
}

export interface PersonaShellConfig {
  key: string;
  label: string;
  tagline: string;
  description: string;
  gradient: string;
  accentColor: string;
  bgColor: string;
  headerIcon: string;
  quickActions: QuickAction[];
  kpiLabels: string[];
}

export const PERSONA_SHELL_CONFIG: Record<
  'solopreneur' | 'startup' | 'sme' | 'enterprise',
  PersonaShellConfig
> = {
  solopreneur: {
    key: 'solopreneur',
    label: 'Solopreneur',
    tagline: 'Ship fast. Stay lean.',
    description:
      'Low-overhead execution focused on revenue and consistency.',
    gradient: 'from-blue-600 via-teal-500 to-cyan-400',
    accentColor: 'text-blue-600',
    bgColor: 'bg-gradient-to-br from-blue-50/40 to-teal-50/20',
    headerIcon: 'rocket',
    quickActions: [
      { label: 'Brain Dump', href: '/dashboard/braindump', icon: 'brain' },
      {
        label: 'Create Initiative',
        href: '/dashboard/initiatives/new',
        icon: 'plus-circle',
      },
      { label: 'Content', href: '/dashboard/content', icon: 'file-text' },
      {
        label: 'Sales Pipeline',
        href: '/dashboard/sales',
        icon: 'trending-up',
      },
    ],
    kpiLabels: ['Cash Collected', 'Weekly Pipeline', 'Content Consistency'],
  },

  startup: {
    key: 'startup',
    label: 'Startup',
    tagline: 'Experiment. Measure. Grow.',
    description:
      'Growth experiments, PMF learning, and team alignment.',
    gradient: 'from-indigo-600 via-violet-500 to-purple-400',
    accentColor: 'text-indigo-600',
    bgColor: 'bg-gradient-to-br from-indigo-50/40 to-violet-50/20',
    headerIcon: 'zap',
    quickActions: [
      {
        label: 'Workflow Templates',
        href: '/dashboard/workflows/templates',
        icon: 'layout-template',
      },
      {
        label: 'User Journeys',
        href: '/dashboard/journeys',
        icon: 'map',
      },
      {
        label: 'Create Initiative',
        href: '/dashboard/initiatives/new',
        icon: 'plus-circle',
      },
      {
        label: 'Sales Pipeline',
        href: '/dashboard/sales',
        icon: 'trending-up',
      },
    ],
    kpiLabels: [
      'MRR Growth',
      'Activation & Conversion',
      'Experiment Velocity',
    ],
  },

  sme: {
    key: 'sme',
    label: 'SME',
    tagline: 'Reliable operations. Clear accountability.',
    description:
      'Departmental coordination, reporting, and compliance.',
    gradient: 'from-emerald-600 via-green-500 to-lime-400',
    accentColor: 'text-emerald-600',
    bgColor: 'bg-gradient-to-br from-emerald-50/40 to-green-50/20',
    headerIcon: 'building2',
    quickActions: [
      { label: 'Departments', href: '/departments', icon: 'building' },
      { label: 'Reports', href: '/dashboard/reports', icon: 'bar-chart-3' },
      { label: 'Finance', href: '/dashboard/finance', icon: 'wallet' },
      {
        label: 'Compliance',
        href: '/dashboard/compliance',
        icon: 'shield-check',
      },
    ],
    kpiLabels: [
      'Department Performance',
      'Process Cycle Time',
      'Margin & Compliance',
    ],
  },

  enterprise: {
    key: 'enterprise',
    label: 'Enterprise',
    tagline: 'Governed execution. Strategic control.',
    description:
      'Strategic visibility, governance, and cross-functional risk management.',
    gradient: 'from-slate-700 via-slate-600 to-slate-500',
    accentColor: 'text-slate-700',
    bgColor: 'bg-gradient-to-br from-slate-50/60 to-gray-50/30',
    headerIcon: 'shield',
    quickActions: [
      {
        label: 'Compliance',
        href: '/dashboard/compliance',
        icon: 'shield-check',
      },
      { label: 'Reports', href: '/dashboard/reports', icon: 'bar-chart-3' },
      {
        label: 'Approvals',
        href: '/dashboard/approvals',
        icon: 'check-circle',
      },
      {
        label: 'Active Workflows',
        href: '/dashboard/workflows/active',
        icon: 'activity',
      },
    ],
    kpiLabels: [
      'Portfolio Health',
      'Risk & Control Coverage',
      'Reporting Quality',
    ],
  },
};
