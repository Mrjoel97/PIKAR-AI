'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { Component, type ReactNode, type ErrorInfo } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  /** Optional keys whose change auto-resets the boundary (e.g. [pathname]). */
  resetKeys?: ReadonlyArray<unknown>;
  /** Optional fallback title override. */
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Reusable React 19 error boundary used at the layout level.
 *
 * Catches render-time errors in any descendant client component and renders a
 * recovery UI with "Try again" (resets local state) and "Go to Dashboard"
 * (hard navigation fallback). Auto-resets when any value in `resetKeys` changes.
 *
 * Wired into both `app/layout.tsx` (root) and `app/(personas)/layout.tsx`
 * (per-persona) so a crash in one persona's dashboard does not unmount the
 * top-level providers.
 *
 * TODO(phase-51 OBS-01): wire `Sentry.captureException(error, { extra: errorInfo })`
 * inside `componentDidCatch` once the Sentry SDK lands. The signature is
 * intentionally `(error: Error, errorInfo: ErrorInfo)` so the integration can
 * pass `errorInfo.componentStack` directly to Sentry's `extra` payload.
 */
export class RootErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log the full component stack so it can be diagnosed in browser DevTools.
    // In production this is also the Sentry hook point (Phase 51 OBS-01).
    console.error(
      'RootErrorBoundary caught an error:',
      error,
      errorInfo.componentStack,
    );
  }

  componentDidUpdate(prevProps: Props): void {
    if (!this.state.hasError) return;
    const prev = prevProps.resetKeys ?? [];
    const next = this.props.resetKeys ?? [];
    if (prev.length !== next.length) {
      this.handleRetry();
      return;
    }
    for (let i = 0; i < prev.length; i++) {
      if (prev[i] !== next[i]) {
        this.handleRetry();
        return;
      }
    }
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="min-h-[60vh] flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
            {this.props.fallbackTitle ?? 'Something went wrong'}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mb-6 text-sm">
            A part of this page failed to load. Your data is safe.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              type="button"
              onClick={this.handleRetry}
              className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors"
            >
              Try again
            </button>
            <a
              href="/dashboard"
              className="px-5 py-2.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium rounded-xl hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
            >
              Go to Dashboard
            </a>
          </div>
        </div>
      </div>
    );
  }
}

export default RootErrorBoundary;
