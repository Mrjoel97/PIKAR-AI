'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { createClient } from '@/lib/supabase/client';
import { Loader2, CheckCircle, XCircle, AlertTriangle, Shield } from 'lucide-react';

interface ApprovalRequest {
    id: string;
    action_type: string;
    payload: Record<string, unknown>;
    status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
    expires_at: string;
}

export default function ApprovalPage({ params }: { params: { token: string } }) {
    const [request, setRequest] = useState<ApprovalRequest | null>(null);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const token = params.token; // In App Router, params are passed as props

    useEffect(() => {
        fetchRequest();
    }, [token]);

    const fetchRequest = async () => {
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
    };

    const handleDecision = async (decision: 'APPROVED' | 'REJECTED') => {
        setProcessing(true);
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

    if (error || !request) {
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

                {/* Payload */}
                <div className="p-6 space-y-4">
                    <div className="bg-slate-100 dark:bg-slate-900/50 rounded-xl p-4 font-mono text-sm text-slate-600 dark:text-slate-300 overflow-x-auto">
                        <pre>{JSON.stringify(request.payload, null, 2)}</pre>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span>Expires: {new Date(request.expires_at).toLocaleString()}</span>
                    </div>
                </div>

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
                            Request is {request.status}
                        </div>
                    )}
                </div>

            </div>
            </motion.div>
        </div>
    );
}
