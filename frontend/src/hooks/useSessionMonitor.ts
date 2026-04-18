'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect, useRef, useCallback } from 'react';
import { createClient } from '@/lib/supabase/client';
import { signOut } from '@/services/auth';

/** Idle timeout in milliseconds — 30 minutes of no activity forces re-login. */
const IDLE_TIMEOUT_MS = 30 * 60 * 1000;

/** How often to check for idle timeout (every 60 seconds). */
const CHECK_INTERVAL_MS = 60 * 1000;

/** Events that count as "user activity". */
const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'scroll', 'touchstart', 'pointermove'] as const;

/**
 * Monitors user session for expiry and idle timeout.
 *
 * - Listens to Supabase auth state changes (TOKEN_REFRESHED failures, SIGNED_OUT)
 * - Tracks user activity and forces logout after IDLE_TIMEOUT_MS of inactivity
 * - Redirects to /auth/login on session expiry
 *
 * Mount this hook once in a layout that wraps all authenticated pages.
 */
export function useSessionMonitor() {
  const lastActivityRef = useRef<number>(Date.now());
  const isRedirectingRef = useRef(false);

  const forceLogout = useCallback(async () => {
    // Prevent multiple redirects
    if (isRedirectingRef.current) return;
    isRedirectingRef.current = true;

    try {
      await signOut();
    } catch {
      // Sign out may fail if token is already expired — that's fine
    }

    // Clear any cached persona/onboarding cookies by navigating to login
    // The proxy.ts will handle cookie cleanup on next protected route access
    window.location.href = '/auth/login?reason=session_expired';
  }, []);

  const recordActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
  }, []);

  useEffect(() => {
    // Skip in non-browser environments
    if (typeof window === 'undefined') return;

    // Skip session monitoring on public pages where no session is expected
    const publicPaths = ['/', '/auth', '/privacy', '/terms', '/data-deletion'];
    const pathname = window.location.pathname;
    const isPublicPage = publicPaths.some(path =>
      pathname === path || pathname.startsWith(path + '/')
    );
    if (isPublicPage) return;

    const supabase = createClient();

    // --- 1. Listen for auth state changes ---
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event: string) => {
        if (event === 'SIGNED_OUT') {
          // Another tab signed out, or token refresh failed
          if (!isRedirectingRef.current) {
            isRedirectingRef.current = true;
            window.location.href = '/auth/login';
          }
        }

        if (event === 'TOKEN_REFRESHED') {
          // Token was successfully refreshed — reset activity timer
          lastActivityRef.current = Date.now();
        }
      }
    );

    // --- 2. Track user activity for idle timeout ---
    for (const event of ACTIVITY_EVENTS) {
      window.addEventListener(event, recordActivity, { passive: true });
    }

    // --- 3. Periodic idle check ---
    const idleCheckInterval = setInterval(async () => {
      // Skip verification when tab is backgrounded to reduce auth calls
      if (document.hidden) return;

      const idleTime = Date.now() - lastActivityRef.current;

      if (idleTime >= IDLE_TIMEOUT_MS) {
        console.warn(
          `Session idle for ${Math.round(idleTime / 60000)}min — forcing logout`
        );
        await forceLogout();
        return;
      }

      // Also verify the session is still valid on each check
      // This catches cases where the JWT expired and Supabase couldn't refresh
      const { data: { user }, error } = await supabase.auth.getUser();
      if (error || !user) {
        console.warn('Session verification failed — forcing logout:', error?.message);
        await forceLogout();
      }
    }, CHECK_INTERVAL_MS);

    // --- Cleanup ---
    return () => {
      subscription.unsubscribe();
      clearInterval(idleCheckInterval);
      for (const event of ACTIVITY_EVENTS) {
        window.removeEventListener(event, recordActivity);
      }
    };
  }, [forceLogout, recordActivity]);
}
