/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import SignupPage from '@/app/auth/signup/page';

// Mock the auth service
vi.mock('@/services/auth', () => ({
  signUp: vi.fn(),
}));

// Mock router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('SignupPage', () => {
  it('renders Sign In link', () => {
    render(<SignupPage />);
    const link = screen.getByRole('link', { name: /sign in/i }); // Or "Already have an account?"
    expect(link).toBeDefined();
    expect(link.getAttribute('href')).toBe('/auth/login');
  });
});
