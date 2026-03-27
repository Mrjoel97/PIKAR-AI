'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


interface PageEntry {
  page_slug: string;
  page_title: string;
  status: 'pending' | 'building' | 'complete';
}

interface MultiPageProgressProps {
  pages: PageEntry[];
  currentIndex: number;
  totalPages: number;
}

/**
 * Per-page progress indicator for multi-page build streaming.
 * Shows a horizontal row of page status indicators and current build text.
 */
export default function MultiPageProgress({
  pages,
  currentIndex,
  totalPages,
}: MultiPageProgressProps) {
  const currentPage = pages[currentIndex];

  return (
    <div
      data-testid="multi-page-progress"
      className="rounded-xl border border-indigo-100 bg-indigo-50 p-4"
    >
      {/* Page indicators */}
      <div className="flex gap-2 mb-3 flex-wrap">
        {pages.map((page, i) => (
          <div
            key={page.page_slug}
            title={page.page_title}
            className={[
              'h-2 flex-1 min-w-[24px] rounded-full transition-all duration-300',
              page.status === 'complete'
                ? 'bg-green-500'
                : page.status === 'building'
                  ? 'bg-indigo-500 animate-pulse'
                  : 'bg-slate-200',
            ].join(' ')}
            aria-label={`${page.page_title}: ${page.status}`}
          />
        ))}
      </div>

      {/* Progress text */}
      <p className="text-sm text-indigo-700 font-medium">
        {currentPage
          ? `Building page ${currentIndex + 1} of ${totalPages}: ${currentPage.page_title}`
          : `Building ${totalPages} pages...`}
      </p>
    </div>
  );
}
