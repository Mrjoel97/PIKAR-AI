'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { usePersona } from '@/contexts/PersonaContext';
import { type PersonaType } from '@/services/onboarding';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import {
  TrendingUp,
  Users,
  Target,
  DollarSign,
  Search,
  Filter,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  Wifi,
  WifiOff,
  BarChart3,
  Globe,
} from 'lucide-react';
import {
  type Contact,
  type ContactActivity,
  type ConnectedAccount,
  type Campaign,
  type PageAnalytic,
  type PipelineStats,
  getContacts,
  getContactActivities,
  getConnectedAccounts,
  getCampaignMetrics,
  getPageAnalytics,
  computePipelineStats,
} from '@/services/sales';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString();
}

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return 'Never';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const PERSONA_SUBTITLES: Record<PersonaType, string> = {
  solopreneur: 'Your leads and customers at a glance',
  startup: 'Track your growing pipeline and outreach',
  sme: 'Pipeline management and channel performance',
  enterprise: 'Enterprise pipeline analytics and channel monitoring',
};

const PIPELINE_STAGES = ['lead', 'qualified', 'opportunity', 'customer'] as const;
const SOLO_STAGES = ['lead', 'customer'] as const;

const STAGE_LABELS: Record<string, string> = {
  lead: 'Leads',
  qualified: 'Qualified',
  opportunity: 'Opportunity',
  customer: 'Customers',
};

// ---------------------------------------------------------------------------
// Skeleton loaders
// ---------------------------------------------------------------------------

function KpiSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-24 animate-pulse rounded-[28px] bg-slate-100" />
      ))}
    </div>
  );
}

