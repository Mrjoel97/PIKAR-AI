/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import ProtectedRoute from '../../src/components/auth/ProtectedRoute';

// Mock useRouter
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

// Mock Supabase
const mockGetSession = vi.fn();
vi.mock('@supabase/auth-helpers-nextjs', () => ({
  createClientComponentClient: () => ({
    auth: {
      getSession: mockGetSession,
    },
  }),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('ProtectedRoute', () => {
  it('renders children when authenticated', async () => {
    mockGetSession.mockResolvedValue({ data: { session: { user: { id: '1' } } }, error: null });

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Protected Content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(screen.getByTestId('protected-content')).toBeDefined();
    });
  });

  it('redirects to login when not authenticated', async () => {
    mockGetSession.mockResolvedValue({ data: { session: null }, error: null });

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });
});
