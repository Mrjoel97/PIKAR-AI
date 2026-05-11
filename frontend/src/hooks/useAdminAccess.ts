// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Detects whether the current user has admin role access.
 *
 * Calls GET /admin/check-access once on mount and caches the result in
 * sessionStorage so the sidebar can show an "Admin Panel" entry without
 * re-fetching on every page navigation. Admin status is role-gated server
 * side (see app/admin/layout.tsx), not tier-gated, so it lives outside
 * the FEATURE_ACCESS matrix.
 */

import { useEffect, useState } from 'react';
import { fetchWithAuthRaw } from '@/services/api';

const STORAGE_KEY = 'pikar:admin-access';

type CachedResult = { access: boolean; ts: number };

const CACHE_TTL_MS = 5 * 60 * 1000;

function readCache(): CachedResult | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as CachedResult;
    if (Date.now() - parsed.ts > CACHE_TTL_MS) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeCache(access: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }
  const payload: CachedResult = { access, ts: Date.now() };
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

export interface AdminAccessResult {
  isAdmin: boolean;
  isLoading: boolean;
}

export function useAdminAccess(): AdminAccessResult {
  const cached = readCache();
  const [isAdmin, setIsAdmin] = useState<boolean>(cached?.access ?? false);
  const [isLoading, setIsLoading] = useState<boolean>(cached === null);

  useEffect(() => {
    if (cached !== null) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetchWithAuthRaw('/admin/check-access');
        if (cancelled) {
          return;
        }
        if (!res.ok) {
          setIsAdmin(false);
          writeCache(false);
          return;
        }
        const data = (await res.json()) as { access?: boolean };
        const access = Boolean(data?.access);
        setIsAdmin(access);
        writeCache(access);
      } catch {
        if (!cancelled) {
          setIsAdmin(false);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { isAdmin, isLoading };
}
