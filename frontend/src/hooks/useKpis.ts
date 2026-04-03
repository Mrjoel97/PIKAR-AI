// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/services/api';

export interface KpiItem {
  label: string;
  value: string;
  unit: string;
}

export interface KpiData {
  persona: string;
  kpis: KpiItem[];
}

export function useKpis(): {
  kpis: KpiItem[];
  isLoading: boolean;
  error: string | null;
} {
  const [kpis, setKpis] = useState<KpiItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchKpis(): Promise<void> {
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
  }, []);

  return { kpis, isLoading, error };
}
