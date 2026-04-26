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

  return (
    <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
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
      </div>

      <div className="space-y-4 px-5 py-5">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/70">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
              <Layers3 className="h-4 w-4 text-sky-500" />
              Canvas Access
            </div>
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              Jump into the guided canvas to answer brief questions, generate screens, and iterate on the build.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/70">
            <div className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-200">
              Current Target
            </div>
            <p className="break-all text-sm leading-6 text-slate-600 dark:text-slate-300">
              {targetPath}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() =>
              navigate(projectId ? 'open_app_builder_project' : 'open_app_builder', {
                projectId,
                targetPath,
              })
            }
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {primaryLabel}
            <ArrowRight className="h-4 w-4" />
          </button>

          {projectId ? (
            <button
              type="button"
              onClick={() => navigate('open_app_builder', { targetPath: '/app-builder/new' })}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Start New App
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
