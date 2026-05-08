// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * ApprovalCard — inline Approve/Reject widget rendered for agent-emitted
 * approval requests.
 *
 * The agent's `request_human_approval` tool emits an `approval` widget
 * envelope; this card surfaces title + action_type + optional deadline and
 * exposes Approve / Reject buttons that POST the user's decision to
 * `data.decision_endpoint`.
 *
 * The callback-resumes-workflow piece (agent receives the decision and
 * continues execution) is ARTIFACT-04 and intentionally NOT wired here.
 */

'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import { CheckCircle2, XCircle, Clock } from 'lucide-react';
import type { WidgetProps } from '@/components/widgets/WidgetRegistry';
import type { ApprovalWidgetData } from '@/types/widgets';

type Decision = 'approve' | 'reject';

function formatDeadline(iso?: string): string | null {
    if (!iso) return null;
    try {
        const dt = new Date(iso);
        if (Number.isNaN(dt.getTime())) return null;
        return dt.toLocaleString();
    } catch {
        return null;
    }
}

export default function ApprovalCard({ definition }: WidgetProps) {
    const data = definition.data as unknown as ApprovalWidgetData;
    const [submitting, setSubmitting] = useState(false);
    const [decided, setDecided] = useState<Decision | null>(null);

    const title =
        definition.title ||
        `Approval required: ${data?.action_type ?? 'action'}`;
    const deadline = formatDeadline(data?.requires_response_by);

    const handleDecision = async (decision: Decision) => {
        if (submitting || decided) return;
        if (!data?.decision_endpoint || !data?.token) {
            toast.error('Approval card is missing token or endpoint.');
            return;
        }
        setSubmitting(true);
        try {
            const url = data.base_url
                ? `${data.base_url.replace(/\/$/, '')}${data.decision_endpoint}`
                : data.decision_endpoint;
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: data.token,
                    decision,
                }),
            });
            if (!res.ok) {
                const detail = await res.text().catch(() => '');
                throw new Error(detail || `HTTP ${res.status}`);
            }
            setDecided(decision);
            if (decision === 'approve') {
                toast.success('Approved.');
            } else {
                toast.success('Rejected.');
            }
        } catch (err) {
            toast.error(
                err instanceof Error
                    ? `Failed to submit decision: ${err.message}`
                    : 'Failed to submit decision.',
            );
        } finally {
            setSubmitting(false);
        }
    };

    const isDisabled = submitting || decided !== null;

    return (
        <div
            data-testid="approval-card"
            className="w-full rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 shadow-sm"
        >
            <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {title}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        Action type:{' '}
                        <span className="font-mono text-slate-700 dark:text-slate-300">
                            {data?.action_type ?? 'unknown'}
                        </span>
                    </p>
                    {deadline && (
                        <p className="mt-1 flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                            <Clock className="w-3 h-3" />
                            <span>
                                Respond by{' '}
                                <span className="text-slate-700 dark:text-slate-300">
                                    {deadline}
                                </span>
                            </span>
                        </p>
                    )}
                </div>
            </div>

            <div className="mt-4 flex items-center gap-2">
                <button
                    type="button"
                    onClick={() => handleDecision('approve')}
                    disabled={isDisabled}
                    aria-label="Approve"
                    className="inline-flex items-center gap-1.5 rounded-2xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    <CheckCircle2 className="w-4 h-4" />
                    {decided === 'approve' ? 'Approved' : 'Approve'}
                </button>
                <button
                    type="button"
                    onClick={() => handleDecision('reject')}
                    disabled={isDisabled}
                    aria-label="Reject"
                    className="inline-flex items-center gap-1.5 rounded-2xl bg-slate-200 px-4 py-2 text-sm font-medium text-slate-800 shadow-sm transition-colors hover:bg-slate-300 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600"
                >
                    <XCircle className="w-4 h-4" />
                    {decided === 'reject' ? 'Rejected' : 'Reject'}
                </button>
            </div>
        </div>
    );
}
