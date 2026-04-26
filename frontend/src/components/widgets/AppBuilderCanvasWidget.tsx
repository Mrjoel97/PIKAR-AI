'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useState } from 'react';
import { ExternalLink, Layers3, RefreshCw } from 'lucide-react';

import type { AppBuilderCanvasData } from '@/types/widgets';

import type { WidgetProps } from './WidgetRegistry';

export default function AppBuilderCanvasWidget({ definition }: WidgetProps) {
  const data = definition.data as unknown as AppBuilderCanvasData;
  const projectId = data?.projectId || '';
  const targetPath =
    data?.targetPath || (projectId ? `/app-builder/${projectId}` : '/app-builder/new');

  const [loadKey, setLoadKey] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const handleReload = () => {
    setIsLoading(true);
    setLoadKey((k) => k + 1);
  };

  return (
    <div className="flex h-full min-h-[640px] w-full flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/60 px-4 py-2.5 dark:border-slate-800 dark:bg-slate-800/50">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          <Layers3 className="h-4 w-4 text-sky-500" />
          {definition.title || 'App Builder Canvas'}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleReload}
            className="rounded-md p-1.5 text-slate-500 transition hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
            title="Reload canvas"
            aria-label="Reload canvas"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <a
            href={targetPath}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md p-1.5 text-slate-500 transition hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
            title="Open in new tab"
            aria-label="Open in new tab"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </div>
      <div className="relative flex-1 bg-white dark:bg-slate-950">
        {isLoading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/80 text-sm text-slate-500 dark:bg-slate-950/80 dark:text-slate-400">
            Loading canvas...
          </div>
        )}
        <iframe
          key={loadKey}
          src={targetPath}
          title="App Builder Canvas"
          className="h-full w-full border-0"
          onLoad={() => setIsLoading(false)}
        />
      </div>
    </div>
  );
}
