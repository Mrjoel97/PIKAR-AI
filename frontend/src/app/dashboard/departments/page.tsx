'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import StatusBadge from '@/components/ui/StatusBadge';
import {
  Building2,
  Activity,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
} from 'lucide-react';
import {
  getDepartmentHealth,
  type DepartmentHealthSummary,
} from '@/services/departments';

// ============================================================================
// Constants
// ============================================================================

const SME_DEPARTMENTS = [
  'Engineering',
  'Marketing',
  'Sales',
  'Finance',
  'HR',
  'Operations',
  'Compliance',
  'Support',
] as const;

type SmeFilter = (typeof SME_DEPARTMENTS)[number] | 'All Departments';

// ============================================================================
// Helpers
// ============================================================================

function healthIcon(status: DepartmentHealthSummary['health_status']) {
  if (status === 'green') return <CheckCircle className="h-5 w-5 text-emerald-500" />;
  if (status === 'yellow') return <AlertTriangle className="h-5 w-5 text-amber-500" />;
  return <AlertTriangle className="h-5 w-5 text-red-500" />;
}

function healthLabel(status: DepartmentHealthSummary['health_status']): string {
  if (status === 'green') return 'Healthy';
  if (status === 'yellow') return 'Needs Attention';
  return 'At Risk';
}

function healthBadgeColor(status: DepartmentHealthSummary['health_status']): string {
  if (status === 'green')
    return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400';
  if (status === 'yellow')
    return 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400';
  return 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400';
}

function completionRate(summary: DepartmentHealthSummary): number {
  if (summary.total_30d === 0) return 0;
  return Math.round((summary.completed_30d / summary.total_30d) * 100);
}

// ============================================================================
// Sub-components
// ============================================================================

function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-[28px] bg-slate-100 dark:bg-slate-800 ${className}`}
    />
  );
}

function LoadingSkeleton() {
  return (
    <PremiumShell>
      <div className="mx-auto max-w-7xl space-y-8">
        <SkeletonCard className="h-8 w-64" />
        <SkeletonCard className="h-10 w-48" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} className="h-48" />
          ))}
        </div>
      </div>
    </PremiumShell>
  );
}

interface DepartmentCardProps {
  summary: DepartmentHealthSummary;
  expanded: boolean;
}

function DepartmentCard({ summary, expanded }: DepartmentCardProps) {
  const rate = completionRate(summary);

  return (
    <motion.div
      layout
      className={`rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-shadow hover:shadow-md dark:border-slate-700 dark:bg-slate-800/60 ${expanded ? 'col-span-full' : ''}`}
    >
      {/* Header */}
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5 flex-shrink-0 text-indigo-500" />
          <h3 className="font-semibold text-slate-900 dark:text-white">{summary.department_name}</h3>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${healthBadgeColor(summary.health_status)}`}
        >
          {healthIcon(summary.health_status)}
          {healthLabel(summary.health_status)}
        </span>
      </div>

      {/* Status */}
      <div className="mb-3 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        <Activity className="h-3.5 w-3.5" />
        <StatusBadge status={summary.department_status} />
      </div>

      {/* Metrics */}
      <div className="space-y-3">
        <div>
          <div className="mb-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>30-day task completion</span>
            <span className="font-medium text-slate-700 dark:text-slate-200">{rate}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
            <div
              className={`h-full transition-all ${rate >= 80 ? 'bg-emerald-400' : rate >= 50 ? 'bg-amber-400' : 'bg-red-400'}`}
              style={{ width: `${rate}%` }}
            />
          </div>
        </div>

        {expanded && (
          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="rounded-2xl bg-slate-50 p-3 text-center dark:bg-slate-700/40">
              <p className="text-xl font-bold text-slate-900 dark:text-white">
                {summary.active_tasks}
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                Active Tasks
              </p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-3 text-center dark:bg-slate-700/40">
              <p className="text-xl font-bold text-emerald-600">
                {summary.completed_30d}
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                Completed (30d)
              </p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-3 text-center dark:bg-slate-700/40">
              <p className="text-xl font-bold text-slate-900 dark:text-white">
                {summary.total_30d}
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                Total (30d)
              </p>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ============================================================================
// Main page
// ============================================================================

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<DepartmentHealthSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<SmeFilter>('All Departments');

  const loadDepartments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDepartmentHealth();
      setDepartments(data);
    } catch {
      setError('Failed to load department data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDepartments();
  }, [loadDepartments]);

  if (loading) {
    return (
      <DashboardErrorBoundary fallbackTitle="Departments Error">
        <LoadingSkeleton />
      </DashboardErrorBoundary>
    );
  }

  // Filtered departments: if a specific dept is selected, match by name (case-insensitive)
  const filteredDepartments =
    filter === 'All Departments'
      ? departments
      : departments.filter((d) =>
          d.department_name.toLowerCase().includes(filter.toLowerCase()),
        );

  const selectedExpanded = filter !== 'All Departments';

  return (
    <DashboardErrorBoundary fallbackTitle="Departments Error">
      <PremiumShell>
        <motion.div
          className="mx-auto max-w-7xl space-y-8"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Building2 className="h-7 w-7 text-indigo-600" />
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
                Departments
              </h1>
            </div>
            <div className="flex items-center gap-3">
              {/* Department filter dropdown */}
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as SmeFilter)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                aria-label="Filter by department"
              >
                <option value="All Departments">All Departments</option>
                {SME_DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>

              <button
                onClick={loadDepartments}
                className="inline-flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
                aria-label="Refresh department data"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </div>

          {/* Filter label when a department is selected */}
          {filter !== 'All Departments' && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500 dark:text-slate-400">
                Showing:
              </span>
              <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                {filter}
              </span>
              <button
                onClick={() => setFilter('All Departments')}
                className="text-xs text-slate-400 underline hover:text-slate-600 dark:hover:text-slate-300"
              >
                Clear filter
              </button>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="flex items-center gap-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
              <AlertTriangle className="h-5 w-5 flex-shrink-0" />
              <span>{error}</span>
              <button
                onClick={loadDepartments}
                className="ml-auto rounded-xl bg-red-100 px-3 py-1.5 font-medium hover:bg-red-200 dark:bg-red-900/40 dark:hover:bg-red-900/60"
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty state */}
          {!error && filteredDepartments.length === 0 && (
            <section className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] dark:border-slate-700 dark:bg-slate-800/60">
              <Building2 className="mx-auto mb-4 h-12 w-12 text-slate-300" />
              <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-200">
                {filter === 'All Departments'
                  ? 'No departments configured yet'
                  : `No department found matching "${filter}"`}
              </h2>
              {filter !== 'All Departments' && (
                <button
                  onClick={() => setFilter('All Departments')}
                  className="mt-4 inline-flex items-center gap-2 rounded-2xl bg-indigo-50 px-5 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100"
                >
                  View All Departments
                </button>
              )}
            </section>
          )}

          {/* Department cards grid */}
          {!error && filteredDepartments.length > 0 && (
            <motion.div
              layout
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            >
              {filteredDepartments.map((dept) => (
                <DepartmentCard
                  key={dept.department_id}
                  summary={dept}
                  expanded={selectedExpanded}
                />
              ))}
            </motion.div>
          )}
        </motion.div>
      </PremiumShell>
    </DashboardErrorBoundary>
  );
}
