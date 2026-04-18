// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import ContentCalendarPage from '@/app/dashboard/content/page';
import DepartmentsPage from '@/app/dashboard/departments/page';
import FinanceDashboardPage from '@/app/dashboard/finance/page';
import GovernancePage from '@/app/dashboard/governance/page';
import PortfolioPage from '@/app/dashboard/portfolio/page';
import { usePersona } from '@/contexts/PersonaContext';
import { getContentBundles, getContentDeliverables } from '@/services/content';
import { getDashboardSummary } from '@/services/dashboard';
import { getDepartmentHealth } from '@/services/departments';
import { getFinanceAssumptions, getInvoices, getRevenueTimeSeries } from '@/services/finance';
import { getPortfolioHealth, getApprovalChains, getAuditLog } from '@/services/governance';
import { getAudits, getRisks, computeComplianceScore } from '@/services/compliance';
import { useRouter } from 'next/navigation';

const push = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
}));

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: any) => (
    <a href={typeof href === 'string' ? href : href?.pathname ?? ''} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

vi.mock('@/components/layout/PremiumShell', () => ({
  PremiumShell: ({ children }: any) => <div>{children}</div>,
  default: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('@/components/ui/DashboardErrorBoundary', () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('@/components/ui/MetricCard', () => ({
  default: ({ label, value }: any) => (
    <div>
      {label}: {String(value)}
    </div>
  ),
}));

vi.mock('@/components/ui/StatusBadge', () => ({
  default: ({ status }: any) => <span>{status}</span>,
}));

vi.mock('@/components/dashboard/GatedPage', () => ({
  GatedPage: ({ children }: any) => <div>{children}</div>,
  default: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('@/contexts/PersonaContext', () => ({
  usePersona: vi.fn(),
}));

vi.mock('@/services/dashboard', () => ({
  getDashboardSummary: vi.fn(),
}));

vi.mock('@/services/content', () => ({
  getContentBundles: vi.fn(),
  getContentDeliverables: vi.fn(),
}));

vi.mock('@/services/departments', () => ({
  getDepartmentHealth: vi.fn(),
}));

vi.mock('@/services/finance', () => ({
  getFinanceAssumptions: vi.fn(),
  getInvoices: vi.fn(),
  getRevenueTimeSeries: vi.fn(),
}));

vi.mock('@/services/governance', () => ({
  getPortfolioHealth: vi.fn(),
  getApprovalChains: vi.fn(),
  getAuditLog: vi.fn(),
}));

vi.mock('@/services/compliance', () => ({
  getAudits: vi.fn(),
  getRisks: vi.fn(),
  computeComplianceScore: vi.fn(),
}));

describe('dashboard empty states', () => {
  beforeEach(() => {
    push.mockReset();
    vi.clearAllMocks();

    vi.mocked(useRouter).mockReturnValue({ push } as any);
    vi.mocked(usePersona).mockReturnValue({ persona: 'startup' } as any);

    vi.mocked(getDashboardSummary).mockResolvedValue({
      finance: {
        currency: 'USD',
        revenue: 0,
        cash_position: 0,
        monthly_burn: 0,
        runway_months: null,
      },
      collections: {
        content_queue: [],
      },
    } as any);

    vi.mocked(getInvoices).mockResolvedValue([] as any);
    vi.mocked(getFinanceAssumptions).mockResolvedValue([] as any);
    vi.mocked(getRevenueTimeSeries).mockResolvedValue([] as any);

    vi.mocked(getContentBundles).mockResolvedValue([] as any);
    vi.mocked(getContentDeliverables).mockResolvedValue([] as any);

    vi.mocked(getPortfolioHealth).mockResolvedValue(null as any);
    vi.mocked(getApprovalChains).mockResolvedValue([] as any);
    vi.mocked(getAuditLog).mockResolvedValue([] as any);

    vi.mocked(getAudits).mockResolvedValue([] as any);
    vi.mocked(getRisks).mockResolvedValue([] as any);
    vi.mocked(computeComplianceScore).mockReturnValue(0);

    vi.mocked(getDepartmentHealth).mockResolvedValue([] as any);
  });

  afterEach(() => {
    cleanup();
  });

  it('shows actionable finance empty states', async () => {
    render(<FinanceDashboardPage />);

    expect(await screen.findByText('No revenue data available yet.')).toBeTruthy();
    expect(screen.getByText('No invoices found.')).toBeTruthy();
    expect(screen.getByText('No active assumptions.')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Generate Invoice' }));
    expect(push).toHaveBeenCalledWith('/dashboard/command-center');
  });

  it('shows governance empty states with next actions', async () => {
    render(<GovernancePage />);

    expect(await screen.findByText('No data available')).toBeTruthy();
    expect(screen.getByText('No pending approval chains')).toBeTruthy();
    expect(screen.getByText('No audit log entries found')).toBeTruthy();
  });

  it('shows a page-level empty state when content has not been created yet', async () => {
    render(<ContentCalendarPage />);

    expect(await screen.findByText('Content Calendar')).toBeTruthy();
    expect(screen.getByText('No content in queue.')).toBeTruthy();

    expect(screen.getByRole('link', { name: 'Create Content' }).getAttribute('href')).toBe(
      '/dashboard/command-center',
    );
  });

  it('reuses the shared empty state for portfolio gaps', async () => {
    render(<PortfolioPage />);

    expect(await screen.findByText('No initiatives yet')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Go to Workspace' }).getAttribute('href')).toBe(
      '/dashboard/workspace',
    );
  });

  it('gives departments a clear zero-data next step', async () => {
    render(<DepartmentsPage />);

    expect(await screen.findByText('No departments configured yet')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Refresh department data' })).toBeTruthy();
  });
});
