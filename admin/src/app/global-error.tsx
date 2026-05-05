// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          backgroundColor: '#030712',
          color: '#e5e7eb',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1rem',
        }}
      >
        <div
          style={{
            maxWidth: '720px',
            width: '100%',
            border: '1px solid rgba(220, 38, 38, 0.4)',
            borderRadius: '1rem',
            backgroundColor: '#111827',
            padding: '2rem',
          }}
        >
          <h1 style={{ color: '#f87171', fontSize: '1.5rem', margin: '0 0 0.5rem' }}>
            Application error
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.875rem', margin: '0 0 1.5rem' }}>
            The admin app hit an unrecoverable error. Details below — share the
            message and digest with engineering.
          </p>

          <div style={{ fontSize: '0.875rem' }}>
            <div style={{ color: '#6b7280', marginBottom: '0.25rem' }}>Message:</div>
            <pre
              style={{
                margin: 0,
                padding: '0.75rem',
                backgroundColor: '#030712',
                border: '1px solid #1f2937',
                borderRadius: '0.5rem',
                color: '#fca5a5',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontSize: '0.8125rem',
              }}
            >
              {error.message || '<no message>'}
            </pre>
            {error.digest && (
              <div style={{ marginTop: '0.75rem' }}>
                <span style={{ color: '#6b7280' }}>Digest:</span>{' '}
                <code style={{ color: '#d1d5db', fontFamily: 'ui-monospace, monospace', fontSize: '0.75rem' }}>
                  {error.digest}
                </code>
              </div>
            )}
            {error.stack && (
              <details style={{ marginTop: '1rem' }}>
                <summary style={{ color: '#9ca3af', cursor: 'pointer' }}>
                  Stack trace
                </summary>
                <pre
                  style={{
                    marginTop: '0.5rem',
                    padding: '0.75rem',
                    backgroundColor: '#030712',
                    border: '1px solid #1f2937',
                    borderRadius: '0.5rem',
                    color: '#9ca3af',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontSize: '0.75rem',
                    maxHeight: '24rem',
                    overflow: 'auto',
                  }}
                >
                  {error.stack}
                </pre>
              </details>
            )}
          </div>

          <div style={{ marginTop: '2rem', display: 'flex', gap: '0.75rem' }}>
            <button
              type="button"
              onClick={reset}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#4f46e5',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              Try again
            </button>
            <a
              href="/login"
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#1f2937',
                color: '#e5e7eb',
                border: '1px solid #374151',
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
                fontWeight: 500,
                textDecoration: 'none',
              }}
            >
              Back to login
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
