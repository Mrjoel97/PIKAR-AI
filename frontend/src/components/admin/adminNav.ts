// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import {
  Activity,
  BarChart3,
  BookOpen,
  CheckCircle,
  CreditCard,
  FileText,
  LayoutDashboard,
  Plug,
  Settings,
  Shield,
  Users,
} from 'lucide-react';

/**
 * Navigation items for the admin panel sidebar.
 * Each item defines a label, href, and Lucide icon for rendering.
 */
export interface AdminNavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
  {
    label: 'Overview',
    href: '/admin',
    icon: LayoutDashboard,
  },
  {
    label: 'Users',
    href: '/admin/users',
    icon: Users,
  },
  {
    label: 'Monitor',
    href: '/admin/monitoring',
    icon: Activity,
  },
  {
    label: 'Analytics',
    href: '/admin/analytics',
    icon: BarChart3,
  },
  {
    label: 'Approvals',
    href: '/admin/approvals',
    icon: CheckCircle,
  },
  {
    label: 'Config',
    href: '/admin/config',
    icon: Settings,
  },
  {
    label: 'Knowledge',
    href: '/admin/knowledge',
    icon: BookOpen,
  },
  {
    label: 'Billing',
    href: '/admin/billing',
    icon: CreditCard,
  },
  {
    label: 'Integrations',
    href: '/admin/integrations',
    icon: Plug,
  },
  {
    label: 'Settings',
    href: '/admin-settings',
    icon: Shield,
  },
  {
    label: 'Audit Log',
    href: '/admin/audit-log',
    icon: FileText,
  },
];
