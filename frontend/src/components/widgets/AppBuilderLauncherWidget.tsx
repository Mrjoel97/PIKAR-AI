'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React from 'react';
import { ArrowRight, Layers3, Sparkles } from 'lucide-react';

import type { AppBuilderLauncherData } from '@/types/widgets';

import type { WidgetProps } from './WidgetRegistry';

export default function AppBuilderLauncherWidget({ definition, onAction }: WidgetProps) {
  const data = definition.data as unknown as AppBuilderLauncherData;
  const projectId = data?.projectId || '';
  const targetPath =
    data?.targetPath || (projectId ? `/app-builder/${projectId}` : '/app-builder/new');
  const primaryLabel =
    data?.primaryActionLabel || (projectId ? 'Resume App Builder' : 'Open App Builder');
  const summary =
    data?.summary || 'Open the guided app-builder flow to define, preview, and ship your app.';

  const navigate = (action: string, payload: Record<string, unknown>) => {
    if (onAction) {
      onAction(action, payload);
      return;
    }

    if (typeof window !== 'undefined') {
      window.location.href = String(payload.targetPath || '/app-builder/new');
    }
  };

  const primaryAction = projectId ? 'open_app_builder_project' : 'open_app_builder';

  return (
    <button
      type="button"
      onClick={() => navigate(primaryAction, { projectId, targetPath })}
      className="group block w-full overflow-hidden rounded-3xl border border-slate-200 bg-white text-left shadow-sm transition hover:border-slate-300 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
    >
      <div className="border-b border-slate-100 bg-[linear-gradient(135deg,#eff6ff,white_45%,#f5f3ff)] px-5 py-5 dark:border-slate-800 dark:bg-[linear-gradient(135deg,#0f172a,#111827_55%,#1e1b4b)]">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-600 dark:bg-slate-800/80 dark:text-slate-300">
          <Sparkles className="h-3.5 w-3.5" />
          App Builder Ready
        </div>
        <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          {definition.title || 'App Builder'}
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          {summary}
        </p>

        <div
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition group-hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:group-hover:bg-white"
        >
          {primaryLabel}
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3 text-xs text-slate-500 dark:text-slate-400">
        <span className="inline-flex items-center gap-1.5">
          <Layers3 className="h-3.5 w-3.5 text-sky-500" />
          Answer a few questions, then generate and iterate on screens
        </span>
        {projectId ? (
          <span
            role="link"
            tabIndex={0}
            onClick={(event) => {
              event.stopPropagation();
              navigate('open_app_builder', { targetPath: '/app-builder/new' });
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                event.stopPropagation();
                navigate('open_app_builder', { targetPath: '/app-builder/new' });
              }
            }}
            className="cursor-pointer underline-offset-2 hover:text-slate-700 hover:underline dark:hover:text-slate-200"
          >
            Or start a new app instead
          </span>
        ) : null}
      </div>
    </button>
  );
}
