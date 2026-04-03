'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import {
  Bell,
  CheckCircle,
  XCircle,
  Clock,
  ListFilter,
} from 'lucide-react';
import { usePendingApprovals, type PendingApproval } from '@/hooks/usePendingApprovals';
import { GatedPage } from '@/components/dashboard/GatedPage';
import {
  getApprovalHistory,
  submitApprovalDecision,
  type ApprovalHistoryItem,
  type ApprovalDecision,
} from '@/services/approvals';

type TabKey = 'pending' | 'approved' | 'rejected' | 'all';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'all', label: 'All' },
];

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatActionType(actionType: string): string {
  return actionType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ---------- Loading skeleton ---------- */

function LoadingSkeleton() {
  return (
    <PremiumShell>
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex items-center justify-between">
          <div className="h-8 w-48 animate-pulse rounded-xl bg-slate-200" />
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-[28px] bg-slate-100" />
          ))}
        </div>
        <div className="h-12 animate-pulse rounded-xl bg-slate-100" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-[28px] bg-slate-100" />
          ))}
        </div>
      </div>
    </PremiumShell>
  );
}

/* ---------- Pending Approval Card ---------- */

function PendingApprovalCard({
  item,
  onDecision,
  deciding,
}: {
  item: PendingApproval;
  onDecision: (token: string, decision: ApprovalDecision) => void;
  deciding: string | null;
}) {
  const isDeciding = deciding === item.id;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0 space-y-1">
          <p className="font-semibold text-slate-900">
            {formatActionType(item.action_type)}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status="pending" />
            <span className="inline-flex items-center gap-1 text-xs text-slate-500">
              <Clock className="h-3 w-3" />
              {formatRelativeTime(item.created_at)}
            </span>
          </div>
        </div>
        {item.token && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onDecision(item.token!, 'APPROVED')}
              disabled={isDeciding}
              className="inline-flex items-center gap-1.5 rounded-2xl bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-50"
            >
              <CheckCircle className="h-4 w-4" />
              Approve
            </button>
            <button
              onClick={() => onDecision(item.token!, 'REJECTED')}
              disabled={isDeciding}
              className="inline-flex items-center gap-1.5 rounded-2xl bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-100 disabled:opacity-50"
            >
              <XCircle className="h-4 w-4" />
              Reject
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

/* ---------- History Item Card ---------- */

function HistoryItemCard({ item }: { item: ApprovalHistoryItem }) {
  return (
    <div className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0 space-y-1">
          <p className="font-semibold text-slate-900">
            {formatActionType(item.action_type)}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={item.status.toLowerCase()} />
            <span className="inline-flex items-center gap-1 text-xs text-slate-500">
              <Clock className="h-3 w-3" />
              Created {formatRelativeTime(item.created_at)}
            </span>
            {item.responded_at && (
              <span className="text-xs text-slate-400">
                Resolved {formatRelativeTime(item.responded_at)}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Main page ---------- */

export default function ApprovalsPage() {
  const { approvals: pending, isLoading: pendingLoading, refresh } = usePendingApprovals();
  const [history, setHistory] = useState<ApprovalHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>('pending');
  const [deciding, setDeciding] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadHistory() {
      try {
        const data = await getApprovalHistory();
        if (!cancelled) setHistory(data);
      } catch (err) {
        console.error('Failed to load approval history:', err);
      } finally {
        if (!cancelled) setHistoryLoading(false);
      }
    }
    loadHistory();
    return () => { cancelled = true; };
  }, []);

  const handleDecision = useCallback(
    async (token: string, decision: ApprovalDecision) => {
      const item = pending.find((p) => p.token === token);
      if (item) setDeciding(item.id);
      try {
        await submitApprovalDecision(token, decision);
        refresh();
        // Reload history to reflect the change
        const data = await getApprovalHistory();
        setHistory(data);
      } catch (err) {
        console.error('Failed to submit decision:', err);
      } finally {
        setDeciding(null);
      }
    },
    [pending, refresh],
  );

  // KPI computations
  const approved24h = useMemo(() => {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    return history.filter(
      (h) => h.status === 'APPROVED' && h.responded_at && new Date(h.responded_at).getTime() > cutoff,
    ).length;
  }, [history]);

  const rejected24h = useMemo(() => {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    return history.filter(
      (h) => h.status === 'REJECTED' && h.responded_at && new Date(h.responded_at).getTime() > cutoff,
    ).length;
  }, [history]);

  const expiredCount = useMemo(
    () => history.filter((h) => h.status === 'EXPIRED').length,
    [history],
  );

  // Tab-filtered history items
  const filteredHistory = useMemo(() => {
    if (activeTab === 'all') return history;
    return history.filter((h) => h.status === activeTab.toUpperCase());
  }, [history, activeTab]);

  const loading = pendingLoading && historyLoading;
  if (loading) {
    return (
      <DashboardErrorBoundary fallbackTitle="Approvals Error">
        <LoadingSkeleton />
      </DashboardErrorBoundary>
    );
  }

  return (
    <GatedPage featureKey="approvals">
    <DashboardErrorBoundary fallbackTitle="Approvals Error">
      <PremiumShell>
        <motion.div
          className="mx-auto max-w-7xl space-y-8"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
            Approvals
          </h1>

          {/* KPI Row */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard
              label="Pending"
              value={pending.length}
              icon={Bell}
              gradient="from-amber-400 to-orange-500"
              delay={0}
            />
            <MetricCard
              label="Approved (24h)"
              value={approved24h}
              icon={CheckCircle}
              gradient="from-emerald-400 to-green-500"
              delay={0.05}
            />
            <MetricCard
              label="Rejected (24h)"
              value={rejected24h}
              icon={XCircle}
              gradient="from-rose-400 to-red-500"
              delay={0.1}
            />
            <MetricCard
              label="Expired"
              value={expiredCount}
              icon={Clock}
              gradient="from-slate-400 to-slate-500"
              delay={0.15}
            />
          </div>

          {/* Tab Bar */}
          <div className="flex items-center gap-1 rounded-2xl bg-slate-100 p-1">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 rounded-xl px-4 py-2 text-sm font-medium transition ${
                  activeTab === tab.key
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {tab.label}
                {tab.key === 'pending' && pending.length > 0 && (
                  <span className="ml-1.5 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-amber-500 px-1.5 text-[10px] font-bold text-white">
                    {pending.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Content */}
          {activeTab === 'pending' ? (
            <section className="space-y-4">
              <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                Awaiting Your Decision
              </h2>
              {pending.length === 0 ? (
                <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                  <CheckCircle className="mx-auto h-10 w-10 text-emerald-400" />
                  <p className="mt-3 text-sm font-medium text-slate-600">All caught up!</p>
                  <p className="mt-1 text-xs text-slate-400">No pending approvals</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {pending.map((item) => (
                    <PendingApprovalCard
                      key={item.id}
                      item={item}
                      onDecision={handleDecision}
                      deciding={deciding}
                    />
                  ))}
                </div>
              )}
            </section>
          ) : (
            <section className="space-y-4">
              <div className="flex items-center gap-2">
                <ListFilter className="h-4 w-4 text-slate-400" />
                <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                  {activeTab === 'all' ? 'All History' : `${activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Items`}
                </h2>
                <span className="text-xs text-slate-400">({filteredHistory.length})</span>
              </div>
              {filteredHistory.length === 0 ? (
                <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                  <p className="text-sm text-slate-400 italic">No items</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredHistory.map((item) => (
                    <HistoryItemCard key={item.id} item={item} />
                  ))}
                </div>
              )}
            </section>
          )}
        </motion.div>
      </PremiumShell>
    </DashboardErrorBoundary>
    </GatedPage>
  );
}
