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
    href: '/',
    icon: LayoutDashboard,
  },
  {
    label: 'Users',
    href: '/users',
    icon: Users,
  },
  {
    label: 'Monitor',
    href: '/monitoring',
    icon: Activity,
  },
  {
    label: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
  },
  {
    label: 'Approvals',
    href: '/approvals',
    icon: CheckCircle,
  },
  {
    label: 'Config',
    href: '/config',
    icon: Settings,
  },
  {
    label: 'Knowledge',
    href: '/knowledge',
    icon: BookOpen,
  },
  {
    label: 'Billing',
    href: '/billing',
    icon: CreditCard,
  },
  {
    label: 'Integrations',
    href: '/integrations',
    icon: Plug,
  },
  {
    label: 'Settings',
    href: '/admin-settings',
    icon: Shield,
  },
  {
    label: 'Audit Log',
    href: '/audit-log',
    icon: FileText,
  },
];
