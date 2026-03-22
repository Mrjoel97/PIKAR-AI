'use client';

import { useEffect } from 'react';

export default function AppError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Unhandled application error:', error);
    }, [error]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-6">
            <div className="max-w-md w-full text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                    <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
                    </svg>
                </div>
                <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
                    Something went wrong
                </h1>
                <p className="text-slate-500 dark:text-slate-400 mb-6 text-sm">
                    An unexpected error occurred. Your data is safe — try refreshing the page.
                </p>
                {error.digest && (
                    <p className="text-xs text-slate-400 dark:text-slate-500 mb-4 font-mono">
                        Error ID: {error.digest}
                    </p>
                )}
                <div className="flex gap-3 justify-center">
                    <button
                        onClick={reset}
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
