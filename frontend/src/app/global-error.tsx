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
            <body>
                <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px', fontFamily: 'system-ui, sans-serif', background: '#0f172a', color: '#f1f5f9' }}>
                    <div style={{ maxWidth: '28rem', textAlign: 'center' }}>
                        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                            Something went wrong
                        </h1>
                        <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
                            A critical error occurred. Your data is safe.
                        </p>
                        {error.digest && (
                            <p style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontFamily: 'monospace' }}>
                                Error ID: {error.digest}
                            </p>
                        )}
                        <button
                            onClick={reset}
                            style={{ padding: '0.625rem 1.25rem', background: '#4f46e5', color: '#fff', fontSize: '0.875rem', fontWeight: 500, borderRadius: '0.75rem', border: 'none', cursor: 'pointer' }}
                        >
                            Try again
                        </button>
                    </div>
                </div>
            </body>
        </html>
    );
}
