/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResetPasswordPage from '@/app/auth/reset-password/page';
import { updateUser } from '@/services/auth';

// Mock the auth service
vi.mock('@/services/auth', () => ({
  updateUser: vi.fn(),
}));

// Mock Next.js router
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the reset password form', () => {
    render(<ResetPasswordPage />);
    expect(screen.getByPlaceholderText(/new password/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /update password/i })).toBeDefined();
  });

  it('calls updateUser on submit', async () => {
    render(<ResetPasswordPage />);
    const passwordInput = screen.getByPlaceholderText(/new password/i);
    const submitButton = screen.getByRole('button', { name: /update password/i });

    fireEvent.change(passwordInput, { target: { value: 'newpassword123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(updateUser).toHaveBeenCalledWith({ password: 'newpassword123' });
    });
  });

  it('redirects to dashboard on success', async () => {
    (updateUser as any).mockResolvedValue({});
    render(<ResetPasswordPage />);
    const passwordInput = screen.getByPlaceholderText(/new password/i);
    const submitButton = screen.getByRole('button', { name: /update password/i });

    fireEvent.change(passwordInput, { target: { value: 'newpassword123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/');
    });
  });

  it('displays error message on failure', async () => {
    (updateUser as any).mockRejectedValue(new Error('Update failed'));
    render(<ResetPasswordPage />);
    const passwordInput = screen.getByPlaceholderText(/new password/i);
    const submitButton = screen.getByRole('button', { name: /update password/i });

    fireEvent.change(passwordInput, { target: { value: 'newpassword123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/update failed/i)).toBeDefined();
    });
  });
});
