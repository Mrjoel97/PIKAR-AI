'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  DollarSign,
  Sun,
  LayoutGrid,
  Megaphone,
  TrendingUp,
  Rocket,
  Activity,
  BarChart3,
  Building2,
  Users,
  type LucideIcon,
} from 'lucide-react';
import { usePersona } from '@/contexts/PersonaContext';
import { getPersonaEmptyState } from '@/components/personas/personaEmptyStates';
import { PERSONA_SHELL_CONFIG } from '@/components/personas/personaShellConfig';

const ICON_MAP: Record<string, LucideIcon> = {
  'dollar-sign': DollarSign,
  sun: Sun,
  'layout-grid': LayoutGrid,
  megaphone: Megaphone,
  'trending-up': TrendingUp,
  rocket: Rocket,
  activity: Activity,
  'bar-chart-3': BarChart3,
  'building-2': Building2,
  users: Users,
};

interface PersonaEmptyStateProps {
  widgetType: string;
  className?: string;
}

export default function PersonaEmptyState({ widgetType, className }: PersonaEmptyStateProps) {
  const { persona } = usePersona();
  const config = getPersonaEmptyState(persona, widgetType);

  if (!config) {
    return (
      <div className={`flex flex-col items-center justify-center py-12 px-6 ${className ?? ''}`}>
        <p className="text-sm text-slate-500">No data yet</p>
      </div>
    );
  }

  const Icon = ICON_MAP[config.icon] ?? DollarSign;
  const shellConfig = persona
    ? PERSONA_SHELL_CONFIG[persona as keyof typeof PERSONA_SHELL_CONFIG]
    : null;
  const gradient = shellConfig?.gradient ?? 'from-slate-400 to-slate-500';

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.21, 0.47, 0.32, 0.98] }}
      className={`flex flex-col items-center justify-center py-12 px-6 ${className ?? ''}`}
    >
      <div className={`rounded-2xl bg-gradient-to-br ${gradient} p-4 shadow-lg mb-4`}>
        <Icon className="h-8 w-8 text-white" />
      </div>
      <h3 className="text-lg font-semibold text-slate-900 mb-1">{config.headline}</h3>
      <p className="text-sm text-slate-500 text-center max-w-xs mb-4">{config.description}</p>
      <Link
        href={config.ctaHref}
        className="rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg hover:bg-teal-700 transition-colors"
      >
        {config.ctaLabel}
      </Link>
    </motion.div>
  );
}
