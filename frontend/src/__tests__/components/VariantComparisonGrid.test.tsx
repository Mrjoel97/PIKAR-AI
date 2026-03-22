// @vitest-environment jsdom
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ScreenVariant } from '@/types/app-builder';

vi.mock('@/services/app-builder', () => ({
  selectVariant: vi.fn(),
  generateScreen: vi.fn(),
  generateDeviceVariant: vi.fn(),
  getScreenVariants: vi.fn(),
  getProject: vi.fn(),
}));

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
  },
}));

import VariantComparisonGrid from '@/components/app-builder/VariantComparisonGrid';

const makeVariant = (i: number, selected = false): ScreenVariant => ({
  id: `var-${i}`,
  screen_id: 'screen-1',
  variant_index: i,
  screenshot_url: `https://example.com/screenshot-${i}.png`,
  html_url: `https://example.com/screen-${i}.html`,
  is_selected: selected,
  prompt_used: 'test prompt',
  created_at: '2026-03-22T00:00:00Z',
});

describe('VariantComparisonGrid', () => {
  const onSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders N variant thumbnail images in a grid', () => {
    const variants = [makeVariant(0), makeVariant(1), makeVariant(2)];
    render(
      <VariantComparisonGrid variants={variants} selectedId={null} onSelect={onSelect} />,
    );

    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(3);
    images.forEach((img, i) => {
      expect((img as HTMLImageElement).src).toContain(`screenshot-${i}`);
    });
  });

  it('clicking a thumbnail calls onSelect with the variant id', () => {
    const variants = [makeVariant(0), makeVariant(1)];
    render(
      <VariantComparisonGrid variants={variants} selectedId={null} onSelect={onSelect} />,
    );

    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[1]);
    expect(onSelect).toHaveBeenCalledWith('var-1');
  });

  it('selected variant has indigo ring border class', () => {
    const variants = [makeVariant(0), makeVariant(1)];
    render(
      <VariantComparisonGrid variants={variants} selectedId="var-0" onSelect={onSelect} />,
    );

    const buttons = screen.getAllByRole('button');
    expect(buttons[0].className).toContain('ring');
    expect(buttons[0].className).toContain('indigo');
  });
});
