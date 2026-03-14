'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { usePersona } from '@/contexts/PersonaContext';
import { type PersonaType } from '@/services/onboarding';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import {
  ShieldCheck,
  AlertTriangle,
  Calendar,
  CheckCircle,
  Clock,
} from 'lucide-react';
import {
  getAudits,
  getRisks,
  computeComplianceScore,
  type ComplianceAudit,
  type ComplianceRisk,
} from '@/services/compliance';

function getTitle(persona: PersonaType | null): string {
  switch (persona) {
    case 'enterprise':
      return 'Compliance & Risk';
    case 'sme':
      return 'Operational Compliance';
    default:
      return 'Risk Overview';
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/* ---------- Severity bar ---------- */

interface SeverityCounts {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

function SeverityBar({ counts }: { counts: SeverityCounts }) {
  const total = counts.low + counts.medium + counts.high + counts.critical;

  if (total === 0) {
    return (
      <p className="text-sm text-slate-400 italic">No open risks</p>
    );
  }

  const segments: { key: keyof SeverityCounts; color: string; label: string }[] = [
    { key: 'low', color: 'bg-green-500', label: 'Low' },
    { key: 'medium', color: 'bg-amber-500', label: 'Medium' },
    { key: 'high', color: 'bg-orange-500', label: 'High' },
    { key: 'critical', color: 'bg-red-500', label: 'Critical' },
  ];

  return (
    <div>
      <div className="flex h-5 w-full overflow-hidden rounded-full">
        {segments.map(
          (seg) =>
            counts[seg.key] > 0 && (
              <div
                key={seg.key}
                className={`${seg.color} transition-all`}
                style={{ width: `${(counts[seg.key] / total) * 100}%` }}
              />
            ),
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-4">
        {segments.map((seg) => (
          <span key={seg.key} className="inline-flex items-center gap-1.5 text-xs text-slate-600">
            <span className={`inline-block h-2.5 w-2.5 rounded-full ${seg.color}`} />
            {seg.label}: {counts[seg.key]}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ---------- Loading skeleton ---------- */

function LoadingSkeleton() {
  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="h-8 w-56 animate-pulse rounded-lg bg-slate-200" />
        <div className="h-10 w-36 animate-pulse rounded-lg bg-slate-200" />
      </div>
      {/* KPI row skeleton */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-2xl bg-slate-100" />
        ))}
      </div>
      {/* Severity bar skeleton */}
      <div className="h-24 animate-pulse rounded-2xl bg-slate-100" />
      {/* Two columns skeleton */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100" />
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100" />
      </div>
    </div>
  );
}

/* ---------- Main page ---------- */

export default function CompliancePage() {
  const { persona } = usePersona();
  const isSimplified = persona === 'solopreneur' || persona === 'startup';

  const [audits, setAudits] = useState<ComplianceAudit[]>([]);
  const [risks, setRisks] = useState<ComplianceRisk[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [a, r] = await Promise.all([getAudits(), getRisks()]);
        if (!cancelled) {
          setAudits(a);
          setRisks(r);
        }
      } catch (err) {
        console.error('Failed to load compliance data:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const complianceScore = useMemo(() => computeComplianceScore(audits), [audits]);

  const openRisks = risks.length;
  const scheduledAudits = useMemo(
    () => audits.filter((a) => a.status === 'scheduled').length,
    [audits],
  );
  const completedAudits = useMemo(
    () => audits.filter((a) => a.status === 'completed').length,
    [audits],
  );

  const severityCounts = useMemo<SeverityCounts>(() => {
    const counts: SeverityCounts = { low: 0, medium: 0, high: 0, critical: 0 };
    for (const r of risks) {
      const sev = r.severity?.toLowerCase() as keyof SeverityCounts;
      if (sev in counts) counts[sev]++;
    }
    return counts;
  }, [risks]);

  const activeAudits = useMemo(
    () => audits.filter((a) => a.status !== 'completed' && a.status !== 'cancelled'),
    [audits],
  );

  if (loading) return <LoadingSkeleton />;

  return (
    <div className="mx-auto max-w-7xl space-y-8 bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">
          {getTitle(persona as PersonaType | null)}
        </h1>
        <Link
          href="/dashboard/command-center"
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-teal-700"
        >
          <ShieldCheck className="h-4 w-4" />
          Run GDPR Audit
        </Link>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard
          label="Compliance Score"
          value={`${complianceScore}%`}
          icon={ShieldCheck}
          color="text-teal-600"
          bg="bg-teal-50"
        />
        <MetricCard
          label="Open Risks"
          value={openRisks}
          icon={AlertTriangle}
          color="text-red-600"
          bg="bg-red-50"
        />
        <MetricCard
          label="Scheduled Audits"
          value={scheduledAudits}
          icon={Calendar}
          color="text-blue-600"
          bg="bg-blue-50"
        />
        <MetricCard
          label="Completed Audits"
          value={completedAudits}
          icon={CheckCircle}
          color="text-emerald-600"
          bg="bg-emerald-50"
        />
      </div>

      {/* Risk Severity Distribution */}
      <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Risk Severity Distribution
        </h2>
        <SeverityBar counts={severityCounts} />
      </section>

      {/* Two-column grid: Active Audits + Open Risks */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Active Audits */}
        <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Active Audits
          </h2>
          {activeAudits.length === 0 ? (
            <p className="text-sm text-slate-400 italic">No active audits</p>
          ) : (
            <div className="relative ml-4 border-l-2 border-slate-200 pl-6 space-y-6">
              {activeAudits.map((audit) => (
                <div key={audit.id} className="relative">
                  {/* Connector dot */}
                  <span className="absolute -left-[31px] top-1 h-3 w-3 rounded-full border-2 border-white bg-teal-500" />
                  <div className="space-y-1">
                    <p className="font-semibold text-slate-900">{audit.title}</p>
                    {audit.scope && (
                      <p className="text-sm text-slate-500">{audit.scope}</p>
                    )}
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={audit.status} />
                      <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                        <Clock className="h-3 w-3" />
                        {formatDate(audit.scheduled_date)}
                      </span>
                    </div>
                    {audit.auditor && (
                      <p className="text-xs text-slate-500">Auditor: {audit.auditor}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Open Risks */}
        <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Open Risks
          </h2>
          {risks.length === 0 ? (
            <p className="text-sm text-slate-400 italic">No open risks</p>
          ) : (
            <div className="space-y-4">
              {risks.map((risk) => (
                <div
                  key={risk.id}
                  className="rounded-xl border border-slate-100 p-4 space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-semibold text-slate-900">{risk.title}</p>
                    <StatusBadge status={risk.severity} />
                  </div>

                  {isSimplified ? (
                    /* Simplified view for solopreneur / startup */
                    <StatusBadge status={risk.status} variant="dot" />
                  ) : (
                    /* Full view for sme / enterprise */
                    <>
                      {risk.description && (
                        <p className="text-sm text-slate-600 line-clamp-2">
                          {risk.description}
                        </p>
                      )}
                      {risk.mitigation_plan && (
                        <p className="text-xs text-slate-500 line-clamp-1">
                          <span className="font-medium">Mitigation:</span>{' '}
                          {risk.mitigation_plan}
                        </p>
                      )}
                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                        <StatusBadge status={risk.status} variant="dot" />
                        {risk.owner && <span>Owner: {risk.owner}</span>}
                        {risk.due_date && (
                          <span className="inline-flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDate(risk.due_date)}
                          </span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
