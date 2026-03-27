'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { listProjectScreens, advanceStage } from '@/services/app-builder';
import type { AppScreen } from '@/types/app-builder';

type ScreenWithUrl = AppScreen & { html_url: string };

/**
 * Verifying page — tab-based multi-page preview after build completes.
 * Each tab shows that page's generated HTML in an iframe preview.
 * User can approve and ship or go back to building.
 */
export default function VerifyingPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params?.projectId ?? '';
  const router = useRouter();

  const [screens, setScreens] = useState<ScreenWithUrl[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isShipping, setIsShipping] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    listProjectScreens(projectId)
      .then((data) => setScreens(data))
      .catch(console.error);
  }, [projectId]);

  async function handleApproveAndShip() {
    if (isShipping) return;
    setIsShipping(true);
    try {
      await advanceStage(projectId, 'shipping');
      router.push(`/app-builder/${projectId}/shipping`);
    } catch {
      setIsShipping(false);
    }
  }

  const activeScreen = screens[activeIndex] ?? null;

  if (screens.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="h-8 w-48 animate-pulse rounded-md bg-slate-200 mb-4" />
        <p className="text-sm text-slate-400">Loading pages...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-800 mb-1">Review Your Pages</h1>
        <p className="text-sm text-slate-500">
          All {screens.length} pages have been generated. Review each page below and approve to ship.
        </p>
      </div>

      {/* Tab row */}
      <div className="flex gap-1 border-b border-slate-200">
        {screens.map((screen, i) => (
          <button
            key={screen.id}
            type="button"
            onClick={() => setActiveIndex(i)}
            className={[
              'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
              i === activeIndex
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            ].join(' ')}
          >
            {screen.name}
          </button>
        ))}
      </div>

      {/* iframe preview */}
      {activeScreen && (
        <iframe
          key={activeScreen.id}
          src={activeScreen.html_url}
          title="Page preview"
          sandbox="allow-scripts allow-same-origin"
          className="w-full h-[80vh] rounded-lg border border-slate-200"
        />
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => router.push(`/app-builder/${projectId}/building`)}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Back to Building
        </button>
        <button
          type="button"
          onClick={handleApproveAndShip}
          disabled={isShipping}
          className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {isShipping ? 'Shipping...' : 'Approve & Ship'}
        </button>
      </div>
    </div>
  );
}
