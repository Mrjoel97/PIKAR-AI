import {
  BookOpen,
  CreditCard,
  Database,
  Globe,
  LayoutDashboard,
  LifeBuoy,
  MessageSquare,
  PieChart,
  Settings,
  Zap
} from 'lucide-react';

export const MAIN_INTERFACE_ROUTE = '/dashboard/command-center';

export const MAIN_INTERFACE_NAV_ITEMS = [
  {
    label: 'Command Center',
    href: MAIN_INTERFACE_ROUTE,
    icon: LayoutDashboard,
  },
  {
    label: 'My Workspace',
    href: '/dashboard/workspace',
    icon: Zap,
  },
  {
    label: 'Reports',
    href: '/dashboard/reports',
    icon: PieChart,
  },
  {
    label: 'Knowledge Vault',
    href: '/dashboard/vault',
    icon: Database,
  },
  {
    label: 'Join Community',
    href: '/dashboard/community',
    icon: Globe,
  },
  {
    label: 'Learning Hub',
    href: '/dashboard/learning',
    icon: BookOpen,
  },
  {
    label: 'Contact Support',
    href: '/dashboard/support',
    icon: LifeBuoy,
  },
  {
    label: 'Chat History',
    href: '/dashboard/history',
    icon: MessageSquare,
  },
  {
    label: 'Billing & Subscription',
    href: '/dashboard/billing',
    icon: CreditCard,
  },
  {
    label: 'Configuration',
    href: '/dashboard/configuration',
    icon: Settings,
  },
];
