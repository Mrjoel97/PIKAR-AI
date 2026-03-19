'use client';

import React from 'react';

interface StatusBadgeProps {
  status: string;
  variant?: 'default' | 'dot';
}

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  draft: { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400' },
  scheduled: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  backlog: { bg: 'bg-slate-50', text: 'text-slate-500', dot: 'bg-slate-300' },
  published: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  review: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  approved: { bg: 'bg-teal-50', text: 'text-teal-700', dot: 'bg-teal-500' },
  active: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  in_progress: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  sent: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  running: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  paid: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  customer: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  resolved: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  blocked: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
  overdue: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
  critical: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
  failed: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
  warning: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  high: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  medium: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  void: { bg: 'bg-slate-50', text: 'text-slate-500', dot: 'bg-slate-300' },
  churned: { bg: 'bg-slate-50', text: 'text-slate-500', dot: 'bg-slate-300' },
  inactive: { bg: 'bg-slate-50', text: 'text-slate-500', dot: 'bg-slate-300' },
  lead: { bg: 'bg-violet-50', text: 'text-violet-700', dot: 'bg-violet-500' },
  qualified: { bg: 'bg-cyan-50', text: 'text-cyan-700', dot: 'bg-cyan-500' },
  opportunity: { bg: 'bg-indigo-50', text: 'text-indigo-700', dot: 'bg-indigo-500' },
  low: { bg: 'bg-green-50', text: 'text-green-700', dot: 'bg-green-500' },
  connected: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  disconnected: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
};

const DEFAULT_COLORS = { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400' };

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function StatusBadge({ status, variant = 'default' }: StatusBadgeProps) {
  const normalised = status.toLowerCase().trim();
  const colors = STATUS_COLORS[normalised] || DEFAULT_COLORS;

  if (variant === 'dot') {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className={`h-2 w-2 rounded-full ${colors.dot}`} />
        <span className={`text-xs font-medium ${colors.text}`}>{formatStatus(status)}</span>
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold shadow-sm backdrop-blur-sm ${colors.bg} ${colors.text}`}
    >
      {formatStatus(status)}
    </span>
  );
}
