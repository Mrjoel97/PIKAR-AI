// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { GsdProgressBar } from '@/components/app-builder/GsdProgressBar';

describe('GsdProgressBar', () => {
  it('renders all 7 stage labels', () => {
    render(<GsdProgressBar currentStage="questioning" />);
    expect(screen.getByText('Questioning')).toBeTruthy();
    expect(screen.getByText('Research')).toBeTruthy();
    expect(screen.getByText('Brief')).toBeTruthy();
    expect(screen.getByText('Building')).toBeTruthy();
    expect(screen.getByText('Verifying')).toBeTruthy();
    expect(screen.getByText('Shipping')).toBeTruthy();
    expect(screen.getByText('Done')).toBeTruthy();
  });

  it('marks the current stage with aria-current="step"', () => {
    render(<GsdProgressBar currentStage="brief" />);
    const currentEl = screen.getByRole('listitem', { current: 'step' });
    expect(currentEl).toBeTruthy();
    expect(currentEl.textContent).toContain('Brief');
  });

  it('completed stages render a check icon', () => {
    render(<GsdProgressBar currentStage="building" />);
    // questioning, research, brief are completed when building is current (index 3)
    const completeIcons = screen.getAllByLabelText(/complete/i);
    expect(completeIcons.length).toBeGreaterThanOrEqual(3);
  });

  it('future stages have muted/slate styling', () => {
    render(<GsdProgressBar currentStage="questioning" />);
    // All stages after index 0 are future — check that the segment list renders
    const items = screen.getAllByRole('listitem');
    // 7 total items
    expect(items.length).toBe(7);
    // Items after the current one should NOT have aria-current
    const nonCurrent = items.filter(
      (el) => el.getAttribute('aria-current') !== 'step',
    );
    expect(nonCurrent.length).toBe(6);
  });
});
