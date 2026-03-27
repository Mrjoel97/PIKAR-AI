// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ projectId: 'proj-123' }),
}));

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
    span: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement> & { children?: React.ReactNode }) => (
      <span {...props}>{children}</span>
    ),
    p: ({ children, ...props }: React.HTMLAttributes<HTMLParagraphElement> & { children?: React.ReactNode }) => (
      <p {...props}>{children}</p>
    ),
  },
}));

vi.mock('@/services/app-builder', () => ({
  generateScreen: vi.fn(),
  generateDeviceVariant: vi.fn(),
  getScreenVariants: vi.fn(),
  selectVariant: vi.fn(),
  getProject: vi.fn(),
}));

import { generateScreen, getProject } from '@/services/app-builder';
import type { AppProject, ScreenVariant, GenerationEvent } from '@/types/app-builder';
import BuildingPage from '@/app/app-builder/[projectId]/building/page';

const mockVariant = (i: number): ScreenVariant => ({
  id: `var-${i}`,
  screen_id: 'screen-1',
  variant_index: i,
  screenshot_url: `https://example.com/screenshot-${i}.png`,
  html_url: `https://example.com/screen-${i}.html`,
  is_selected: i === 0,
  prompt_used: 'test prompt',
  created_at: '2026-03-22T00:00:00Z',
});

const mockProject: AppProject = {
  id: 'proj-123',
  user_id: 'user-1',
  title: 'My App',
  status: 'generating',
  stage: 'building',
  creative_brief: { what: 'Landing page' },
  build_plan: [
    {
      phase: 1,
      label: 'Core Screens',
      screens: [{ name: 'Home', page: 'home', device: 'DESKTOP' }],
      dependencies: [],
    },
  ],
  created_at: '2026-03-22T00:00:00Z',
  updated_at: '2026-03-22T00:00:00Z',
};

describe('BuildingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getProject as ReturnType<typeof vi.fn>).mockResolvedValue(mockProject);
  });

  it('shows GenerationProgress component during generation (before ready event)', async () => {
    (generateScreen as ReturnType<typeof vi.fn>).mockImplementation(
      (_id: string, _name: string, _slug: string, onEvent: (e: GenerationEvent) => void) => {
        onEvent({ step: 'generating', message: 'Generating variants...' });
        return new Promise(() => {}); // never resolves — simulates ongoing generation
      },
    );

    await act(async () => {
      render(<BuildingPage />);
    });

    // Trigger generation by clicking a screen button
    const screenButton = await screen.findByRole('button', { name: /home/i });
    await act(async () => {
      screenButton.click();
    });

    // During generation, GenerationProgress should be visible
    await waitFor(() => {
      expect(screen.getByTestId('generation-progress')).toBeTruthy();
    });
  });

  it('renders VariantComparisonGrid after generation events arrive', async () => {
    const variants = [mockVariant(0), mockVariant(1)];
    (generateScreen as ReturnType<typeof vi.fn>).mockImplementation(
      (_id: string, _name: string, _slug: string, onEvent: (e: GenerationEvent) => void) => {
        onEvent({ step: 'variant_generated', variant_index: 0, variant_id: 'var-0', screenshot_url: variants[0].screenshot_url!, html_url: variants[0].html_url!, screen_id: 'screen-1' });
        onEvent({ step: 'variant_generated', variant_index: 1, variant_id: 'var-1', screenshot_url: variants[1].screenshot_url!, html_url: variants[1].html_url!, screen_id: 'screen-1' });
        onEvent({ step: 'ready', screen_id: 'screen-1', variants });
        return Promise.resolve();
      },
    );

    await act(async () => {
      render(<BuildingPage />);
    });

    const screenButton = await screen.findByRole('button', { name: /home/i });
    await act(async () => {
      screenButton.click();
    });

    await waitFor(() => {
      const images = screen.getAllByRole('img');
      expect(images.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('renders DevicePreviewFrame with selected variant html_url after generation', async () => {
    const variants = [mockVariant(0), mockVariant(1)];
    (generateScreen as ReturnType<typeof vi.fn>).mockImplementation(
      (_id: string, _name: string, _slug: string, onEvent: (e: GenerationEvent) => void) => {
        onEvent({ step: 'ready', screen_id: 'screen-1', variants });
        return Promise.resolve();
      },
    );

    await act(async () => {
      render(<BuildingPage />);
    });

    const screenButton = await screen.findByRole('button', { name: /home/i });
    await act(async () => {
      screenButton.click();
    });

    await waitFor(() => {
      const iframe = screen.getByTitle(/preview/i) as HTMLIFrameElement;
      expect(iframe.src).toContain('screen-0');
    });
  });
});
