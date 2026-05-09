'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * ApprovalCard — inline tappable Approve/Reject card for agent-emitted
 * approval requests.
 *
 * Replaces the bare Magic Link URL the agent used to quote in chat. Posts
 * the user's decision to the existing `/approvals/{token}/decision`
 * endpoint and toasts the outcome. The agent-resume-on-decision flow is
 * tracked under ARTIFACT-04 and is intentionally NOT implemented here —
 * for now the card just disables both buttons and surfaces a "Decision
 * recorded." toast.
 */

import React, { useState } from 'react';
import { CheckCircle2, XCircle, Clock, Shield } from 'lucide-react';
import { toast } from 'sonner';

import type { WidgetProps } from '@/components/widgets/WidgetRegistry';
import type { ApprovalWidgetData } from '@/types/widgets';

type DecisionPayload = 'approve' | 'reject';

function formatDeadline(iso?: string): string | null {
    if (!iso) return null;
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleString();
}

export function ApprovalCard({ definition }: WidgetProps) {
    const data = definition.data as unknown as ApprovalWidgetData;
    const [submitting, setSubmitting] = useState<DecisionPayload | null>(null);
    const [decided, setDecided] = useState<DecisionPayload | null>(null);

    const title =
        definition.title ||
        (data.action_type
            ? data.action_type.replace(/_/g, ' ')
            : 'Approval Request');
    const deadline = formatDeadline(data.requires_response_by);
    const disabled = decided !== null || submitting !== null;

    const submitDecision = async (decision: DecisionPayload) => {
        if (disabled) return;
        setSubmitting(decision);
        try {
            const res = await fetch(data.decision_endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: data.token, decision }),
            });
            if (!res.ok) {
                throw new Error(`Request failed: ${res.status}`);
            }
            setDecided(decision);
            // ARTIFACT-04 will notify the originating agent so the workflow
            // can resume; for now we just acknowledge locally.
            toast.success('Decision recorded.');
        } catch (err) {
            toast.error(
                err instanceof Error ? err.message : 'Failed to submit decision',
            );
        } finally {
            setSubmitting(null);
        }
    };

    return (
        <div
            className="w-full rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden dark:bg-slate-800 dark:border-slate-700"
            data-testid="approval-card"
        >
            <div className="flex items-start gap-3 px-5 py-4 border-b border-slate-100 dark:border-slate-700">
                <span className="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
                    <Shield size={16} />
                </span>
                <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-300">
                        Approval Request
                    </p>
                    <h4
                        className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate"
                        title={title}
                    >
                        {title}
                    </h4>
                    {data.action_type && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            {data.action_type.replace(/_/g, ' ')}
                        </p>
                    )}
                </div>
            </div>

            <div className="px-5 py-4 space-y-3">
                {deadline && (
                    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                        <Clock size={12} />
                        <span>Respond by {deadline}</span>
                    </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                    <button
                        type="button"
                        onClick={() => submitDecision('reject')}
                        disabled={disabled}
                        aria-label="Reject approval request"
                        data-testid="approval-reject"
                        className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition disabled:opacity-50 disabled:cursor-not-allowed dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
                    >
                        <XCircle size={16} />
                        {decided === 'reject' ? 'Rejected' : 'Reject'}
                    </button>
                    <button
                        type="button"
                        onClick={() => submitDecision('approve')}
                        disabled={disabled}
                        aria-label="Approve request"
                        data-testid="approval-approve"
                        className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <CheckCircle2 size={16} />
                        {decided === 'approve' ? 'Approved' : 'Approve'}
                    </button>
                </div>

                {decided && (
                    <p className="text-xs text-slate-500 dark:text-slate-400 text-center">
                        Decision recorded. Agent resume is pending (ARTIFACT-04).
                    </p>
                )}
            </div>
        </div>
    );
}

export default ApprovalCard;
