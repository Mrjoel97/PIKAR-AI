// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import { useEffect } from 'react';

export default function PanelError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[panel-error]', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-2xl rounded-2xl border border-red-700/40 bg-gray-900 p-8 shadow-2xl">
        <h1 className="text-2xl font-bold text-red-400 mb-2">Application error</h1>
        <p className="text-sm text-gray-400 mb-6">
          The admin panel hit an unexpected error while rendering this page.
        </p>

        <div className="space-y-3 text-sm">
          <div>
            <span className="text-gray-500">Message:</span>
            <pre className="mt-1 p-3 bg-gray-950 border border-gray-800 rounded text-red-300 whitespace-pre-wrap break-words">
              {error.message || '<no message>'}
            </pre>
          </div>
          {error.digest && (
            <div>
              <span className="text-gray-500">Digest:</span>{' '}
              <code className="text-gray-300 font-mono text-xs">{error.digest}</code>
            </div>
          )}
          {error.stack && (
            <details className="mt-4">
              <summary className="text-gray-400 cursor-pointer hover:text-gray-200">
                Stack trace
              </summary>
              <pre className="mt-2 p-3 bg-gray-950 border border-gray-800 rounded text-gray-400 text-xs whitespace-pre-wrap break-words max-h-96 overflow-auto">
                {error.stack}
              </pre>
            </details>
          )}
        </div>

        <div className="mt-8 flex gap-3">
          <button
            type="button"
            onClick={reset}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-sm font-medium"
          >
            Try again
          </button>
          <a
            href="/login"
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded text-sm font-medium"
          >
            Back to login
          </a>
        </div>
      </div>
    </div>
  );
}
