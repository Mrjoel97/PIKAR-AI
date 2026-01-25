/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { signUp, signIn, signOut, signInWithGoogle } from '../src/services/auth';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

// Mock Supabase client
vi.mock('@supabase/auth-helpers-nextjs', () => ({
  createClientComponentClient: vi.fn(),
}));

describe('Auth Service', () => {
  const mockSupabase = {
    auth: {
      signUp: vi.fn(),
      signInWithPassword: vi.fn(),
      signInWithOAuth: vi.fn(),
      signOut: vi.fn(),
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (createClientComponentClient as any).mockReturnValue(mockSupabase);
  });

  it('signInWithGoogle should call supabase.auth.signInWithOAuth', async () => {
    mockSupabase.auth.signInWithOAuth.mockResolvedValue({ data: { url: 'http://url' }, error: null });
    
    await signInWithGoogle();
    
    expect(mockSupabase.auth.signInWithOAuth).toHaveBeenCalledWith({
      provider: 'google',
      options: {
        redirectTo: expect.stringContaining('/auth/callback'),
      },
    });
  });

  it('signUp should call supabase.auth.signUp with correct params', async () => {
    const email = 'test@example.com';
    const password = 'password123';
    mockSupabase.auth.signUp.mockResolvedValue({ data: { user: { id: '1' } }, error: null });

    await signUp(email, password);

    expect(mockSupabase.auth.signUp).toHaveBeenCalledWith({
      email,
      password,
      options: {
        emailRedirectTo: expect.stringContaining('/auth/callback'),
      },
    });
  });

  it('signIn should call supabase.auth.signInWithPassword', async () => {
    const email = 'test@example.com';
    const password = 'password123';
    mockSupabase.auth.signInWithPassword.mockResolvedValue({ data: { session: {} }, error: null });

    await signIn(email, password);

    expect(mockSupabase.auth.signInWithPassword).toHaveBeenCalledWith({
      email,
      password,
    });
  });

  it('signOut should call supabase.auth.signOut', async () => {
    mockSupabase.auth.signOut.mockResolvedValue({ error: null });

    await signOut();

    expect(mockSupabase.auth.signOut).toHaveBeenCalled();
  });
});
