// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '@/services/api';

export interface KpiItem {
  label: string;
  value: string;
  unit: string;
  subtitle?: string;
}

export interface KpiData {
  persona: string;
  kpis: KpiItem[];
}

export function useKpis(): {
  kpis: KpiItem[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
} {
  const [kpis, setKpis] = useState<KpiItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;

    async function fetchKpis(): Promise<void> {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetchWithAuth('/kpis/persona');
        if (!response.ok) {
          throw new Error(`KPI fetch failed: ${response.status} ${response.statusText}`);
        }
        const data: KpiData = await response.json() as KpiData;
        if (!cancelled) {
          setKpis(data.kpis ?? []);
        }
      } catch (err) {
        console.error('[useKpis] Failed to fetch KPIs:', err);
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch KPIs');
          setKpis([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void fetchKpis();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return { kpis, isLoading, error, refresh };
}
