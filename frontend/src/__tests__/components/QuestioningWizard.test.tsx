// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QuestioningWizard } from '@/components/app-builder/QuestioningWizard';

// Mock next/navigation so router.push works in tests
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
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
  createProject: vi.fn(),
}));

import { createProject } from '@/services/app-builder';

describe('QuestioningWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the first question prompt and choice cards on mount', () => {
    render(<QuestioningWizard />);
    expect(screen.getByText('What do you want to build?')).toBeTruthy();
    expect(screen.getByText('Landing page')).toBeTruthy();
    expect(screen.getByText('Web app')).toBeTruthy();
    expect(screen.getByText('Mobile app')).toBeTruthy();
  });

  it('clicking a choice card on a non-final step advances to the next step', async () => {
    render(<QuestioningWizard />);
    // Step 1: "What do you want to build?"
    fireEvent.click(screen.getByText('Landing page'));
    // Should advance to step 2: "Who is this for?"
    await waitFor(() => {
      expect(screen.getByText('Who is this for?')).toBeTruthy();
    });
  });

  it('renders a text input and "Start Building" button on the final step, not choice cards', async () => {
    render(<QuestioningWizard />);
    // Navigate through 4 choice steps
    fireEvent.click(screen.getByText('Landing page'));    // step 1 -> 2
    await waitFor(() => screen.getByText('Who is this for?'));
    fireEvent.click(screen.getByText('My business'));     // step 2 -> 3
    await waitFor(() => screen.getByText('What should visitors do?'));
    fireEvent.click(screen.getByText('Book a call'));     // step 3 -> 4
    await waitFor(() => screen.getByText('Pick a style vibe'));
    fireEvent.click(screen.getByText('Clean & minimal')); // step 4 -> 5 (name)
    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeTruthy();
      expect(screen.getByRole('button', { name: /start building/i })).toBeTruthy();
    });
    // No more choice cards on final step
    expect(screen.queryByText('Landing page')).toBeNull();
  });

  it('clicking "Start Building" calls createProject with title and creative_brief', async () => {
    const mockProject = { id: 'proj-123', title: 'My App' };
    (createProject as ReturnType<typeof vi.fn>).mockResolvedValue(mockProject);

    render(<QuestioningWizard />);
    // Navigate to final step
    fireEvent.click(screen.getByText('Landing page'));
    await waitFor(() => screen.getByText('Who is this for?'));
    fireEvent.click(screen.getByText('My business'));
    await waitFor(() => screen.getByText('What should visitors do?'));
    fireEvent.click(screen.getByText('Book a call'));
    await waitFor(() => screen.getByText('Pick a style vibe'));
    fireEvent.click(screen.getByText('Clean & minimal'));
    await waitFor(() => screen.getByRole('textbox'));

    // Enter project name
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'My App' } });
    fireEvent.click(screen.getByRole('button', { name: /start building/i }));

    await waitFor(() => {
      expect(createProject).toHaveBeenCalledWith({
        title: 'My App',
        creative_brief: expect.objectContaining({ what: 'Landing page', name: 'My App' }),
      });
    });
  });

  it('disables the "Start Building" button while submitting', async () => {
    // Return a promise that never resolves to simulate loading state
    (createProject as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    render(<QuestioningWizard />);
    fireEvent.click(screen.getByText('Landing page'));
    await waitFor(() => screen.getByText('Who is this for?'));
    fireEvent.click(screen.getByText('My business'));
    await waitFor(() => screen.getByText('What should visitors do?'));
    fireEvent.click(screen.getByText('Book a call'));
    await waitFor(() => screen.getByText('Pick a style vibe'));
    fireEvent.click(screen.getByText('Clean & minimal'));
    await waitFor(() => screen.getByRole('textbox'));

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Test' } });
    const btn = screen.getByRole('button', { name: /start building/i });
    fireEvent.click(btn);

    // Once submitting, the button text changes to "Starting…" — find by role and check disabled
    await waitFor(() => {
      // The button is still present but disabled (either labelled "Start Building" or "Starting…")
      const buttons = screen.getAllByRole('button');
      const submitBtn = buttons.find((b) => b.getAttribute('type') === 'submit');
      expect(submitBtn).toBeDefined();
      // Use DOM property — toBeDisabled() is jest-dom only; vitest uses native DOM
      expect((submitBtn as HTMLButtonElement).disabled).toBe(true);
    });
  });
});
