'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { type LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  gradient?: string;
}

export default function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  gradient = 'from-slate-400 to-slate-500',
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.21, 0.47, 0.32, 0.98] }}
      className="flex flex-col items-center justify-center rounded-[28px] border-2 border-dashed border-slate-200 bg-white/50 px-8 py-16"
    >
      <div className={`rounded-2xl bg-gradient-to-br ${gradient} p-4 shadow-lg mb-4`}>
        <Icon className="h-8 w-8 text-white" />
      </div>
      <h3 className="text-lg font-semibold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 text-center max-w-sm mb-4">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg hover:bg-teal-700 transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </motion.div>
  );
}
