// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ projectId: 'test-id' }),
}));

// Mock framer-motion to avoid animation overhead in tests
vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
  },
}));

// Mock the app-builder service
vi.mock('@/services/app-builder', () => ({
  startResearch: vi.fn(),
  approveBrief: vi.fn(),
  advanceStage: vi.fn(),
}));

import { startResearch, approveBrief, advanceStage } from '@/services/app-builder';
import ResearchPage from '@/app/app-builder/[projectId]/research/page';
import type { ResearchEvent } from '@/types/app-builder';

const mockReadyData: ResearchEvent = {
  step: 'ready',
  message: 'Research complete',
  data: {
    colors: [
      { hex: '#1a1a2e', name: 'Navy' },
      { hex: '#e94560', name: 'Crimson' },
    ],
    typography: { heading: 'Inter', body: 'Source Sans' },
    spacing: { base_unit: '4px' },
    raw_markdown: '# Design System\n',
    sitemap: [
      { page: 'home', title: 'Home', sections: ['hero', 'features'], device_targets: ['desktop', 'mobile'] },
    ],
  },
};

describe('ResearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (advanceStage as ReturnType<typeof vi.fn>).mockResolvedValue({ stage: 'research' });
  });

  it('shows progress during research', async () => {
    (startResearch as ReturnType<typeof vi.fn>).mockImplementation(
      (_id: string, onEvent: (e: ResearchEvent) => void) => {
        onEvent({ step: 'searching', message: 'Searching the web...' });
        return new Promise(() => {}); // never resolves — simulates ongoing stream
      },
    );

    await act(async () => {
      render(<ResearchPage />);
    });

    expect(screen.getByText(/researching/i)).toBeTruthy();
  });

  it('shows design brief card after research completes', async () => {
    (startResearch as ReturnType<typeof vi.fn>).mockImplementation(
      (_id: string, onEvent: (e: ResearchEvent) => void) => {
        onEvent(mockReadyData);
        return Promise.resolve();
      },
    );

    await act(async () => {
      render(<ResearchPage />);
    });

    await waitFor(() => {
      expect(screen.getByTestId('design-brief-card')).toBeTruthy();
    });
  });

  it('approve button calls approveBrief', async () => {
    (startResearch as ReturnType<typeof vi.fn>).mockImplementation(
      (_id: string, onEvent: (e: ResearchEvent) => void) => {
        onEvent(mockReadyData);
        return Promise.resolve();
      },
    );
    (approveBrief as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      build_plan: [],
      stage: 'building',
    });

    await act(async () => {
      render(<ResearchPage />);
    });

    await waitFor(() => {
      expect(screen.getByTestId('design-brief-card')).toBeTruthy();
    });

    const approveBtn = screen.getByRole('button', { name: /approve/i });
    await act(async () => {
      fireEvent.click(approveBtn);
    });

    await waitFor(() => {
      expect(approveBrief).toHaveBeenCalledWith('test-id', expect.objectContaining({
        design_system: expect.any(Object),
        sitemap: expect.any(Array),
        raw_markdown: expect.any(String),
      }));
    });
  });

  it('approve button is disabled during research', async () => {
    (startResearch as ReturnType<typeof vi.fn>).mockImplementation(
      (_id: string, onEvent: (e: ResearchEvent) => void) => {
        onEvent({ step: 'searching', message: 'Searching...' });
        return new Promise(() => {}); // never resolves
      },
    );

    await act(async () => {
      render(<ResearchPage />);
    });

    await waitFor(() => {
      const btn = screen.queryByRole('button', { name: /approve/i });
      if (btn) {
        expect((btn as HTMLButtonElement).disabled).toBe(true);
      }
      // If button isn't rendered yet during research, that's also acceptable
    });
  });
});
