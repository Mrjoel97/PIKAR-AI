/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ForgotPasswordPage from '@/app/auth/forgot-password/page';
import { resetPasswordForEmail } from '@/services/auth';

// Mock the auth service
vi.mock('@/services/auth', () => ({
  resetPasswordForEmail: vi.fn(),
}));

// Mock Next.js router
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the forgot password form', () => {
    render(<ForgotPasswordPage />);
    expect(screen.getByPlaceholderText(/email/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /reset password/i })).toBeDefined();
  });

  it('calls resetPasswordForEmail on submit', async () => {
    render(<ForgotPasswordPage />);
    const emailInput = screen.getByPlaceholderText(/email/i);
    const submitButton = screen.getByRole('button', { name: /reset password/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(resetPasswordForEmail).toHaveBeenCalledWith('test@example.com');
    });
  });

  it('displays success message on success', async () => {
    (resetPasswordForEmail as any).mockResolvedValue({});
    render(<ForgotPasswordPage />);
    const emailInput = screen.getByPlaceholderText(/email/i);
    const submitButton = screen.getByRole('button', { name: /reset password/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/check your email/i)).toBeDefined();
    });
  });
  
  it('displays error message on failure', async () => {
    (resetPasswordForEmail as any).mockRejectedValue(new Error('Invalid email'));
    render(<ForgotPasswordPage />);
    const emailInput = screen.getByPlaceholderText(/email/i);
    const submitButton = screen.getByRole('button', { name: /reset password/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeDefined();
    });
  });
});
