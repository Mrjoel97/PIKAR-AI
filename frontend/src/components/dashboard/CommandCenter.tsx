'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  BrainCircuit,
  Building2,
  CheckCircle2,
  ClipboardList,
  Clock3,
  FileText,
  FolderKanban,
  Map,
  PlusCircle,
  Rocket,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Wallet,
  Zap,
} from 'lucide-react';
import { PersonaType } from '@/services/onboarding';
import { DashboardListItem, DashboardSummary, getDashboardSummary } from '@/services/dashboard';
import { DashboardBriefCard } from '@/components/dashboard/DashboardBriefCard';

interface CommandCenterProps {
  user: { id?: string };
  persona: PersonaType;
}

type LaunchCard = {
  title: string;
  description: string;
  href: string;
  icon: React.ReactNode;
  accent: string;
};

const PERSONA_LAUNCHPADS: Record<PersonaType, LaunchCard[]> = {
  solopreneur: [
    { title: 'Brain Dump', description: 'Capture the next idea while it is hot.', href: '/dashboard/braindump', icon: <BrainCircuit size={18} />, accent: 'from-amber-400 to-orange-500' },
    { title: 'Create Initiative', description: 'Turn a loose idea into committed work.', href: '/dashboard/initiatives/new', icon: <PlusCircle size={18} />, accent: 'from-emerald-400 to-teal-500' },
    { title: 'Workflow Templates', description: 'Start from proven execution patterns.', href: '/dashboard/workflows/templates', icon: <FileText size={18} />, accent: 'from-sky-400 to-blue-500' },
    { title: 'Active Workflows', description: 'Finish what is already moving.', href: '/dashboard/workflows/active', icon: <Clock3 size={18} />, accent: 'from-rose-400 to-red-500' },
  ],
  startup: [
    { title: 'Workflow Templates', description: 'Ship the next experiment faster.', href: '/dashboard/workflows/templates', icon: <Zap size={18} />, accent: 'from-indigo-400 to-violet-500' },
    { title: 'User Journeys', description: 'Map growth friction and handoffs.', href: '/dashboard/journeys', icon: <Map size={18} />, accent: 'from-fuchsia-400 to-pink-500' },
    { title: 'Create Initiative', description: 'Push a launch, bet, or roadmap item.', href: '/dashboard/initiatives/new', icon: <Rocket size={18} />, accent: 'from-emerald-400 to-teal-500' },
    { title: 'Workflow Generator', description: 'Draft a custom growth workflow.', href: '/dashboard/workflows/generate', icon: <Sparkles size={18} />, accent: 'from-cyan-400 to-blue-500' },
  ],
  sme: [
    { title: 'Departments', description: 'Check cross-team ownership and follow-up.', href: '/departments', icon: <Building2 size={18} />, accent: 'from-slate-400 to-slate-600' },
    { title: 'Reports', description: 'Review reporting and operating cadence.', href: '/dashboard/reports', icon: <ClipboardList size={18} />, accent: 'from-blue-400 to-cyan-500' },
    { title: 'Workflow Templates', description: 'Standardize recurring operational flows.', href: '/dashboard/workflows/templates', icon: <FileText size={18} />, accent: 'from-emerald-400 to-lime-500' },
    { title: 'Active Workflows', description: 'Track approvals and execution status.', href: '/dashboard/workflows/active', icon: <Clock3 size={18} />, accent: 'from-amber-400 to-orange-500' },
  ],
  enterprise: [
    { title: 'Active Workflows', description: 'Monitor controlled execution across teams.', href: '/dashboard/workflows/active', icon: <ShieldCheck size={18} />, accent: 'from-slate-500 to-slate-700' },
    { title: 'Reports', description: 'Open stakeholder-safe summaries and outputs.', href: '/dashboard/reports', icon: <ClipboardList size={18} />, accent: 'from-sky-400 to-blue-600' },
    { title: 'Workflow Templates', description: 'Review governed workflow inventory.', href: '/dashboard/workflows/templates', icon: <FolderKanban size={18} />, accent: 'from-violet-400 to-indigo-600' },
    { title: 'History', description: 'Inspect prior work and executive context.', href: '/dashboard/history', icon: <CheckCircle2 size={18} />, accent: 'from-emerald-500 to-teal-600' },
  ],
};

