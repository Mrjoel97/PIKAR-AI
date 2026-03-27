// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ApprovalCheckpointCard from '@/components/app-builder/ApprovalCheckpointCard';

describe('ApprovalCheckpointCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders approve button with screen name when not approved', () => {
    render(
      <ApprovalCheckpointCard
        screenName="Home Page"
        onApprove={vi.fn()}
        isApproved={false}
      />,
    );
    expect(screen.getByText(/Home Page/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /approve screen/i })).toBeTruthy();
  });

  it('approve button is disabled during submission (double-click protection)', async () => {
    let resolveApprove: () => void;
    const onApprove = vi.fn(
      () => new Promise<void>((resolve) => { resolveApprove = resolve; }),
    );
    render(
      <ApprovalCheckpointCard
        screenName="Home Page"
        onApprove={onApprove}
        isApproved={false}
      />,
    );
    const button = screen.getByRole('button', { name: /approve screen/i }) as HTMLButtonElement;
    fireEvent.click(button);
    // Button should be disabled while the async call is in progress
    expect(button.disabled).toBe(true);
    resolveApprove!();
  });

  it('renders green approved banner when isApproved=true', () => {
    render(
      <ApprovalCheckpointCard
        screenName="Home Page"
        onApprove={vi.fn()}
        isApproved={true}
      />,
    );
    expect(screen.getByText(/screen approved/i)).toBeTruthy();
  });
});
