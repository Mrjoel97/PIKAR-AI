'use client';

import { useState, useEffect, useMemo } from 'react';
import { usePersona } from '@/contexts/PersonaContext';
import type { PersonaType } from '@/services/onboarding';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import { getContentBundles, getCampaigns } from '@/services/content';
import type { ContentBundle } from '@/services/content';
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
} from 'lucide-react';
import Link from 'next/link';

type ViewMode = 'calendar' | 'list';
type StatusFilter = 'all' | 'draft' | 'in_progress' | 'published';

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
          <div key={i} className="h-24 rounded-2xl bg-slate-100" />
        ))}
      </div>
      <div className="h-10 w-48 rounded-lg bg-slate-100" />
      <div className="h-96 rounded-lg bg-slate-100" />
    </div>
  );
}

export default function ContentCalendarPage() {
  const { persona } = usePersona();
  const [view, setView] = useState<ViewMode>('calendar');
  const [bundles, setBundles] = useState<ContentBundle[]>([]);
  const [contentQueue, setContentQueue] = useState<DashboardListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [bundlesData, summaryData] = await Promise.allSettled([
          getContentBundles(),
          getDashboardSummary(),
        ]);
        if (cancelled) return;
        if (bundlesData.status === 'fulfilled') setBundles(bundlesData.value);
        if (summaryData.status === 'fulfilled')
          setContentQueue(summaryData.value.collections.content_queue ?? []);
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

  // KPI calculations
  const kpis = useMemo(() => {
    const total = bundles.length;
    const published = bundles.filter((b) => b.status === 'published').length;
    const inProgress = bundles.filter(
      (b) => b.status === 'in_progress' || b.status === 'review'
    ).length;
    const drafts = bundles.filter((b) => b.status === 'draft').length;
    return { total, published, inProgress, drafts };
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

  // Map bundles to dates for calendar
  const bundlesByDate = useMemo(() => {
    const map = new Map<string, ContentBundle[]>();
    for (const b of bundles) {
      if (!b.target_date) continue;
      const key = b.target_date.slice(0, 10);
      const existing = map.get(key) ?? [];
      existing.push(b);
      map.set(key, existing);
    }
    return map;
  }, [bundles]);

  // List view filtering
  const filteredBundles = useMemo(() => {
    let result = [...bundles];
    if (statusFilter !== 'all') {
      result = result.filter((b) => b.status === statusFilter);
    }
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
  }, [bundles, statusFilter, searchQuery]);

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

  const isEnterprise = (persona as PersonaType) === 'enterprise';

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl bg-white p-6">
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl bg-white p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Content Calendar</h1>
        <Link
          href="/dashboard/command-center"
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Create Content
        </Link>
      </div>

      {/* KPI Row */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard
          label="Total Content"
          value={kpis.total}
          icon={FileText}
          color="text-teal-600"
          bg="bg-teal-50"
        />
        <MetricCard
          label="Published"
          value={kpis.published}
          icon={CalendarIcon}
          color="text-emerald-600"
          bg="bg-emerald-50"
        />
        <MetricCard
          label="In Progress"
          value={kpis.inProgress}
          icon={Layers}
          color="text-blue-600"
          bg="bg-blue-50"
        />
        <MetricCard
          label="Drafts"
          value={kpis.drafts}
          icon={FileText}
          color="text-slate-600"
          bg="bg-slate-50"
        />
      </div>

      {/* View Toggle */}
      <div className="mb-6 flex border-b border-slate-200">
        <button
          onClick={() => setView('calendar')}
          className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
            view === 'calendar'
              ? 'border-b-2 border-teal-600 text-teal-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <CalendarIcon className="h-4 w-4" />
          Calendar
        </button>
        <button
          onClick={() => setView('list')}
          className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
            view === 'list'
              ? 'border-b-2 border-teal-600 text-teal-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <List className="h-4 w-4" />
          List
        </button>
      </div>

      {/* Calendar View */}
      {view === 'calendar' && (
        <div className="mb-8">
          {/* Month Navigation */}
          <div className="mb-4 flex items-center gap-4">
            <button
              onClick={goToPrevMonth}
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <h2 className="text-lg font-semibold text-slate-900">{monthLabel}</h2>
            <button
              onClick={goToNextMonth}
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
            <button
              onClick={goToToday}
              className="ml-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Today
            </button>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-px overflow-hidden rounded-lg bg-slate-200">
            {/* Day Headers */}
            {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => (
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
              const visibleBundles = dayBundles.slice(0, 2);
              const extraCount = dayBundles.length - 2;

              return (
                <div
                  key={`day-${idx}`}
                  className={`min-h-[80px] p-1 md:min-h-[100px] ${
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
                      return (
                        <div
                          key={b.id}
                          className={`truncate rounded px-1 py-0.5 text-[10px] font-medium leading-tight ${style.bg} ${style.text}`}
                          title={b.title}
                        >
                          {b.title}
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
          {/* Search and Filter */}
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              type="text"
              placeholder="Search content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              <option value="all">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="in_progress">In Progress</option>
              <option value="published">Published</option>
            </select>
          </div>

          {/* Content Cards */}
          {filteredBundles.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 p-12 text-center">
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
                return (
                  <div
                    key={bundle.id}
                    className="flex items-center gap-4 rounded-xl border border-slate-100 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
                  >
                    <div
                      className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${typeStyle.bg}`}
                    >
                      <TypeIcon className={`h-5 w-5 ${typeStyle.text}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-slate-900">{bundle.title}</p>
                      <p className="text-xs text-slate-500">
                        {formatDate(bundle.target_date)}
                      </p>
                    </div>
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${typeStyle.bg} ${typeStyle.text}`}
                    >
                      {(bundle.bundle_type ?? 'text').charAt(0).toUpperCase() +
                        (bundle.bundle_type ?? 'text').slice(1)}
                    </span>
                    <StatusBadge status={bundle.status} />
                    {isEnterprise && (
                      <span className="inline-flex items-center rounded-full bg-violet-50 px-2.5 py-0.5 text-xs font-medium text-violet-700">
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
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Upcoming Queue</h2>
        {contentQueue.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center">
            <CalendarIcon className="mx-auto mb-3 h-8 w-8 text-slate-300" />
            <p className="text-sm font-medium text-slate-500">No content in queue.</p>
            <p className="mt-1 text-xs text-slate-400">Start creating!</p>
          </div>
        ) : (
          <div className="space-y-2">
            {contentQueue.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-4 py-3 shadow-sm"
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
    </div>
  );
}
