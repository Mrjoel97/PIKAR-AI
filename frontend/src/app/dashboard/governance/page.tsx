'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import {
  Shield,
  Activity,
  CheckCircle,
  Clock,
  AlertTriangle,
  FileText,
  Users,
} from 'lucide-react';
import {
  getAuditLog,
  getPortfolioHealth,
  getApprovalChains,
  type AuditLogEntry,
  type PortfolioHealth,
  type ApprovalChain,
} from '@/services/governance';
import {
  getAudits,
  getRisks,
  computeComplianceScore,
  type ComplianceAudit,
  type ComplianceRisk,
} from '@/services/compliance';
import { GatedPage } from '@/components/dashboard/GatedPage';

// ============================================================================
// Helpers
// ============================================================================

const ACTION_TYPE_LABELS: Record<string, string> = {
  'initiative.created': 'Initiative Created',
  'initiative.deleted': 'Initiative Deleted',
  'workflow.executed': 'Workflow Executed',
  'role.changed': 'Role Changed',
  'approval.decided': 'Approval Decision',
  'member.joined': 'Member Joined',
  'member.removed': 'Member Removed',
};

function formatActionType(actionType: string): string {
  return (
    ACTION_TYPE_LABELS[actionType] ??
    actionType
      .split('.')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  );
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function healthColor(score: number): string {
  if (score >= 70) return 'text-emerald-600';
  if (score >= 40) return 'text-amber-500';
  return 'text-red-500';
}

function healthBg(score: number): string {
  if (score >= 70) return 'bg-emerald-50';
  if (score >= 40) return 'bg-amber-50';
  return 'bg-red-50';
}

function healthGradient(score: number): string {
  if (score >= 70) return 'from-emerald-400 to-teal-500';
  if (score >= 40) return 'from-amber-400 to-orange-400';
  return 'from-rose-400 to-red-500';
}

const ACTION_TYPE_OPTIONS = [
  '',
  'initiative.created',
  'initiative.deleted',
  'workflow.executed',
  'role.changed',
  'approval.decided',
  'member.joined',
  'member.removed',
];

// ============================================================================
// Sub-components
// ============================================================================

function HealthComponentBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(value)));
  const barColor =
    pct >= 70 ? 'bg-emerald-400' : pct >= 40 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{label}</span>
        <span className="font-medium text-slate-700">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

interface StepIndicatorProps {
  status: 'pending' | 'approved' | 'rejected' | 'skipped';
}

function StepIndicator({ status }: StepIndicatorProps) {
  if (status === 'approved') {
    return <CheckCircle className="h-4 w-4 flex-shrink-0 text-emerald-500" />;
  }
  if (status === 'rejected') {
    return <AlertTriangle className="h-4 w-4 flex-shrink-0 text-red-500" />;
  }
  if (status === 'skipped') {
    return <span className="inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full bg-slate-300" />;
  }
  // pending
  return <span className="inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full bg-amber-400" />;
}

// ============================================================================
// Loading skeleton
// ============================================================================

function LoadingSkeleton() {
  return (
    <PremiumShell>
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="h-8 w-64 animate-pulse rounded-xl bg-slate-200" />
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="h-48 animate-pulse rounded-[28px] bg-slate-100" />
          <div className="h-48 animate-pulse rounded-[28px] bg-slate-100" />
        </div>
        <div className="h-40 animate-pulse rounded-[28px] bg-slate-100" />
        <div className="h-64 animate-pulse rounded-[28px] bg-slate-100" />
      </div>
    </PremiumShell>
  );
}

// ============================================================================
// Main page
// ============================================================================

