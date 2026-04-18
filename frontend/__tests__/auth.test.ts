/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { signUp, signIn, signOut, signInWithGoogle } from '../src/services/auth';
import * as supabaseClient from '@/lib/supabase/client';
const { createClient } = supabaseClient;

// Mock Supabase client
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(),
  clearSupabaseBrowserState: vi.fn(),
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
    (createClient as any).mockReturnValue(mockSupabase);
  });

  it('signInWithGoogle should call supabase.auth.signInWithOAuth', async () => {
    mockSupabase.auth.signInWithOAuth.mockResolvedValue({ data: { url: 'http://url' }, error: null });
    
    await signInWithGoogle();
    
    expect(mockSupabase.auth.signInWithOAuth).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'google',
      options: expect.objectContaining({
        redirectTo: expect.stringContaining('/auth/callback'),
      }),
    }));
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

  it('signOut should fall back to local sign-out when the global sign-out hangs', async () => {
    vi.useFakeTimers();
    mockSupabase.auth.signOut
      .mockImplementationOnce(() => new Promise(() => {}))
      .mockResolvedValueOnce({ error: null });

    const signOutPromise = signOut();
    await vi.advanceTimersByTimeAsync(3000);
    await signOutPromise;

    expect(mockSupabase.auth.signOut).toHaveBeenNthCalledWith(1);
    expect(mockSupabase.auth.signOut).toHaveBeenNthCalledWith(2, { scope: 'local' });
    expect(vi.mocked(supabaseClient.clearSupabaseBrowserState)).toHaveBeenCalled();

    vi.useRealTimers();
  });
});
