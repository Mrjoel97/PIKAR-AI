'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { type LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  color?: string;
  bg?: string;
  gradient?: string;
  subtitle?: string;
  delay?: number;
}

/**
 * Premium KPI card matching CommandCenter design language.
 *
 * - `gradient` overrides `bg`/`color` with a vibrant icon background.
 *   Example: `"from-emerald-400 to-teal-500"`
 * - Backwards-compatible: existing callers using `bg`/`color` still work.
 */
export default function MetricCard({
  label,
  value,
  icon: Icon,
  color = 'text-teal-600',
  bg = 'bg-teal-50',
  gradient,
  subtitle,
  delay = 0,
}: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.21, 0.47, 0.32, 0.98] }}
      className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-35px_rgba(15,23,42,0.4)] transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            {label}
          </p>
          <p className="mt-1.5 text-2xl font-bold text-slate-900 truncate">{value}</p>
          {subtitle && (
            <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
          )}
        </div>
        {gradient ? (
          <div
            className={`flex-shrink-0 rounded-2xl bg-gradient-to-br ${gradient} p-3 shadow-lg`}
          >
            <Icon className="h-5 w-5 text-white" />
          </div>
        ) : (
          <div className={`flex-shrink-0 rounded-2xl p-3 ${bg}`}>
            <Icon className={`h-5 w-5 ${color}`} />
          </div>
        )}
      </div>
    </motion.div>
  );
}
