'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * WorkflowLauncher -- Inline panel showing NL-matched workflows with one-click launch.
 *
 * Appears contextually when a user's message looks like a workflow request
 * (e.g. "I want to launch a product"). Each match shows name, description,
 * category badge, confidence indicator, and a Start button.
 */

import { Sparkles, Play } from 'lucide-react';

import type { WorkflowMatch } from '@/services/suggestions';

interface WorkflowLauncherProps {
  matches: WorkflowMatch[];
  onLaunch: (templateName: string) => void;
  onDismiss: () => void;
}

function ConfidenceDot({ score }: { score: number }) {
  const color =
    score >= 0.7
      ? 'bg-green-500'
      : score >= 0.4
        ? 'bg-yellow-500'
        : 'bg-slate-400';
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${color} flex-shrink-0`}
      title={`Match confidence: ${Math.round(score * 100)}%`}
    />
  );
}

export function WorkflowLauncher({ matches, onLaunch, onDismiss }: WorkflowLauncherProps) {
  if (matches.length === 0) return null;

  return (
    <div className="mb-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={16} className="text-teal-500" />
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          Matching Workflows
        </span>
      </div>

      {/* Match list */}
      <div className="space-y-2">
        {matches.map((match) => (
          <div
            key={match.name}
            className="flex items-center gap-3 p-3 rounded-lg border border-slate-100 dark:border-slate-800 hover:border-teal-200 dark:hover:border-teal-800 transition-colors"
          >
            <ConfidenceDot score={match.match_score} />

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
                {match.name}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                {match.description}
              </p>
            </div>

            <span className="flex-shrink-0 px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-[10px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              {match.category}
            </span>

            <button
              type="button"
              onClick={() => onLaunch(match.name)}
              className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 text-white text-xs font-medium rounded-lg hover:bg-teal-700 transition-colors shadow-sm"
            >
              <Play size={12} />
              <span>Start Workflow</span>
            </button>
          </div>
        ))}
      </div>

      {/* Dismiss */}
      <button
        type="button"
        onClick={onDismiss}
        className="mt-3 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
      >
        Not what I&apos;m looking for
      </button>
    </div>
  );
}
