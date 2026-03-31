'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import type { ScreenVariant } from '@/types/app-builder';

interface VariantComparisonGridProps {
  variants: ScreenVariant[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/**
 * Side-by-side screenshot thumbnail grid for variant comparison.
 * Shows 2 or 3 columns depending on variant count.
 * Selected variant has an indigo ring indicator.
 */
export default function VariantComparisonGrid({
  variants,
  selectedId,
  onSelect,
}: VariantComparisonGridProps) {
  const gridCols = variants.length === 3 ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2';

  return (
    <div className={`grid ${gridCols} gap-4`}>
      {variants.map((variant, index) => {
        const isSelected = variant.id === selectedId;
        const ringClass = isSelected
          ? 'border-indigo-500 ring-2 ring-indigo-200'
          : 'border-slate-200 hover:border-slate-300';

        return (
          <button
            key={variant.id}
            type="button"
            onClick={() => onSelect(variant.id)}
            className={`flex flex-col overflow-hidden rounded-lg border-2 ${ringClass} transition-all focus:outline-none`}
          >
            {variant.screenshot_url ? (
              <img
                src={variant.screenshot_url}
                alt={`Variant ${index + 1}`}
                className="aspect-video w-full object-cover object-top"
              />
            ) : (
              <div className="aspect-video w-full bg-slate-100 flex items-center justify-center">
                <span className="text-slate-400 text-sm">No preview</span>
              </div>
            )}
            <div className="px-3 py-2 text-center text-sm font-medium text-slate-700">
              Variant {index + 1}
            </div>
          </button>
        );
      })}
    </div>
  );
}
