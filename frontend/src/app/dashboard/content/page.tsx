'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { usePersona } from '@/contexts/PersonaContext';
import type { PersonaType } from '@/services/onboarding';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { getContentBundles, getContentDeliverables } from '@/services/content';
import type { ContentBundle, ContentDeliverable } from '@/services/content';
import { getDashboardSummary } from '@/services/dashboard';
import type { DashboardListItem } from '@/services/dashboard';
import {
  FileText,
  Calendar as CalendarIcon,
  List,
  ChevronLeft,
  ChevronRight,
  Plus,
  Image,
  Video,
  Music,
  Layers,
  Search,
  Clock,
  Archive,
} from 'lucide-react';
import Link from 'next/link';

type ViewMode = 'calendar' | 'list';
type StatusFilter = 'all' | 'scheduled' | 'draft' | 'in_progress' | 'review' | 'published' | 'backlog';

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'scheduled', label: 'Scheduled' },
  { key: 'draft', label: 'Drafts' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'review', label: 'Review' },
  { key: 'published', label: 'Published' },
  { key: 'backlog', label: 'Backlog' },
];

const PLATFORMS = [
  { key: 'instagram', label: 'Instagram', dot: 'bg-pink-500' },
  { key: 'youtube', label: 'YouTube', dot: 'bg-red-500' },
  { key: 'linkedin', label: 'LinkedIn', dot: 'bg-blue-600' },
  { key: 'twitter', label: 'Twitter', dot: 'bg-sky-500' },
  { key: 'tiktok', label: 'TikTok', dot: 'bg-slate-800' },
  { key: 'facebook', label: 'Facebook', dot: 'bg-blue-500' },
] as const;

const PLATFORM_DOTS: Record<string, string> = {
  instagram: 'bg-pink-500',
  youtube: 'bg-red-500',
  linkedin: 'bg-blue-600',
  twitter: 'bg-sky-500',
  tiktok: 'bg-slate-800',
  facebook: 'bg-blue-500',
};

const BUNDLE_TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  image: { bg: 'bg-blue-100', text: 'text-blue-700' },
  video: { bg: 'bg-purple-100', text: 'text-purple-700' },
  audio: { bg: 'bg-amber-100', text: 'text-amber-700' },
  mixed: { bg: 'bg-teal-100', text: 'text-teal-700' },
  text: { bg: 'bg-slate-100', text: 'text-slate-700' },
};

const BUNDLE_TYPE_ICONS: Record<string, typeof FileText> = {
  image: Image,
  video: Video,
  audio: Music,
  mixed: Layers,
  text: FileText,
};

function getBundleTypeStyle(bundleType: string | null) {
  const key = (bundleType ?? 'text').toLowerCase();
  return BUNDLE_TYPE_COLORS[key] ?? BUNDLE_TYPE_COLORS.text;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 rounded-[28px] bg-slate-100" />
        ))}
      </div>
      <div className="h-10 w-full rounded-xl bg-slate-100" />
      <div className="h-96 rounded-xl bg-slate-100" />
    </div>
  );
}

