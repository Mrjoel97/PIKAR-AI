// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import React from 'react';
import type { KpiItem } from '@/hooks/useKpis';

interface KpiBarProps {
  kpiLabels: string[];
  kpis: KpiItem[];
  isLoading: boolean;
}

export function KpiBar({ kpiLabels, kpis, isLoading }: KpiBarProps) {
  return (
    <>
      {kpiLabels.map((label) => {
        const match = kpis.find(
          (k) => k.label.toLowerCase() === label.toLowerCase(),
        );

        let valueNode: React.ReactNode;
        if (isLoading) {
          valueNode = (
            <span className="animate-pulse font-semibold">...</span>
          );
        } else if (match) {
          valueNode = <span className="font-semibold">{match.value}</span>;
        } else {
          valueNode = <span className="font-semibold">&mdash;</span>;
        }

        return (
          <span
            key={label}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/10 text-white/90 text-[11px] font-medium tracking-wide"
          >
            {label}:{'\u00A0'}
            {valueNode}
          </span>
        );
      })}
    </>
  );
}
