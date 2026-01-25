/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoginPage from '@/app/auth/login/page';

// Mock the auth service and form
vi.mock('@/services/auth', () => ({
  signIn: vi.fn(),
  signInWithGoogle: vi.fn(),
}));

// Mock router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('LoginPage', () => {
  it('renders Forgot Password link', () => {
    render(<LoginPage />);
    const link = screen.getByRole('link', { name: /forgot password/i });
    expect(link).toBeDefined();
    expect(link.getAttribute('href')).toBe('/auth/forgot-password');
  });

  it('renders Sign Up link', () => {
    render(<LoginPage />);
    const link = screen.getByRole('link', { name: /sign up/i }); // Or "Don't have an account?"
    expect(link).toBeDefined();
    expect(link.getAttribute('href')).toBe('/auth/signup');
  });
});
