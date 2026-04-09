/**
 * @vitest-environment jsdom
 */
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { UpgradeGateModal } from '../../src/components/layout/UpgradeGateModal';

// Mock featureGating so tests aren't coupled to actual feature config
vi.mock('../../src/config/featureGating', () => ({
  FEATURE_ACCESS: {
    compliance: {
      label: 'Compliance Suite',
      description: 'Automate regulatory compliance tracking and document management.',
      minTier: 'enterprise',
    },
    workflows: {
      label: 'Workflow Engine',
      description: 'Automate multi-step business processes with the visual workflow builder.',
      minTier: 'solopreneur',
    },
  },
}));

afterEach(() => {
  cleanup();
});

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  feature: 'compliance',
  currentTier: 'solopreneur',
  requiredTier: 'enterprise',
};

describe('UpgradeGateModal', () => {
  it('renders feature name, description, required tier badge, and CTA button', () => {
    render(<UpgradeGateModal {...defaultProps} />);

    // Feature label from FEATURE_ACCESS (rendered as "Unlock Compliance Suite" in heading)
    expect(screen.getByText(/Compliance Suite/i)).toBeDefined();
    // Feature description
    expect(screen.getByText('Automate regulatory compliance tracking and document management.')).toBeDefined();
    // Required tier badge
    expect(screen.getByText(/enterprise/i)).toBeDefined();
    // CTA button present
    expect(screen.getByRole('button', { name: /contact us/i })).toBeDefined();
  });

  it('shows "Upgrade to {tier}" CTA for non-enterprise required tiers', () => {
    render(
      <UpgradeGateModal
        isOpen={true}
        onClose={vi.fn()}
        feature="workflows"
        currentTier="free"
        requiredTier="startup"
      />,
    );

    const cta = screen.getByRole('button', { name: /upgrade to startup/i });
    expect(cta).toBeDefined();
  });

  it('shows "Contact us" CTA for enterprise-tier gates', () => {
    render(<UpgradeGateModal {...defaultProps} requiredTier="enterprise" />);

    expect(screen.getByRole('button', { name: /contact us/i })).toBeDefined();
    // Should NOT show a standard "Upgrade to" button
    expect(screen.queryByRole('button', { name: /upgrade to/i })).toBeNull();
  });

  it('calls onClose when the dismiss button is clicked', () => {
    const onClose = vi.fn();
    render(<UpgradeGateModal {...defaultProps} onClose={onClose} />);

    fireEvent.click(screen.getByRole('button', { name: /maybe later/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does not render modal content when isOpen is false', () => {
    render(<UpgradeGateModal {...defaultProps} isOpen={false} />);

    // The modal overlay and content should not be visible
    expect(screen.queryByText('Compliance Suite')).toBeNull();
    expect(screen.queryByRole('button', { name: /contact us/i })).toBeNull();
  });

  it('calls onClose when the overlay backdrop is clicked', () => {
    const onClose = vi.fn();
    render(<UpgradeGateModal {...defaultProps} onClose={onClose} />);

    // Click the overlay (outermost div with the backdrop role)
    const backdrop = screen.getByTestId('upgrade-gate-backdrop');
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('falls back to raw feature string when feature key not in FEATURE_ACCESS', () => {
    render(
      <UpgradeGateModal
        isOpen={true}
        onClose={vi.fn()}
        feature="unknown-feature"
        currentTier="solopreneur"
        requiredTier="startup"
      />,
    );

    // Should render the raw feature string as title fallback
    expect(screen.getByText(/unknown-feature/i)).toBeDefined();
  });
});
