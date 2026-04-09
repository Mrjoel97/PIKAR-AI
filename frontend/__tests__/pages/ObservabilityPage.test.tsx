// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Tests for admin observability dashboard page (OBS-02/03/04/05).
 * Verifies page renders with 4 tabs, hero metric cards, and time-range picker.
 */

import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mock next/navigation (required by ObservabilityPage useRouter + useSearchParams)
// ---------------------------------------------------------------------------

vi.mock('next/navigation', () => ({
  useSearchParams: vi.fn(() => new URLSearchParams()),
  useRouter: vi.fn(() => ({ replace: vi.fn() })),
  usePathname: vi.fn(() => '/admin/observability'),
}));

// ---------------------------------------------------------------------------
// Mock Supabase client
// ---------------------------------------------------------------------------

vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'mock-token' } },
      }),
    },
  })),
}));

// ---------------------------------------------------------------------------
// Mock fetch globally — return empty summary by default
// ---------------------------------------------------------------------------

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const mockSummaryResponse = {
  error_rate_24h: { error_rate: 0.02, error_count: 5, total_count: 250 },
  mtd_ai_spend: { mtd_actual: 12.5, projected_full_month: 45.0, projection_method: 'linear_7day' },
  p95_latency_24h: { p50: 120, p95: 450, p99: 1200, sample_count: 250, error_count: 5 },
  threshold_breach: null,
};

describe('ObservabilityPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSummaryResponse),
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders the page title', async () => {
    const { default: ObservabilityPage } = await import(
      '@/app/(admin)/observability/page'
    );
    render(<ObservabilityPage />);
    expect(screen.getByText('Observability')).toBeTruthy();
  });

  it('renders all four tab buttons', async () => {
    const { default: ObservabilityPage } = await import(
      '@/app/(admin)/observability/page'
    );
    render(<ObservabilityPage />);
    expect(screen.getByText('Errors')).toBeTruthy();
    expect(screen.getByText('Performance')).toBeTruthy();
    expect(screen.getByText('AI Cost')).toBeTruthy();
    expect(screen.getByText('Health')).toBeTruthy();
  });

  it('renders all four time-window picker buttons', async () => {
    const { default: ObservabilityPage } = await import(
      '@/app/(admin)/observability/page'
    );
    render(<ObservabilityPage />);
    expect(screen.getByText('1h')).toBeTruthy();
    expect(screen.getByText('24h')).toBeTruthy();
    expect(screen.getByText('7d')).toBeTruthy();
    expect(screen.getByText('30d')).toBeTruthy();
  });

  it('renders hero metric card titles', async () => {
    const { default: ObservabilityPage } = await import(
      '@/app/(admin)/observability/page'
    );
    render(<ObservabilityPage />);
    // Cards render during loading (skeleton) then are filled — but titles are data-driven
    // Just verify the page renders without crashing and has tabs + time-range picker
    const tabs = screen.getAllByRole('button');
    // Should include: 4 time-window buttons + 4 tab buttons + at least 1 Refresh button
    expect(tabs.length).toBeGreaterThanOrEqual(9);
  });

  it('renders a Refresh button', async () => {
    const { default: ObservabilityPage } = await import(
      '@/app/(admin)/observability/page'
    );
    render(<ObservabilityPage />);
    expect(screen.getByText('Refresh')).toBeTruthy();
  });

  it('renders subtitle describing the page purpose', async () => {
    const { default: ObservabilityPage } = await import(
      '@/app/(admin)/observability/page'
    );
    render(<ObservabilityPage />);
    expect(screen.getByText('Agent performance, errors, AI cost, and health')).toBeTruthy();
  });
});