function KanbanSkeleton() {
  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="w-72 flex-shrink-0">
          <div className="mb-3 h-8 w-32 animate-pulse rounded-xl bg-slate-100" />
          {Array.from({ length: 3 }).map((_, j) => (
            <div key={j} className="mb-3 h-28 animate-pulse rounded-2xl bg-slate-100" />
          ))}
        </div>
      ))}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-xl bg-slate-100" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function SalesPipelinePage() {
  const { persona } = usePersona();
  const activePersona = (persona ?? 'startup') as PersonaType;

  // ---- State ----
  const [activeTab, setActiveTab] = useState<'pipeline' | 'channels'>('pipeline');
  const [searchQuery, setSearchQuery] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [platformFilter, setPlatformFilter] = useState('all');

  // Data
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [activities, setActivities] = useState<ContactActivity[]>([]);
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [analytics, setAnalytics] = useState<PageAnalytic[]>([]);

  // Loading
  const [loadingPipeline, setLoadingPipeline] = useState(true);
  const [loadingChannels, setLoadingChannels] = useState(true);

  // ---- Data fetching ----
  useEffect(() => {
    let cancelled = false;
    async function fetchPipeline() {
      setLoadingPipeline(true);
      try {
        const [c, a] = await Promise.all([getContacts(), getContactActivities()]);
        if (!cancelled) {
          setContacts(c);
          setActivities(a);
        }
      } catch {
        // silently degrade
      } finally {
        if (!cancelled) setLoadingPipeline(false);
      }
    }
    fetchPipeline();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function fetchChannels() {
      setLoadingChannels(true);
      try {
        const [acc, camp, pa] = await Promise.all([
          getConnectedAccounts(),
          getCampaignMetrics(),
          getPageAnalytics(),
        ]);
        if (!cancelled) {
          setAccounts(acc);
          setCampaigns(camp);
          setAnalytics(pa);
        }
      } catch {
        // silently degrade
      } finally {
        if (!cancelled) setLoadingChannels(false);
      }
    }
    fetchChannels();
    return () => {
      cancelled = true;
    };
  }, []);

  // ---- Computed ----
  const stats: PipelineStats = useMemo(() => computePipelineStats(contacts), [contacts]);

  const filteredContacts = useMemo(() => {
    let list = contacts;
    if (stageFilter !== 'all') {
      list = list.filter((c) => c.lifecycle_stage === stageFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          (c.company ?? '').toLowerCase().includes(q) ||
          (c.email ?? '').toLowerCase().includes(q),
      );
    }
    return list;
  }, [contacts, stageFilter, searchQuery]);

  const stages = activePersona === 'solopreneur' ? SOLO_STAGES : PIPELINE_STAGES;

  const contactsByStage = useMemo(() => {
    const map: Record<string, Contact[]> = {};
    for (const s of stages) map[s] = [];
    for (const c of filteredContacts) {
      const s = c.lifecycle_stage || 'lead';
      if (map[s]) map[s].push(c);
    }
    return map;
  }, [filteredContacts, stages]);

  // Channel aggregates
  const channelKpis = useMemo(() => {
    let reach = 0;
    let engagement = 0;
    let conversions = 0;
    for (const c of campaigns) {
      reach += c.metrics?.reach ?? c.metrics?.impressions ?? c.metrics?.views ?? 0;
      engagement +=
        (c.metrics?.likes ?? 0) +
        (c.metrics?.comments ?? 0) +
        (c.metrics?.shares ?? 0) +
        (c.metrics?.engagement ?? 0);
      conversions += c.metrics?.conversions ?? 0;
    }
    const activeChannels = accounts.filter((a) => a.status === 'connected').length;
    return { reach, engagement, conversions, activeChannels };
  }, [campaigns, accounts]);

  const filteredAnalytics = useMemo(() => {
    if (platformFilter === 'all') return analytics;
    return analytics.filter((a) => a.platform === platformFilter);
  }, [analytics, platformFilter]);

  const platformOptions = useMemo(() => {
    const set = new Set(analytics.map((a) => a.platform).filter(Boolean));
    return Array.from(set) as string[];
  }, [analytics]);

  // ---- Render ----
  return (
    <DashboardErrorBoundary fallbackTitle="Sales Error">
    <PremiumShell>
      <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      <div className="mx-auto max-w-7xl p-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Sales Pipeline</h1>
            <p className="mt-1 text-sm text-slate-500">
              {PERSONA_SUBTITLES[activePersona]}
            </p>
          </div>
          <Link
            href="/dashboard/command-center"
            className="rounded-2xl bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
          >
            Score a Lead
          </Link>
        </div>

        {/* KPI Row */}
        {loadingPipeline ? (
          <KpiSkeleton />
        ) : (
          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              label="Total Pipeline Value"
              value={formatCurrency(stats.totalValue)}
              icon={DollarSign}
              color="text-emerald-600"
              bg="bg-emerald-50"
              gradient="from-emerald-400 to-teal-500"
              delay={0}
            />
            <MetricCard
              label="Active Leads"
              value={stats.activeLeads}
              icon={Users}
              color="text-blue-600"
              bg="bg-blue-50"
              gradient="from-sky-400 to-blue-500"
              delay={0.05}
            />
            <MetricCard
              label="Conversion Rate"
              value={`${stats.conversionRate.toFixed(1)}%`}
              icon={Target}
              color="text-violet-600"
              bg="bg-violet-50"
              gradient="from-violet-400 to-purple-500"
              delay={0.1}
            />
            <MetricCard
              label="Avg Deal Size"
              value={formatCurrency(stats.avgDealSize)}
              icon={TrendingUp}
              color="text-amber-600"
              bg="bg-amber-50"
              gradient="from-amber-400 to-orange-500"
              delay={0.15}
            />
          </div>
        )}

        {/* Tab Navigation */}
        <div className="mb-6 flex gap-2 rounded-2xl bg-slate-100 p-1">
          <button
            onClick={() => setActiveTab('pipeline')}
            className={`transition ${
              activeTab === 'pipeline'
                ? 'rounded-2xl bg-teal-600 px-5 py-2 text-sm font-semibold text-white shadow-sm'
                : 'rounded-2xl px-5 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100'
            }`}
          >
            Pipeline
          </button>
          <button
            onClick={() => setActiveTab('channels')}
            className={`transition ${
              activeTab === 'channels'
                ? 'rounded-2xl bg-teal-600 px-5 py-2 text-sm font-semibold text-white shadow-sm'
                : 'rounded-2xl px-5 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100'
            }`}
          >
            Channel Monitor
          </button>
        </div>

        {/* ================================================================ */}
        {/* TAB 1: Pipeline View                                             */}
        {/* ================================================================ */}
        {activeTab === 'pipeline' && (
          <div>
            {/* Search + Filter */}
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search contacts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 py-2 pl-10 pr-4 text-sm text-slate-900 placeholder-slate-400 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <select
                  value={stageFilter}
                  onChange={(e) => setStageFilter(e.target.value)}
                  className="appearance-none rounded-xl border border-slate-200 py-2 pl-10 pr-8 text-sm text-slate-700 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                >
                  <option value="all">All Stages</option>
                  <option value="lead">Leads</option>
                  <option value="qualified">Qualified</option>
                  <option value="opportunity">Opportunity</option>
                  <option value="customer">Customers</option>
                  <option value="churned">Churned</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            </div>

            {/* Kanban Board */}
            {loadingPipeline ? (
              <KanbanSkeleton />
            ) : filteredContacts.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-[28px] border border-dashed border-slate-200 py-16">
                <Users className="mb-3 h-10 w-10 text-slate-300" />
                <p className="text-sm font-medium text-slate-500">No contacts found</p>
                <p className="mt-1 text-xs text-slate-400">
                  Add contacts or adjust your filters to see your pipeline
                </p>
              </div>
            ) : (
              <div className="mb-8 flex gap-4 overflow-x-auto pb-4">
                {stages.map((stage) => {
                  const items = contactsByStage[stage] ?? [];
                  const stageValue = items.reduce((s, c) => s + (c.estimated_value ?? 0), 0);
                  return (
                    <div key={stage} className="w-72 flex-shrink-0">
                      {/* Column Header */}
                      <div className="mb-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-slate-700">
                            {STAGE_LABELS[stage] ?? stage}
                          </h3>
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                            {items.length}
                          </span>
                        </div>
                        <span className="text-xs font-medium text-slate-500">
                          {formatCurrency(stageValue)}
                        </span>
                      </div>

                      {/* Contact Cards */}
                      <div className="space-y-3">
                        {items.map((contact) => (
                          <div
                            key={contact.id}
                            className="rounded-2xl border border-slate-100/80 bg-white p-3.5 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] transition-all hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] hover:-translate-y-0.5"
                          >
                            <p className="text-sm font-bold text-slate-900">{contact.name}</p>
                            {contact.company && (
                              <p className="mt-0.5 text-sm text-slate-500">{contact.company}</p>
                            )}
                            <div className="mt-2 flex flex-wrap items-center gap-2">
                              {contact.estimated_value != null && (
                                <StatusBadge status={formatCurrency(contact.estimated_value)} />
                              )}
                              {contact.source && (
                                <span className="rounded-full bg-slate-50 px-2 py-0.5 text-xs text-slate-500">
                                  {contact.source}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                        {items.length === 0 && (
                          <p className="py-6 text-center text-xs text-slate-400">No contacts</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Recent Activity */}
            <div>
              <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Recent Activity</h2>
              {loadingPipeline ? (
                <TableSkeleton />
              ) : activities.length === 0 ? (
                <p className="py-6 text-center text-sm text-slate-400">
                  No recent activity recorded
                </p>
              ) : (
                <div className="space-y-3">
                  {activities.map((a) => (
                    <div
                      key={a.id}
                      className="flex items-start gap-3 rounded-xl border border-slate-100 p-3"
                    >
                      <div className="flex-shrink-0 rounded-lg bg-slate-50 p-2">
                        <BarChart3 className="h-4 w-4 text-slate-500" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-slate-700">{a.activity_type}</p>
                        {a.description && (
                          <p className="mt-0.5 text-xs text-slate-500">{a.description}</p>
                        )}
                      </div>
                      <span className="flex-shrink-0 text-xs text-slate-400">
                        {relativeTime(a.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* TAB 2: Channel Monitor                                           */}
        {/* ================================================================ */}
        {activeTab === 'channels' && (
          <div>
            {/* Channel KPI Row */}
            {loadingChannels ? (
              <KpiSkeleton />
            ) : (
              <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
                <MetricCard
                  label="Total Reach"
                  value={formatNumber(channelKpis.reach)}
                  icon={Eye}
                  color="text-blue-600"
                  bg="bg-blue-50"
                  gradient="from-sky-400 to-blue-500"
                  delay={0}
                />
                <MetricCard
                  label="Total Engagement"
                  value={formatNumber(channelKpis.engagement)}
                  icon={Heart}
                  color="text-pink-600"
                  bg="bg-pink-50"
                  gradient="from-pink-400 to-rose-500"
                  delay={0.05}
                />
                <MetricCard
                  label="Total Conversions"
                  value={formatNumber(channelKpis.conversions)}
                  icon={Target}
                  color="text-emerald-600"
                  bg="bg-emerald-50"
                  gradient="from-emerald-400 to-teal-500"
                  delay={0.1}
                />
                <MetricCard
                  label="Active Channels"
                  value={channelKpis.activeChannels}
                  icon={Wifi}
                  color="text-teal-600"
                  bg="bg-teal-50"
                  gradient="from-teal-400 to-cyan-500"
                  delay={0.15}
                />
              </div>
            )}

            {/* Connected Accounts */}
            <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Connected Accounts</h2>
            {loadingChannels ? (
              <TableSkeleton />
            ) : accounts.length === 0 ? (
              <div className="mb-8 flex flex-col items-center justify-center rounded-[28px] border border-dashed border-slate-200 py-12">
                <WifiOff className="mb-3 h-10 w-10 text-slate-300" />
                <p className="text-sm font-medium text-slate-500">No accounts connected</p>
                <p className="mt-1 text-xs text-slate-400">
                  Connect your social and marketing accounts to start monitoring
                </p>
              </div>
            ) : (
              <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {accounts.map((acc) => (
                  <div
                    key={acc.id}
                    className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                  >
                    <div className="mb-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="rounded-xl bg-slate-50 p-2">
                          <Globe className="h-5 w-5 text-slate-600" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-900">
                            {acc.account_name ?? acc.platform}
                          </p>
                          <p className="text-xs capitalize text-slate-500">{acc.platform}</p>
                        </div>
                      </div>
                      <StatusBadge status={acc.status} variant="dot" />
                    </div>
                    <p className="mb-3 text-xs text-slate-400">
                      Last synced: {relativeTime(acc.last_synced_at)}
                    </p>
                    <div className="flex items-center gap-4 rounded-xl bg-slate-50 p-3">
                      <div className="flex items-center gap-1">
                        <Eye className="h-3.5 w-3.5 text-slate-400" />
                        <span className="text-xs text-slate-500">--</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Heart className="h-3.5 w-3.5 text-slate-400" />
                        <span className="text-xs text-slate-500">--</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <MessageCircle className="h-3.5 w-3.5 text-slate-400" />
                        <span className="text-xs text-slate-500">--</span>
                      </div>
                      <p className="ml-auto text-xs text-slate-400">Sync to view metrics</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Campaign Performance Table */}
            <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Campaign Performance</h2>
            {loadingChannels ? (
              <TableSkeleton />
            ) : campaigns.length === 0 ? (
              <div className="mb-8 flex flex-col items-center justify-center rounded-[28px] border border-dashed border-slate-200 py-12">
                <BarChart3 className="mb-3 h-10 w-10 text-slate-300" />
                <p className="text-sm font-medium text-slate-500">No campaigns yet</p>
                <p className="mt-1 text-xs text-slate-400">
                  Create a campaign to track its performance here
                </p>
              </div>
            ) : (
              <div className="mb-8 overflow-x-auto rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100">
                      <th className="pb-3 pr-4 font-semibold text-[11px] uppercase tracking-[0.28em] text-slate-400">Campaign Name</th>
                      <th className="pb-3 pr-4 font-semibold text-[11px] uppercase tracking-[0.28em] text-slate-400">Channel</th>
                      <th className="pb-3 pr-4 text-right font-semibold text-[11px] uppercase tracking-[0.28em] text-slate-400">Views</th>
                      <th className="pb-3 pr-4 text-right font-semibold text-[11px] uppercase tracking-[0.28em] text-slate-400">Clicks</th>
                      <th className="pb-3 pr-4 text-right font-semibold text-[11px] uppercase tracking-[0.28em] text-slate-400">
                        Conversions
                      </th>
                      <th className="pb-3 pr-4 text-right font-semibold text-[11px] uppercase tracking-[0.28em] text-slate-400">
                        Engagement
                      </th>
                      <th className="pb-3 font-semibold text-[11px] uppercase tracking-[0.28em] text-slate-400">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {campaigns.map((c) => {
                      const engRate = c.metrics?.ctr ?? c.metrics?.engagement ?? 0;
                      const engColor =
                        engRate > 5
                          ? 'text-emerald-600'
                          : engRate >= 2
                            ? 'text-amber-600'
                            : 'text-red-500';
                      return (
                        <tr key={c.id} className="border-b border-slate-50">
                          <td className="py-3 pr-4 font-medium text-slate-900">{c.name}</td>
                          <td className="py-3 pr-4 text-slate-600">{c.type ?? '--'}</td>
                          <td className="py-3 pr-4 text-right text-slate-700">
                            {formatNumber(c.metrics?.views ?? 0)}
                          </td>
                          <td className="py-3 pr-4 text-right text-slate-700">
                            {formatNumber(c.metrics?.clicks ?? 0)}
                          </td>
                          <td className="py-3 pr-4 text-right text-slate-700">
                            {formatNumber(c.metrics?.conversions ?? 0)}
                          </td>
                          <td className={`py-3 pr-4 text-right font-medium ${engColor}`}>
                            {engRate.toFixed(1)}%
                          </td>
                          <td className="py-3">
                            <StatusBadge status={c.status} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Content Performance Feed */}
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Content Performance</h2>
              {platformOptions.length > 0 && (
                <div className="relative">
                  <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <select
                    value={platformFilter}
                    onChange={(e) => setPlatformFilter(e.target.value)}
                    className="appearance-none rounded-xl border border-slate-200 py-2 pl-10 pr-8 text-sm text-slate-700 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  >
                    <option value="all">All Platforms</option>
                    {platformOptions.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            {loadingChannels ? (
              <TableSkeleton />
            ) : filteredAnalytics.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-[28px] border border-dashed border-slate-200 py-12">
                <Share2 className="mb-3 h-10 w-10 text-slate-300" />
                <p className="text-sm font-medium text-slate-500">
                  No content performance data yet
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Publish content and connect channels to track performance
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredAnalytics.map((pa) => {
                  const engColor =
                    (pa.engagement_rate ?? 0) > 5
                      ? 'text-emerald-600'
                      : (pa.engagement_rate ?? 0) >= 2
                        ? 'text-amber-600'
                        : 'text-red-500';
                  return (
                    <div
                      key={pa.id}
                      className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <p
                          className="truncate text-sm font-semibold text-slate-900"
                          title={pa.page_url ?? ''}
                        >
                          {pa.page_url ?? 'Untitled'}
                        </p>
                        {pa.platform && <StatusBadge status={pa.platform} />}
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <p className="text-xs text-slate-400">Views</p>
                          <p className="text-sm font-bold text-slate-900">
                            {formatNumber(pa.views)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-400">Clicks</p>
                          <p className="text-sm font-bold text-slate-900">
                            {formatNumber(pa.clicks ?? 0)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-400">Conversions</p>
                          <p className="text-sm font-bold text-slate-900">
                            {formatNumber(pa.conversions ?? 0)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-400">Engagement</p>
                          <p className={`text-sm font-bold ${engColor}`}>
                            {(pa.engagement_rate ?? 0).toFixed(1)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
      </motion.div>
    </PremiumShell>
    </DashboardErrorBoundary>
  );
}