export default function ContentCalendarPage() {
  const { persona } = usePersona();
  const [view, setView] = useState<ViewMode>('calendar');
  const [bundles, setBundles] = useState<ContentBundle[]>([]);
  const [deliverables, setDeliverables] = useState<ContentDeliverable[]>([]);
  const [contentQueue, setContentQueue] = useState<DashboardListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [platformFilter, setPlatformFilter] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [bundlesData, summaryData] = await Promise.allSettled([
          getContentBundles(),
          getDashboardSummary(),
        ]);
        if (cancelled) return;
        let loadedBundles: ContentBundle[] = [];
        if (bundlesData.status === 'fulfilled') {
          loadedBundles = bundlesData.value;
          setBundles(loadedBundles);
        }
        if (summaryData.status === 'fulfilled')
          setContentQueue(summaryData.value.collections.content_queue ?? []);

        // Load deliverables for platform data
        if (loadedBundles.length > 0) {
          try {
            const bundleIds = loadedBundles.map((b) => b.id);
            const delivs = await getContentDeliverables(bundleIds);
            if (!cancelled) setDeliverables(delivs);
          } catch {
            // Platform data is non-critical, continue without it
          }
        }
      } catch {
        // Errors handled by individual promises
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Aggregate platforms per bundle from deliverables
  const bundlePlatforms = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const d of deliverables) {
      if (!d.platform) continue;
      const platforms = map.get(d.bundle_id) ?? [];
      const normalizedPlatform = d.platform.toLowerCase();
      if (!platforms.includes(normalizedPlatform)) {
        platforms.push(normalizedPlatform);
        map.set(d.bundle_id, platforms);
      }
    }
    return map;
  }, [deliverables]);

  // All unique platforms actually in use
  const activePlatforms = useMemo(() => {
    const all = new Set<string>();
    for (const platforms of bundlePlatforms.values()) {
      for (const p of platforms) all.add(p);
    }
    return all;
  }, [bundlePlatforms]);

  // KPI calculations (with scheduled + backlog)
  const kpis = useMemo(() => {
    const total = bundles.length;
    const published = bundles.filter((b) => b.status === 'published').length;
    const scheduled = bundles.filter((b) => b.status === 'scheduled').length;
    const inProgress = bundles.filter(
      (b) => b.status === 'in_progress' || b.status === 'review'
    ).length;
    const drafts = bundles.filter((b) => b.status === 'draft').length;
    const backlog = bundles.filter((b) => b.status === 'backlog').length;
    return { total, published, scheduled, inProgress, drafts, backlog };
  }, [bundles]);

  // Status tab counts
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: bundles.length };
    for (const b of bundles) {
      counts[b.status] = (counts[b.status] ?? 0) + 1;
    }
    return counts;
  }, [bundles]);

  // Calendar helpers
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayOfWeek = new Date(year, month, 1).getDay();

  const prevMonthDays = new Date(year, month, 0).getDate();
  const totalCells = Math.ceil((firstDayOfWeek + daysInMonth) / 7) * 7;

  const calendarDays = useMemo(() => {
    const days: { date: Date; isCurrentMonth: boolean }[] = [];
    // Previous month padding
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month - 1, prevMonthDays - i),
        isCurrentMonth: false,
      });
    }
    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
      days.push({ date: new Date(year, month, d), isCurrentMonth: true });
    }
    // Next month padding
    const remaining = totalCells - days.length;
    for (let d = 1; d <= remaining; d++) {
      days.push({ date: new Date(year, month + 1, d), isCurrentMonth: false });
    }
    return days;
  }, [year, month, daysInMonth, firstDayOfWeek, prevMonthDays, totalCells]);

  // Filter bundles by status + platform for both views
  const filterBundle = (b: ContentBundle): boolean => {
    if (statusFilter !== 'all' && b.status !== statusFilter) return false;
    if (platformFilter.length > 0) {
      const platforms = bundlePlatforms.get(b.id) ?? [];
      if (!platformFilter.some((pf) => platforms.includes(pf))) return false;
    }
    return true;
  };

  // Map filtered bundles to dates for calendar
  const bundlesByDate = useMemo(() => {
    const map = new Map<string, ContentBundle[]>();
    for (const b of bundles) {
      if (!b.target_date) continue;
      if (!filterBundle(b)) continue;
      const key = b.target_date.slice(0, 10);
      const existing = map.get(key) ?? [];
      existing.push(b);
      map.set(key, existing);
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundles, statusFilter, platformFilter, bundlePlatforms]);

  // List view filtering (includes search)
  const filteredBundles = useMemo(() => {
    let result = bundles.filter(filterBundle);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (b) =>
          b.title.toLowerCase().includes(q) ||
          (b.description ?? '').toLowerCase().includes(q)
      );
    }
    result.sort((a, b) => {
      const da = a.target_date ?? '';
      const db = b.target_date ?? '';
      return db.localeCompare(da);
    });
    return result;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundles, statusFilter, platformFilter, bundlePlatforms, searchQuery]);

  const today = new Date();
  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  const monthLabel = currentDate.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  function goToPrevMonth() {
    setCurrentDate(new Date(year, month - 1, 1));
  }

  function goToNextMonth() {
    setCurrentDate(new Date(year, month + 1, 1));
  }

  function goToToday() {
    setCurrentDate(new Date());
  }

  function togglePlatform(platform: string) {
    setPlatformFilter((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
  }

  const isEnterprise = (persona as PersonaType) === 'enterprise';

  if (loading) {
    return (
      <DashboardErrorBoundary fallbackTitle="Content Error">
      <PremiumShell><div className="mx-auto max-w-7xl p-6">
        <LoadingSkeleton />
      </div></PremiumShell>
      </DashboardErrorBoundary>
    );
  }

  return (
    <DashboardErrorBoundary fallbackTitle="Content Error">
    <PremiumShell><motion.div className="mx-auto max-w-7xl p-6" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Content Calendar</h1>
        <Link
          href="/dashboard/command-center"
          className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Create Content
        </Link>
      </div>

      {/* KPI Row */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
        <MetricCard
          label="Total Content"
          value={kpis.total}
          icon={FileText}
          color="text-teal-600"
          bg="bg-teal-50"
          gradient="from-teal-400 to-cyan-500"
          delay={0}
        />
        <MetricCard
          label="Scheduled"
          value={kpis.scheduled}
          icon={Clock}
          color="text-blue-600"
          bg="bg-blue-50"
          gradient="from-blue-400 to-sky-500"
          delay={0.05}
        />
        <MetricCard
          label="In Progress"
          value={kpis.inProgress}
          icon={Layers}
          color="text-amber-600"
          bg="bg-amber-50"
          gradient="from-amber-400 to-orange-500"
          delay={0.1}
        />
        <MetricCard
          label="Published"
          value={kpis.published}
          icon={CalendarIcon}
          color="text-emerald-600"
          bg="bg-emerald-50"
          gradient="from-emerald-400 to-green-500"
          delay={0.15}
        />
        <MetricCard
          label="Backlog"
          value={kpis.backlog}
          icon={Archive}
          color="text-slate-600"
          bg="bg-slate-50"
          gradient="from-slate-400 to-slate-600"
          delay={0.2}
        />
      </div>

      {/* View Toggle + Platform Filters Row */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* View Toggle */}
        <div className="flex gap-1 rounded-2xl bg-slate-100 p-1">
          <button
            onClick={() => setView('calendar')}
            className={`inline-flex items-center gap-2 transition-colors ${
              view === 'calendar'
                ? 'rounded-xl bg-teal-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm'
                : 'rounded-xl px-4 py-1.5 text-sm font-semibold text-slate-500 hover:bg-white'
            }`}
          >
            <CalendarIcon className="h-4 w-4" />
            Calendar
          </button>
          <button
            onClick={() => setView('list')}
            className={`inline-flex items-center gap-2 transition-colors ${
              view === 'list'
                ? 'rounded-xl bg-teal-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm'
                : 'rounded-xl px-4 py-1.5 text-sm font-semibold text-slate-500 hover:bg-white'
            }`}
          >
            <List className="h-4 w-4" />
            List
          </button>
        </div>

        {/* Platform Filter Chips */}
        {activePlatforms.size > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {PLATFORMS.filter((p) => activePlatforms.has(p.key)).map((platform) => {
              const isActive = platformFilter.includes(platform.key);
              return (
                <button
                  key={platform.key}
                  onClick={() => togglePlatform(platform.key)}
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-slate-800 text-white shadow-sm'
                      : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <span className={`inline-block h-2 w-2 rounded-full ${platform.dot}`} />
                  {platform.label}
                </button>
              );
            })}
            {platformFilter.length > 0 && (
              <button
                onClick={() => setPlatformFilter([])}
                className="rounded-full px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-600 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* Status Tabs */}
      <div className="mb-6 flex gap-1 overflow-x-auto rounded-2xl bg-slate-100 p-1">
        {STATUS_TABS.map((tab) => {
          const count = statusCounts[tab.key] ?? 0;
          // Hide tabs with 0 count (except "all")
          if (tab.key !== 'all' && count === 0) return null;
          return (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              className={`flex-shrink-0 rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                statusFilter === tab.key
                  ? 'bg-white text-slate-800 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab.label}
              <span className="ml-1.5 text-[11px] text-slate-400">
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Calendar View */}
      {view === 'calendar' && (
        <div className="mb-8">
          {/* Month Navigation */}
          <div className="mb-4 flex items-center gap-4">
            <button
              onClick={goToPrevMonth}
              className="rounded-2xl p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <h2 className="text-lg font-semibold text-slate-900">{monthLabel}</h2>
            <button
              onClick={goToNextMonth}
              className="rounded-2xl p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
            <button
              onClick={goToToday}
              className="ml-2 rounded-2xl border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Today
            </button>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-px overflow-hidden rounded-[28px] bg-slate-200 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] border border-slate-100/80">
            {/* Day Headers */}
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => (
              <div
                key={`header-${i}`}
                className="bg-slate-50 p-2 text-center text-xs font-semibold text-slate-500"
              >
                {day}
              </div>
            ))}

            {/* Day Cells */}
            {calendarDays.map(({ date, isCurrentMonth }, idx) => {
              const dateKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
              const dayBundles = bundlesByDate.get(dateKey) ?? [];
              const isToday = dateKey === todayKey;
              const visibleBundles = dayBundles.slice(0, 3);
              const extraCount = dayBundles.length - 3;

              return (
                <div
                  key={`day-${idx}`}
                  className={`min-h-[80px] p-1.5 md:min-h-[110px] ${
                    isCurrentMonth ? 'bg-white' : 'bg-slate-50'
                  }`}
                >
                  <div className="mb-1 flex items-start">
                    <span
                      className={`inline-flex h-6 w-6 items-center justify-center text-xs ${
                        isToday
                          ? 'rounded-full bg-teal-600 font-bold text-white'
                          : isCurrentMonth
                            ? 'font-medium text-slate-700'
                            : 'text-slate-300'
                      }`}
                    >
                      {date.getDate()}
                    </span>
                  </div>
                  <div className="space-y-0.5">
                    {visibleBundles.map((b) => {
                      const style = getBundleTypeStyle(b.bundle_type);
                      const platforms = bundlePlatforms.get(b.id) ?? [];
                      return (
                        <div
                          key={b.id}
                          className={`flex items-center gap-0.5 truncate rounded px-1 py-0.5 text-[10px] font-medium leading-tight ${style.bg} ${style.text}`}
                          title={`${b.title}${platforms.length > 0 ? ` (${platforms.join(', ')})` : ''}`}
                        >
                          {/* Platform indicator dots */}
                          {platforms.length > 0 && (
                            <span className="flex flex-shrink-0 gap-px">
                              {platforms.slice(0, 2).map((p) => (
                                <span
                                  key={p}
                                  className={`inline-block h-1.5 w-1.5 rounded-full ${PLATFORM_DOTS[p] ?? 'bg-slate-400'}`}
                                />
                              ))}
                            </span>
                          )}
                          <span className="truncate">{b.title}</span>
                        </div>
                      );
                    })}
                    {extraCount > 0 && (
                      <div className="px-1 text-[10px] font-medium text-slate-400">
                        +{extraCount} more
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* List View */}
      {view === 'list' && (
        <div className="mb-8">
          {/* Search */}
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search content..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="rounded-xl border border-slate-200 pl-9 pr-4 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 w-full sm:w-64"
              />
            </div>
            <span className="text-xs text-slate-400">
              {filteredBundles.length} item{filteredBundles.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Content Cards */}
          {filteredBundles.length === 0 ? (
            <div className="rounded-[28px] border border-dashed border-slate-200 p-12 text-center">
              <FileText className="mx-auto mb-3 h-10 w-10 text-slate-300" />
              <p className="text-sm font-medium text-slate-500">No content found</p>
              <p className="mt-1 text-xs text-slate-400">
                Try adjusting your search or filter criteria
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredBundles.map((bundle) => {
                const typeStyle = getBundleTypeStyle(bundle.bundle_type);
                const TypeIcon =
                  BUNDLE_TYPE_ICONS[(bundle.bundle_type ?? 'text').toLowerCase()] ?? FileText;
                const platforms = bundlePlatforms.get(bundle.id) ?? [];
                return (
                  <div
                    key={bundle.id}
                    className="flex items-center gap-4 rounded-2xl border border-slate-100/80 bg-white p-4 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] transition-all hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] hover:-translate-y-0.5"
                  >
                    <div
                      className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${typeStyle.bg}`}
                    >
                      <TypeIcon className={`h-5 w-5 ${typeStyle.text}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-slate-900">{bundle.title}</p>
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span>{formatDate(bundle.target_date)}</span>
                        {/* Platform indicators */}
                        {platforms.length > 0 && (
                          <span className="flex items-center gap-1">
                            {platforms.map((p) => (
                              <span
                                key={p}
                                className={`inline-flex items-center gap-1 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500`}
                              >
                                <span className={`inline-block h-1.5 w-1.5 rounded-full ${PLATFORM_DOTS[p] ?? 'bg-slate-400'}`} />
                                <span className="capitalize">{p}</span>
                              </span>
                            ))}
                          </span>
                        )}
                      </div>
                    </div>
                    <span
                      className={`hidden sm:inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${typeStyle.bg} ${typeStyle.text}`}
                    >
                      {(bundle.bundle_type ?? 'text').charAt(0).toUpperCase() +
                        (bundle.bundle_type ?? 'text').slice(1)}
                    </span>
                    <StatusBadge status={bundle.status} />
                    {isEnterprise && (
                      <span className="hidden sm:inline-flex items-center rounded-full bg-violet-50 px-2.5 py-0.5 text-xs font-medium text-violet-700">
                        {bundle.status === 'approved' ? 'Approved' : 'Pending Approval'}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Content Queue */}
      <div className="mt-8">
        <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Upcoming Queue</h2>
        {contentQueue.length === 0 ? (
          <div className="rounded-[28px] border border-dashed border-slate-200 p-8 text-center">
            <CalendarIcon className="mx-auto mb-3 h-8 w-8 text-slate-300" />
            <p className="text-sm font-medium text-slate-500">No content in queue.</p>
            <p className="mt-1 text-xs text-slate-400">Start creating!</p>
          </div>
        ) : (
          <div className="space-y-2">
            {contentQueue.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-2xl border border-slate-100/80 bg-white px-4 py-3 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-900">{item.title}</p>
                  {item.created_at && (
                    <p className="text-xs text-slate-400">
                      {formatDate(item.created_at)}
                    </p>
                  )}
                </div>
                {item.status && <StatusBadge status={item.status} />}
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div></PremiumShell>
    </DashboardErrorBoundary>
  );
}