export default function GovernancePage() {
  // Portfolio health state
  const [health, setHealth] = useState<PortfolioHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Compliance state
  const [audits, setAudits] = useState<ComplianceAudit[]>([]);
  const [risks, setRisks] = useState<ComplianceRisk[]>([]);
  const [complianceError, setComplianceError] = useState<string | null>(null);

  // Approval chains state
  const [chains, setChains] = useState<ApprovalChain[]>([]);
  const [chainsError, setChainsError] = useState<string | null>(null);

  // Audit log state
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [auditLogOffset, setAuditLogOffset] = useState(0);
  const [auditLogLoading, setAuditLogLoading] = useState(false);
  const [auditLogError, setAuditLogError] = useState<string | null>(null);
  const [auditLogFilter, setAuditLogFilter] = useState('');
  const [hasMore, setHasMore] = useState(true);

  // Global loading — only on initial mount
  const [loading, setLoading] = useState(true);

  // Initial data load
  useEffect(() => {
    let cancelled = false;

    async function loadInitial() {
      try {
        const [healthData, auditsData, risksData, chainsData, logData] = await Promise.allSettled([
          getPortfolioHealth(),
          getAudits(),
          getRisks(),
          getApprovalChains(),
          getAuditLog(50, 0),
        ]);

        if (cancelled) return;

        if (healthData.status === 'fulfilled') {
          setHealth(healthData.value);
        } else {
          setHealthError('Failed to load portfolio health');
        }

        if (auditsData.status === 'fulfilled' && risksData.status === 'fulfilled') {
          setAudits(auditsData.value);
          setRisks(risksData.value);
        } else {
          setComplianceError('Failed to load compliance data');
        }

        if (chainsData.status === 'fulfilled') {
          setChains(chainsData.value);
        } else {
          setChainsError('Failed to load approval chains');
        }

        if (logData.status === 'fulfilled') {
          setAuditLog(logData.value);
          setHasMore(logData.value.length === 50);
        } else {
          setAuditLogError('Failed to load audit log');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadInitial();
    return () => {
      cancelled = true;
    };
  }, []);

  // Load more audit log entries
  async function loadMoreAuditLog() {
    setAuditLogLoading(true);
    try {
      const newOffset = auditLogOffset + 50;
      const entries = await getAuditLog(50, newOffset, auditLogFilter || undefined);
      setAuditLog((prev) => [...prev, ...entries]);
      setAuditLogOffset(newOffset);
      setHasMore(entries.length === 50);
    } catch {
      setAuditLogError('Failed to load more entries');
    } finally {
      setAuditLogLoading(false);
    }
  }

  // Re-fetch audit log when filter changes
  useEffect(() => {
    if (loading) return; // skip during initial load
    let cancelled = false;

    async function reloadLog() {
      setAuditLogLoading(true);
      setAuditLogError(null);
      try {
        const entries = await getAuditLog(50, 0, auditLogFilter || undefined);
        if (!cancelled) {
          setAuditLog(entries);
          setAuditLogOffset(0);
          setHasMore(entries.length === 50);
        }
      } catch {
        if (!cancelled) setAuditLogError('Failed to reload audit log');
      } finally {
        if (!cancelled) setAuditLogLoading(false);
      }
    }

    reloadLog();
    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auditLogFilter]);

  const complianceScore = useMemo(() => computeComplianceScore(audits), [audits]);
  const openRisksCount = risks.length;
  const completedAudits = useMemo(
    () => audits.filter((a) => a.status === 'completed').length,
    [audits],
  );
  const pendingChains = useMemo(
    () => chains.filter((c) => c.status === 'pending'),
    [chains],
  );

  if (loading) {
    return (
      <DashboardErrorBoundary fallbackTitle="Governance Error">
        <LoadingSkeleton />
      </DashboardErrorBoundary>
    );
  }

  return (
    <GatedPage featureKey="governance">
      <DashboardErrorBoundary fallbackTitle="Governance Error">
        <PremiumShell>
          <motion.div
            className="mx-auto max-w-7xl space-y-8"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Header */}
            <div className="flex items-center gap-3">
              <Shield className="h-7 w-7 text-indigo-600" />
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                Enterprise Governance
              </h1>
            </div>

            {/* Top row: Portfolio Health + Compliance Status */}
            <div className="grid gap-6 lg:grid-cols-2">

              {/* Portfolio Health */}
              <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                  Portfolio Health
                </h2>
                {healthError ? (
                  <p className="text-sm text-red-500 italic">{healthError}</p>
                ) : health === null ? (
                  <p className="text-sm text-slate-400 italic">No data available</p>
                ) : (
                  <div className="space-y-4">
                    {/* Score display */}
                    <div className="flex items-center gap-4">
                      <div
                        className={`flex h-20 w-20 flex-shrink-0 items-center justify-center rounded-full ${healthBg(health.score)} border-4 ${health.score >= 70 ? 'border-emerald-200' : health.score >= 40 ? 'border-amber-200' : 'border-red-200'}`}
                      >
                        <span className={`text-2xl font-bold ${healthColor(health.score)}`}>
                          {health.score}
                        </span>
                      </div>
                      <div>
                        <p className={`text-lg font-semibold ${healthColor(health.score)}`}>
                          {health.score >= 70
                            ? 'Healthy'
                            : health.score >= 40
                              ? 'Needs Attention'
                              : 'At Risk'}
                        </p>
                        <p className="text-xs text-slate-400">Overall portfolio score / 100</p>
                      </div>
                    </div>
                    {/* Component bars */}
                    <div className="space-y-3">
                      <HealthComponentBar
                        label="Initiative Completion"
                        value={health.components.initiative_completion}
                      />
                      <HealthComponentBar
                        label="Risk Coverage"
                        value={health.components.risk_coverage}
                      />
                      <HealthComponentBar
                        label="Resource Allocation"
                        value={health.components.resource_allocation}
                      />
                    </div>
                  </div>
                )}
              </section>

              {/* Compliance Status Summary */}
              <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                  Compliance Status
                </h2>
                {complianceError ? (
                  <p className="text-sm text-red-500 italic">{complianceError}</p>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    <MetricCard
                      label="Compliance Score"
                      value={`${complianceScore}%`}
                      icon={Shield}
                      gradient={
                        complianceScore >= 70
                          ? 'from-emerald-400 to-teal-500'
                          : 'from-amber-400 to-orange-400'
                      }
                      delay={0}
                    />
                    <MetricCard
                      label="Total Audits"
                      value={audits.length}
                      icon={FileText}
                      gradient="from-sky-400 to-blue-500"
                      delay={0.05}
                    />
                    <MetricCard
                      label="Completed"
                      value={completedAudits}
                      icon={CheckCircle}
                      gradient="from-emerald-400 to-green-500"
                      delay={0.1}
                    />
                    <MetricCard
                      label="Open Risks"
                      value={openRisksCount}
                      icon={AlertTriangle}
                      gradient="from-rose-400 to-red-500"
                      delay={0.15}
                    />
                  </div>
                )}
              </section>
            </div>

            {/* Pending Approval Chains */}
            <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
              <div className="mb-4 flex items-center gap-2">
                <Users className="h-4 w-4 text-indigo-500" />
                <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                  Pending Approval Chains
                </h2>
                {pendingChains.length > 0 && (
                  <span className="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
                    {pendingChains.length}
                  </span>
                )}
              </div>
              {chainsError ? (
                <p className="text-sm text-red-500 italic">{chainsError}</p>
              ) : pendingChains.length === 0 ? (
                <p className="text-sm text-slate-400 italic">No pending approval chains</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                        <th className="pb-3 pr-4">Action</th>
                        <th className="pb-3 pr-4">Resource</th>
                        <th className="pb-3 pr-4">Status</th>
                        <th className="pb-3 pr-4">Steps</th>
                        <th className="pb-3">Created</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {pendingChains.map((chain) => {
                        const currentStep = chain.steps.find((s) => s.status === 'pending');
                        const approvedCount = chain.steps.filter(
                          (s) => s.status === 'approved',
                        ).length;
                        return (
                          <tr key={chain.id} className="transition-colors hover:bg-slate-50/60">
                            <td className="py-3 pr-4 font-medium text-slate-800">
                              {formatActionType(chain.action_type)}
                            </td>
                            <td className="py-3 pr-4 text-slate-600">
                              {chain.resource_label ?? chain.resource_id ?? '--'}
                            </td>
                            <td className="py-3 pr-4">
                              <StatusBadge status={chain.status} />
                            </td>
                            <td className="py-3 pr-4">
                              <div className="flex items-center gap-1.5">
                                {chain.steps.map((step) => (
                                  <StepIndicator key={step.id} status={step.status} />
                                ))}
                                {currentStep && (
                                  <span className="ml-1 text-xs text-slate-500">
                                    Step {approvedCount + 1} of {chain.steps.length} —{' '}
                                    {currentStep.role_label}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="py-3 text-xs text-slate-500">
                              {formatDateTime(chain.created_at)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Audit Log */}
            <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-indigo-500" />
                  <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                    Audit Log
                  </h2>
                </div>
                {/* Filter */}
                <select
                  value={auditLogFilter}
                  onChange={(e) => setAuditLogFilter(e.target.value)}
                  className="ml-auto rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                >
                  <option value="">All Actions</option>
                  {ACTION_TYPE_OPTIONS.filter(Boolean).map((opt) => (
                    <option key={opt} value={opt}>
                      {formatActionType(opt)}
                    </option>
                  ))}
                </select>
              </div>

              {auditLogError ? (
                <p className="text-sm text-red-500 italic">{auditLogError}</p>
              ) : auditLog.length === 0 && !auditLogLoading ? (
                <p className="text-sm text-slate-400 italic">No audit log entries found</p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                          <th className="pb-3 pr-4">Timestamp</th>
                          <th className="pb-3 pr-4">Action</th>
                          <th className="pb-3 pr-4">Resource</th>
                          <th className="pb-3">Details</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {auditLog.map((entry) => (
                          <AuditRow key={entry.id} entry={entry} />
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {hasMore && (
                    <div className="mt-4 flex justify-center">
                      <button
                        onClick={loadMoreAuditLog}
                        disabled={auditLogLoading}
                        className="inline-flex items-center gap-2 rounded-2xl bg-indigo-50 px-5 py-2 text-sm font-medium text-indigo-700 transition hover:bg-indigo-100 disabled:opacity-50"
                      >
                        {auditLogLoading ? (
                          <>
                            <Clock className="h-4 w-4 animate-spin" />
                            Loading...
                          </>
                        ) : (
                          'Load More'
                        )}
                      </button>
                    </div>
                  )}
                </>
              )}
            </section>
          </motion.div>
        </PremiumShell>
      </DashboardErrorBoundary>
    </GatedPage>
  );
}

// ============================================================================
// Audit row (separate component to isolate expand state)
// ============================================================================

function AuditRow({ entry }: { entry: AuditLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = Object.keys(entry.details).length > 0;

  return (
    <>
      <tr className="transition-colors hover:bg-slate-50/60">
        <td className="py-3 pr-4 text-xs text-slate-500 whitespace-nowrap">
          {new Date(entry.created_at).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </td>
        <td className="py-3 pr-4 font-medium text-slate-800">
          {formatActionType(entry.action_type)}
        </td>
        <td className="py-3 pr-4 text-slate-600">
          <span className="font-medium">{entry.resource_type}</span>
          {entry.resource_id && (
            <span className="ml-1 text-xs text-slate-400">#{entry.resource_id.slice(0, 8)}</span>
          )}
        </td>
        <td className="py-3">
          {hasDetails ? (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-200"
            >
              {expanded ? 'Hide' : 'View'}
            </button>
          ) : (
            <span className="text-xs text-slate-300 italic">—</span>
          )}
        </td>
      </tr>
      {expanded && hasDetails && (
        <tr>
          <td colSpan={4} className="pb-3 pl-2 pr-4">
            <pre className="overflow-x-auto rounded-xl bg-slate-50 p-3 text-xs text-slate-700">
              {JSON.stringify(entry.details, null, 2)}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}
