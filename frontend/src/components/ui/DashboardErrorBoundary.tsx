'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class DashboardErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Always log the actual error so the production console retains
    // diagnostic detail even though the UI shows a generic fallback.
    console.error(
      `[${this.props.fallbackTitle || 'DashboardErrorBoundary'}] caught error:`,
      error,
      info,
    );
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      const errorMessage = this.state.error?.message;
      return (
        <div className="flex flex-col items-center justify-center rounded-[28px] border border-rose-200 bg-white px-8 py-16 shadow-[0_18px_60px_-35px_rgba(15,23,42,0.4)]">
          <div className="rounded-2xl bg-gradient-to-br from-rose-400 to-rose-500 p-4 shadow-lg mb-4">
            <AlertTriangle className="h-8 w-8 text-white" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 mb-1">
            {this.props.fallbackTitle || 'Something went wrong'}
          </h3>
          <p className="text-sm text-slate-500 text-center max-w-sm mb-4">
            An unexpected error occurred. Please try again.
          </p>
          {errorMessage && (
            <details className="mb-4 max-w-md text-xs text-slate-500 bg-slate-50 rounded-xl px-4 py-2 w-full">
              <summary className="cursor-pointer font-medium text-slate-700">
                Error detail
              </summary>
              <pre className="mt-2 whitespace-pre-wrap break-words text-rose-600">
                {errorMessage}
              </pre>
            </details>
          )}
          <button
            onClick={this.handleRetry}
            className="rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg hover:bg-teal-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
