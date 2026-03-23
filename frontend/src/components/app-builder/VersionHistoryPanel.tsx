'use client';

import { RotateCcw } from 'lucide-react';
import type { ScreenVariant } from '@/types/app-builder';

interface VersionHistoryPanelProps {
  variants: ScreenVariant[];
  onRollback: (variantId: string) => void;
}

/**
 * Scrollable list of past screen variants with rollback buttons.
 * Variants are displayed in the order received (caller passes them sorted by iteration DESC).
 */
export default function VersionHistoryPanel({ variants, onRollback }: VersionHistoryPanelProps) {
  if (variants.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Version history</h3>
      <ul className="max-h-64 space-y-2 overflow-y-auto">
        {variants.map((variant) => (
          <li
            key={variant.id}
            className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 p-2"
          >
            {/* Thumbnail */}
            {variant.screenshot_url ? (
              <img
                src={variant.screenshot_url}
                alt={`Iteration ${variant.iteration ?? variant.variant_index} thumbnail`}
                className="h-10 w-16 shrink-0 rounded object-cover"
              />
            ) : (
              <div className="h-10 w-16 shrink-0 rounded bg-slate-200" />
            )}

            {/* Metadata */}
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-slate-700">
                Iteration {variant.iteration ?? variant.variant_index}
              </p>
              <p className="truncate text-xs text-slate-400">
                {new Date(variant.created_at).toLocaleString()}
              </p>
            </div>

            {/* Status / action */}
            {variant.is_selected ? (
              <span className="shrink-0 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
                Current
              </span>
            ) : (
              <button
                type="button"
                onClick={() => onRollback(variant.id)}
                className="flex shrink-0 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 hover:border-indigo-300 hover:text-indigo-700 transition-colors"
                aria-label="Rollback"
              >
                <RotateCcw className="h-3 w-3" />
                Rollback
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
