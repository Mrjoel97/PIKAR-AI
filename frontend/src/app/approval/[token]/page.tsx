'use client';

import React, { useEffect, useState, useCallback, Suspense } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Loader2, CheckCircle, XCircle, AlertTriangle, Shield } from 'lucide-react';

interface ApprovalRequest {
    id: string;
    action_type: string;
    payload: Record<string, unknown>;
    status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
    expires_at: string;
}

/**
 * Inner component that reads searchParams (must be wrapped in Suspense).
 */
function ApprovalPageInner({ token }: { token: string }) {
    const searchParams = useSearchParams();
    const [request, setRequest] = useState<ApprovalRequest | null>(null);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Magic-link email action: ?action=APPROVED or ?action=REJECTED
    const emailAction = searchParams.get('action') as 'APPROVED' | 'REJECTED' | null;
    const [pendingEmailAction, setPendingEmailAction] = useState<'APPROVED' | 'REJECTED' | null>(null);

    const fetchRequest = useCallback(async () => {
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/approvals/${token}`);
            if (!res.ok) throw new Error('Request not found or expired');
            const data = await res.json();
            setRequest(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load request');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchRequest();
    }, [fetchRequest]);

    // When request loads and we have an email action, show the confirmation banner
    useEffect(() => {
        if (
            request &&
            request.status === 'PENDING' &&
            emailAction &&
            (emailAction === 'APPROVED' || emailAction === 'REJECTED') &&
            !successMessage &&
            !pendingEmailAction
        ) {
            setPendingEmailAction(emailAction);
        }
    }, [request, emailAction, successMessage, pendingEmailAction]);

    const handleDecision = async (decision: 'APPROVED' | 'REJECTED') => {
        setProcessing(true);
        setPendingEmailAction(null);
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/approvals/${token}/decision`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ token, decision })
            });

            const data = await res.json();

            if (!data.success) {
                if (data.status === 'EXPIRED') {
                    setRequest(prev => prev ? ({ ...prev, status: 'EXPIRED' }) : null);
                } else {
                    // Already processed
                    setRequest(prev => prev ? ({ ...prev, status: data.status }) : null);
                }
                throw new Error(data.message);
            }

            setSuccessMessage(data.message);
            setRequest(prev => prev ? ({ ...prev, status: decision }) : null);

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Action failed');
        } finally {
            setProcessing(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    if (error && !request) {
        return (
            <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
                <div className="bg-white dark:bg-slate-800 p-8 rounded-2xl shadow-xl max-w-md w-full text-center">
                    <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Unavailable</h2>
                    <p className="text-slate-600 dark:text-slate-400">{error || "This link is invalid or has expired."}</p>
                </div>
            </div>
        );
    }

    if (!request) return null;

    // Extract human-readable description/details from payload
    const payload = request.payload || {};
    const description = typeof payload.description === 'string' ? payload.description : '';
    const details = typeof payload.details === 'string' ? payload.details : '';

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col items-center justify-center p-4">
            {/* Branded header */}
            <motion.div
                initial={{ opacity: 0, y: -16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: [0.21, 0.47, 0.32, 0.98] }}
                className="mb-6 flex items-center gap-3"
            >
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-400 to-violet-500 shadow-lg">
                    <Shield className="h-5 w-5 text-white" />
                </div>
                <span className="text-lg font-semibold text-slate-700 dark:text-slate-200">Pikar AI</span>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: [0.21, 0.47, 0.32, 0.98] }}
            >
            <div className="rounded-[28px] border border-slate-100/80 bg-white dark:bg-slate-800 p-8 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] max-w-lg w-full overflow-hidden">

                {/* Header */}
                <div className="pb-6 mb-6 border-b border-slate-100 dark:border-slate-700">
                    <div className="flex items-center gap-3 mb-1">
                        <div className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></div>
                        <span className="text-xs font-semibold tracking-wider text-indigo-600 dark:text-indigo-400 uppercase">Approval Request</span>
                    </div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                        {request.action_type.replace(/_/g, ' ')}
                    </h1>
                </div>

                {/* Description & Details (from magic link email) */}
                {(description || details) && (
                    <div className="px-6 pb-4 space-y-2">
                        {description && (
                            <p className="text-base font-medium text-slate-800 dark:text-slate-200">{description}</p>
                        )}
                        {details && (
                            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">{details}</p>
                        )}
                    </div>
                )}

                {/* Payload */}
                <div className="p-6 space-y-4">
                    <div className="bg-slate-100 dark:bg-slate-900/50 rounded-xl p-4 font-mono text-sm text-slate-600 dark:text-slate-300 overflow-x-auto">
                        <pre>{JSON.stringify(request.payload, null, 2)}</pre>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span>Expires: {new Date(request.expires_at).toLocaleString()}</span>
                    </div>
                </div>

                {/* Email action confirmation banner */}
                {pendingEmailAction && request.status === 'PENDING' && (
                    <div className={`mx-6 mb-4 p-4 rounded-xl border ${
                        pendingEmailAction === 'APPROVED'
                            ? 'bg-indigo-50 border-indigo-200 dark:bg-indigo-900/20 dark:border-indigo-800'
                            : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                    }`}>
                        <p className={`text-sm font-medium mb-3 ${
                            pendingEmailAction === 'APPROVED'
                                ? 'text-indigo-800 dark:text-indigo-300'
                                : 'text-red-800 dark:text-red-300'
                        }`}>
                            Are you sure you want to <strong>{pendingEmailAction === 'APPROVED' ? 'approve' : 'reject'}</strong> this request?
                        </p>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setPendingEmailAction(null)}
                                className="flex-1 py-2 px-3 rounded-lg text-sm font-medium bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 transition dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleDecision(pendingEmailAction)}
                                disabled={processing}
                                className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold text-white transition disabled:opacity-50 ${
                                    pendingEmailAction === 'APPROVED'
                                        ? 'bg-indigo-600 hover:bg-indigo-700'
                                        : 'bg-red-600 hover:bg-red-700'
                                }`}
                            >
                                {processing ? (
                                    <Loader2 size={16} className="animate-spin inline mr-1" />
                                ) : null}
                                Confirm {pendingEmailAction === 'APPROVED' ? 'Approve' : 'Reject'}
                            </button>
                        </div>
                    </div>
                )}

                {/* Actions */}
                <div className="p-6 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-700">
                    {request.status === 'PENDING' ? (
                        <div className="grid grid-cols-2 gap-4">
                            <button
                                onClick={() => handleDecision('REJECTED')}
                                disabled={processing}
                                className="flex items-center justify-center gap-2 py-3 px-4 rounded-2xl font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-red-600 transition disabled:opacity-50"
                            >
                                <XCircle size={18} />
                                Reject
                            </button>
                            <button
                                onClick={() => handleDecision('APPROVED')}
                                disabled={processing}
                                className="flex items-center justify-center gap-2 py-3 px-4 rounded-2xl font-semibold bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-500/20 transition disabled:opacity-50"
                            >
                                {processing ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle size={18} />}
                                Approve
                            </button>
                        </div>
                    ) : (
                        <div className={`text-center p-4 rounded-xl font-medium flex items-center justify-center gap-2
                    ${request.status === 'APPROVED' ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : ''}
                    ${request.status === 'REJECTED' ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400' : ''}
                    ${request.status === 'EXPIRED' ? 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400' : ''}
                `}>
                            {request.status === 'APPROVED' && <CheckCircle size={20} />}
                            {request.status === 'REJECTED' && <XCircle size={20} />}
                            {request.status === 'EXPIRED' && <AlertTriangle size={20} />}
                            {successMessage || `Request is ${request.status}`}
                        </div>
                    )}

                    {/* Show non-fatal errors (e.g., already processed) alongside the status */}
                    {error && request && (
                        <p className="mt-3 text-center text-sm text-amber-600 dark:text-amber-400">{error}</p>
                    )}
                </div>

            </div>
            </motion.div>
        </div>
    );
}

/**
 * Page component that extracts the token from params and wraps
 * the inner component in Suspense (required for useSearchParams).
 */
export default function ApprovalPage() {
    const { token } = useParams<{ token: string }>();

    return (
        <Suspense fallback={
            <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        }>
            <ApprovalPageInner token={token} />
        </Suspense>
    );
}
