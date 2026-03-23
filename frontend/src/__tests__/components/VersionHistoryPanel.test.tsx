// @vitest-environment jsdom
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import VersionHistoryPanel from '@/components/app-builder/VersionHistoryPanel';
import type { ScreenVariant } from '@/types/app-builder';

const makeVariant = (i: number, isSelected = false): ScreenVariant => ({
  id: `var-${i}`,
  screen_id: 'screen-1',
  variant_index: i,
  screenshot_url: `https://example.com/shot-${i}.png`,
  html_url: `https://example.com/screen-${i}.html`,
  is_selected: isSelected,
  prompt_used: null,
  iteration: i,
  created_at: '2026-03-22T00:00:00Z',
});

describe('VersionHistoryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a list of variant thumbnails with iteration numbers', () => {
    const variants = [makeVariant(2, true), makeVariant(1), makeVariant(0)];
    render(<VersionHistoryPanel variants={variants} onRollback={vi.fn()} />);
    // Should show iteration numbers
    expect(screen.getByText(/iteration 2/i)).toBeTruthy();
    expect(screen.getByText(/iteration 1/i)).toBeTruthy();
    expect(screen.getByText(/iteration 0/i)).toBeTruthy();
  });

  it('shows Rollback button on non-selected variants', () => {
    const variants = [makeVariant(2, true), makeVariant(1), makeVariant(0)];
    render(<VersionHistoryPanel variants={variants} onRollback={vi.fn()} />);
    const rollbackButtons = screen.getAllByRole('button', { name: /rollback/i });
    // Only non-selected variants (2 of them) should have rollback buttons
    expect(rollbackButtons.length).toBe(2);
  });

  it('calls onRollback with variant id when rollback clicked', () => {
    const onRollback = vi.fn();
    const variants = [makeVariant(2, true), makeVariant(1), makeVariant(0)];
    render(<VersionHistoryPanel variants={variants} onRollback={onRollback} />);
    const rollbackButtons = screen.getAllByRole('button', { name: /rollback/i });
    fireEvent.click(rollbackButtons[0]);
    // First rollback button should be for variant 1 (index 1 in the list)
    expect(onRollback).toHaveBeenCalledWith('var-1');
  });
});
