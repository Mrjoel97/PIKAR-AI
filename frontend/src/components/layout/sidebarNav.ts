// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import {
  Bell,
  BookOpen,
  CreditCard,
  Database,
  FileText,
  Globe,
  LayoutDashboard,
  LifeBuoy,
  MessageSquare,
  PieChart,
  Settings,
  ShieldCheck,
  TrendingUp,
  Wallet,
  Zap
} from 'lucide-react';
import type { FeatureKey } from '@/config/featureGating';

export const MAIN_INTERFACE_ROUTE = '/dashboard/command-center';

/**
 * Shape of a single sidebar navigation item.
 *
 * `featureKey` is optional — only present for items that correspond to a
 * gated feature in FEATURE_ACCESS.  Items without a featureKey are always
 * visible and clickable regardless of the user's tier.
 */
export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  featureKey?: FeatureKey;
}

export const MAIN_INTERFACE_NAV_ITEMS: NavItem[] = [
  {
    label: 'Command Center',
    href: MAIN_INTERFACE_ROUTE,
    icon: LayoutDashboard,
    // Ungated — available to every tier.
  },
  {
    label: 'Approvals',
    href: '/dashboard/approvals',
    icon: Bell,
    featureKey: 'approvals',
  },
  {
    label: 'Finance',
    href: '/dashboard/finance',
    icon: Wallet,
    featureKey: 'finance-forecasting',
  },
  {
    label: 'Content',
    href: '/dashboard/content',
    icon: FileText,
    // Ungated — not in FEATURE_ACCESS.
  },
  {
    label: 'Sales Pipeline',
    href: '/dashboard/sales',
    icon: TrendingUp,
    featureKey: 'sales',
  },
  {
    label: 'Compliance',
    href: '/dashboard/compliance',
    icon: ShieldCheck,
    featureKey: 'compliance',
  },
  {
    label: 'My Workspace',
    href: '/dashboard/workspace',
    icon: Zap,
    // Ungated — not in FEATURE_ACCESS.
  },
  {
    label: 'Reports',
    href: '/dashboard/reports',
    icon: PieChart,
    featureKey: 'reports',
  },
  {
    label: 'Knowledge Vault',
    href: '/dashboard/vault',
    icon: Database,
    // Ungated — not in FEATURE_ACCESS.
  },
  {
    label: 'Join Community',
    href: '/dashboard/community',
    icon: Globe,
    // Ungated — not in FEATURE_ACCESS.
  },
  {
    label: 'Learning Hub',
    href: '/dashboard/learning',
    icon: BookOpen,
    // Ungated — not in FEATURE_ACCESS.
  },
  {
    label: 'Contact Support',
    href: '/dashboard/support',
    icon: LifeBuoy,
    // Ungated — not in FEATURE_ACCESS.
  },
  {
    label: 'Chat History',
    href: '/dashboard/history',
    icon: MessageSquare,
    // Ungated — not in FEATURE_ACCESS.
  },
  {
    label: 'Billing & Subscription',
    href: '/dashboard/billing',
    icon: CreditCard,
    // Ungated — always accessible so users can upgrade.
  },
  {
    label: 'Configuration',
    href: '/dashboard/configuration',
    icon: Settings,
    // Ungated — not in FEATURE_ACCESS.
  },
];