function formatTimestamp(value?: string): string {
  if (!value) {
    return 'Updated recently';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Updated recently';
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function DashboardSection({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[28px] border border-slate-200/80 bg-white/95 p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
      <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">{eyebrow}</p>
      <h2 className="mt-2 text-xl font-semibold text-slate-900">{title}</h2>
      <div className="mt-5 space-y-3">{children}</div>
    </section>
  );
}

function ListItem({
  item,
  onClick,
  meta,
}: {
  item: DashboardListItem;
  onClick?: () => void;
  meta: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-slate-50/90 px-4 py-3 text-left transition hover:border-slate-300 hover:bg-white"
    >
      <div>
        <p className="text-sm font-semibold text-slate-800">{item.title}</p>
        <p className="mt-1 text-xs text-slate-500">{meta}</p>
      </div>
      <ArrowRight size={16} className="text-slate-300" />
    </button>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
      {message}
    </div>
  );
}

export function CommandCenter({ user: _user, persona }: CommandCenterProps) {
  const router = useRouter();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSummary(null);
    getDashboardSummary()
      .then((data) => {
        if (!cancelled) {
          setSummary(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load dashboard');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [persona, reloadKey]);

  const launchpad = PERSONA_LAUNCHPADS[persona];
  const isTimeoutError = (error ?? '').toLowerCase().includes('timed out');

  const collection = summary?.collections;

  const openRoute = (href: string) => router.push(href);

  const renderFounderBoard = () => {
    if (!summary || !collection) {
      return null;
    }

    if (persona === 'solopreneur') {
      return (
        <div className="grid gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-[1.25fr_0.95fr]">
          <DashboardSection eyebrow="Execution" title="Immediate focus">
            {collection.initiatives.length > 0 ? collection.initiatives.slice(0, 4).map((item) => (
              <ListItem
                key={item.id}
                item={item}
                onClick={() => openRoute(`/dashboard/initiatives/${item.id}`)}
                meta={`${item.phase || 'ideation'} · ${item.progress ?? 0}% complete`}
              />
            )) : <EmptyState message="No active initiatives yet. Start from Brain Dump or create one from a template." />}
          </DashboardSection>
          <div className="space-y-6">
            <DashboardSection eyebrow="Tasks" title="Quick tasks">
              {collection.tasks.length > 0 ? collection.tasks.slice(0, 4).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workspace')} meta={`${item.status || 'pending'} · ${formatTimestamp(item.created_at)}`} />
              )) : <EmptyState message="No open tasks right now. The next captured idea can become today’s action list." />}
            </DashboardSection>
            <DashboardSection eyebrow="Momentum" title="Content and brain dumps">
              {collection.content_queue.length > 0 ? collection.content_queue.slice(0, 2).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/reports')} meta={`${item.category || 'Content'} · ${formatTimestamp(item.created_at)}`} />
              )) : null}
              {collection.brain_dumps.length > 0 ? collection.brain_dumps.slice(0, 2).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute(`/dashboard/workspace?braindump_id=${item.id}`)} meta={`${item.category || 'Brain Dump'} · ${formatTimestamp(item.created_at)}`} />
              )) : null}
              {collection.content_queue.length === 0 && collection.brain_dumps.length === 0 ? (
                <EmptyState message="Nothing is queued here yet. Use Brain Dump to capture and continue your next revenue move." />
              ) : null}
            </DashboardSection>
          </div>
        </div>
      );
    }

    if (persona === 'startup') {
      return (
        <div className="grid gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-[1.1fr_0.9fr]">
          <DashboardSection eyebrow="Growth board" title="Initiatives and launches">
            {collection.initiatives.length > 0 ? collection.initiatives.slice(0, 4).map((item) => (
              <ListItem
                key={item.id}
                item={item}
                onClick={() => openRoute(`/dashboard/initiatives/${item.id}`)}
                meta={`${item.phase || 'ideation'} · ${item.progress ?? 0}% complete`}
              />
            )) : <EmptyState message="No active startup initiatives yet. Create one to anchor your next experiment or launch." />}
          </DashboardSection>
          <div className="space-y-6">
            <DashboardSection eyebrow="Throughput" title="Workflow velocity">
              {collection.workflows.length > 0 ? collection.workflows.slice(0, 4).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workflows/active')} meta={`${item.status || 'running'} · ${formatTimestamp(item.updated_at)}`} />
              )) : <EmptyState message="No active workflows right now. Spin up a template to keep launches and experiments moving." />}
            </DashboardSection>
            <DashboardSection eyebrow="Coordination" title="Approval queue">
              {collection.approvals.length > 0 ? collection.approvals.slice(0, 4).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workflows/active')} meta={`Waiting since ${formatTimestamp(item.created_at)}`} />
              )) : <EmptyState message="Nothing is blocked by approvals right now. That is runway-positive." />}
            </DashboardSection>
          </div>
        </div>
      );
    }

    if (persona === 'sme') {
      return (
        <div className="grid gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-[1.08fr_0.92fr]">
          <DashboardSection eyebrow="Operations" title="Department health and follow-up">
            {collection.departments.length > 0 ? collection.departments.slice(0, 3).map((item) => (
              <ListItem key={item.id} item={item} onClick={() => openRoute('/departments')} meta={`${item.category || 'Department'} · ${item.status || 'PAUSED'} · ${formatTimestamp(item.updated_at)}`} />
            )) : null}
            {collection.tasks.length > 0 ? collection.tasks.slice(0, 2).map((item) => (
              <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workspace')} meta={`${item.status || 'pending'} · ${formatTimestamp(item.created_at)}`} />
            )) : null}
            {collection.departments.length === 0 && collection.tasks.length === 0 ? <EmptyState message="No operational follow-ups are open. Use workflows to standardize recurring work before it slips." /> : null}
          </DashboardSection>
          <div className="space-y-6">
            <DashboardSection eyebrow="Controls" title="Compliance and risk summary">
              {collection.audits.length > 0 ? collection.audits.slice(0, 2).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/reports')} meta={`${item.status || 'scheduled'} · ${item.category || 'Audit'} · ${formatTimestamp(item.created_at)}`} />
              )) : null}
              {collection.risks.length > 0 ? collection.risks.slice(0, 2).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workspace')} meta={`${item.summary || item.category || 'Risk'} · ${formatTimestamp(item.created_at)}`} />
              )) : null}
              {collection.approvals.length > 0 ? collection.approvals.slice(0, 1).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workflows/active')} meta={`Pending since ${formatTimestamp(item.created_at)}`} />
              )) : null}
              {collection.audits.length === 0 && collection.risks.length === 0 && collection.approvals.length === 0 ? <EmptyState message="No control signals are open. This space will track audits, risks, and approvals as operations scale." /> : null}
            </DashboardSection>
            <DashboardSection eyebrow="Reports" title="Recurring reporting">
              {collection.reports.length > 0 ? collection.reports.slice(0, 4).map((item) => (
                <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/reports')} meta={`${item.category || 'Report'} · ${formatTimestamp(item.created_at)}`} />
              )) : <EmptyState message="No recent reports yet. This area becomes your recurring operating cadence." />}
            </DashboardSection>
          </div>
        </div>
      );
    }

    return (
      <div className="grid gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-[1.05fr_0.95fr]">
        <DashboardSection eyebrow="Governance" title="Approval queue">
          {collection.approvals.length > 0 ? collection.approvals.slice(0, 5).map((item) => (
            <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workflows/active')} meta={`Pending since ${formatTimestamp(item.created_at)}`} />
          )) : <EmptyState message="No governance blockers are queued. Keep reporting current so this stays true." />}
        </DashboardSection>
        <div className="space-y-6">
          <DashboardSection eyebrow="Visibility" title="Executive reporting">
            {collection.reports.length > 0 ? collection.reports.slice(0, 4).map((item) => (
              <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/reports')} meta={`${item.category || 'Report'} · ${formatTimestamp(item.created_at)}`} />
            )) : <EmptyState message="No stakeholder-ready reports yet. Completed workflow summaries will start to show up here." />}
          </DashboardSection>
          <DashboardSection eyebrow="Execution" title="Workflow readiness and audit trail">
            {collection.execution_audit.length > 0 ? collection.execution_audit.slice(0, 2).map((item) => (
              <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workflows/active')} meta={`${item.category || 'Audit event'} · ${formatTimestamp(item.created_at)}`} />
            )) : null}
            {collection.template_audit.length > 0 ? collection.template_audit.slice(0, 1).map((item) => (
              <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workflows/templates')} meta={`${item.category || 'Template audit'} · ${formatTimestamp(item.created_at)}`} />
            )) : null}
            {collection.workflows.length > 0 ? collection.workflows.slice(0, 2).map((item) => (
              <ListItem key={item.id} item={item} onClick={() => openRoute('/dashboard/workflows/active')} meta={`${item.status || 'running'} · ${formatTimestamp(item.updated_at)}`} />
            )) : null}
            {collection.execution_audit.length === 0 && collection.template_audit.length === 0 && collection.workflows.length === 0 ? <EmptyState message="No workflow activity yet. Use governed templates to start building the audit trail." /> : null}
          </DashboardSection>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="h-52 animate-pulse rounded-[32px] bg-slate-100" />
        <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((item) => <div key={item} className="h-28 animate-pulse rounded-3xl bg-slate-100" />)}
        </div>
        <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
          <div className="h-72 animate-pulse rounded-3xl bg-slate-100" />
          <div className="h-72 animate-pulse rounded-3xl bg-slate-100" />
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="mx-auto max-w-6xl space-y-8">
        <div className={`rounded-[28px] p-6 ${
          isTimeoutError
            ? 'border border-amber-200 bg-amber-50'
            : 'border border-rose-200 bg-rose-50'
        }`}>
          <div className="flex items-start gap-4">
            <div className={`shrink-0 flex h-10 w-10 items-center justify-center rounded-full ${
              isTimeoutError ? 'bg-amber-100' : 'bg-rose-100'
            }`}>
              <Zap size={20} className={isTimeoutError ? 'text-amber-600' : 'text-rose-600'} />
            </div>
            <div className="flex-1">
              <h2 className={`text-lg font-semibold ${isTimeoutError ? 'text-amber-900' : 'text-rose-900'}`}>
                {isTimeoutError ? 'Dashboard data is taking too long' : 'Dashboard data is unavailable'}
              </h2>
              <p className={`mt-1 text-sm ${isTimeoutError ? 'text-amber-700' : 'text-rose-700'}`}>
                {error ?? 'We could not load your dashboard summary right now.'}
              </p>
              <p className={`mt-2 text-sm ${isTimeoutError ? 'text-amber-700' : 'text-rose-700'}`}>
                Quick Actions below still work, so you can keep moving while we reconnect the live dashboard summary.
              </p>
              <button
                type="button"
                onClick={() => setReloadKey((value) => value + 1)}
                className={`mt-4 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
                  isTimeoutError
                    ? 'bg-amber-600 text-white hover:bg-amber-700'
                    : 'bg-rose-600 text-white hover:bg-rose-700'
                }`}
              >
                Try again <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>

        <section>
          <h2 className="text-xl font-semibold text-slate-900 mb-4">Quick Actions</h2>
          <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {launchpad.map((card) => (
              <button
                key={card.href}
                type="button"
                onClick={() => openRoute(card.href)}
                className="group relative flex flex-col gap-3 rounded-[24px] border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:shadow-md hover:border-slate-300"
              >
                <div className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${card.accent} text-white shadow-sm`}>
                  {card.icon}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">{card.title}</p>
                  <p className="mt-1 text-xs text-slate-500 leading-relaxed">{card.description}</p>
                </div>
                <ArrowRight size={14} className="absolute right-4 top-5 text-slate-300 group-hover:text-slate-500 transition-colors" />
              </button>
            ))}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <DashboardBriefCard persona={persona} />

      <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summary.kpis.map((kpi) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_18px_60px_-35px_rgba(15,23,42,0.4)]">
            <p className="text-sm text-slate-500">{kpi.label}</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{kpi.value}</p>
          </motion.div>
        ))}
      </div>

      {renderFounderBoard()}

      <DashboardSection eyebrow="Launchpad" title="Move somewhere useful quickly">
        <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {launchpad.map((card) => (
            <button
              key={card.title}
              type="button"
              onClick={() => openRoute(card.href)}
              className="group rounded-[26px] border border-slate-200 bg-slate-50/90 p-5 text-left transition hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white"
            >
              <div className={`inline-flex rounded-2xl bg-gradient-to-br ${card.accent} p-3 text-white shadow-lg`}>
                {card.icon}
              </div>
              <p className="mt-4 text-base font-semibold text-slate-900">{card.title}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p>
              <span className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
                Open <ArrowRight size={14} className="transition group-hover:translate-x-1" />
              </span>
            </button>
          ))}
        </div>
      </DashboardSection>
    </div>
  );
}

