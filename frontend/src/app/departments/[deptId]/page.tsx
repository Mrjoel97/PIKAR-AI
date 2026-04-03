'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  CheckCircle2,
  PlayCircle,
  ArrowRightLeft,
  Clock,
  ListTodo,
  Activity,
  TrendingUp,
  Heart,
  Plus,
  X,
  ChevronDown,
  CalendarDays,
} from 'lucide-react';
import PremiumShell from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import {
  listDepartments,
  getDepartmentTasks,
  getDepartmentHealth,
  createDepartmentTask,
  updateDepartmentTaskStatus,
  type Department,
  type DepartmentTask,
  type DepartmentHealthSummary,
  type CreateDepartmentTaskParams,
} from '@/services/departments';

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return 'never';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function isOverdue(dueDateStr: string | null): boolean {
  if (!dueDateStr) return false;
  return new Date(dueDateStr).getTime() < Date.now();
}

// ── Health Badge ──────────────────────────────────────────────────────────────

const HEALTH_CONFIG = {
  green: {
    dot: 'bg-emerald-500',
    text: 'text-emerald-700',
    bg: 'bg-emerald-50',
    label: 'Healthy',
    gradient: 'from-emerald-400 to-green-500',
  },
  yellow: {
    dot: 'bg-amber-400',
    text: 'text-amber-700',
    bg: 'bg-amber-50',
    label: 'At Risk',
    gradient: 'from-amber-400 to-orange-400',
  },
  red: {
    dot: 'bg-red-500',
    text: 'text-red-700',
    bg: 'bg-red-50',
    label: 'Critical',
    gradient: 'from-rose-400 to-red-500',
  },
} as const;

function HealthBadge({ status }: { status: 'green' | 'yellow' | 'red' }) {
  const cfg = HEALTH_CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
      <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

// ── Priority Badge ────────────────────────────────────────────────────────────

const PRIORITY_CONFIG = {
  urgent: { bg: 'bg-red-50', text: 'text-red-700' },
  high: { bg: 'bg-orange-50', text: 'text-orange-700' },
  medium: { bg: 'bg-blue-50', text: 'text-blue-700' },
  low: { bg: 'bg-slate-100', text: 'text-slate-600' },
} as const;

function PriorityBadge({ priority }: { priority: DepartmentTask['priority'] }) {
  const cfg = PRIORITY_CONFIG[priority];
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${cfg.bg} ${cfg.text}`}>
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
}

// ── Task Card ─────────────────────────────────────────────────────────────────

function TaskCard({
  task,
  onStatusChange,
}: {
  task: DepartmentTask;
  onStatusChange: (id: string, status: DepartmentTask['status']) => Promise<void>;
}) {
  const [updating, setUpdating] = useState(false);
  const overdue = task.status !== 'completed' && task.status !== 'cancelled' && isOverdue(task.due_date);

  async function handleAction(nextStatus: DepartmentTask['status']) {
    setUpdating(true);
    try {
      await onStatusChange(task.id, nextStatus);
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        {/* Left content */}
        <div className="flex-1 space-y-2">
          <p className="font-semibold text-slate-900">{task.title}</p>

          {/* From → To */}
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="font-medium text-slate-700">{task.from_department_name ?? 'Unknown'}</span>
            <ArrowRightLeft className="h-3 w-3 flex-shrink-0 text-slate-400" />
            <span className="font-medium text-slate-700">{task.to_department_name ?? 'Unknown'}</span>
          </div>

          {/* Badges row */}
          <div className="flex flex-wrap items-center gap-2">
            <PriorityBadge priority={task.priority} />
            <StatusBadge status={task.status} />
            {task.due_date && (
              <span className={`inline-flex items-center gap-1 text-xs ${overdue ? 'font-semibold text-red-600' : 'text-slate-400'}`}>
                <CalendarDays className="h-3 w-3" />
                {overdue ? 'Overdue · ' : ''}Due {formatDate(task.due_date)}
              </span>
            )}
            <span className="inline-flex items-center gap-1 text-xs text-slate-400">
              <Clock className="h-3 w-3" />
              {formatRelativeTime(task.created_at)}
            </span>
          </div>

          {task.description && (
            <p className="text-xs text-slate-500 line-clamp-2">{task.description}</p>
          )}
        </div>

        {/* Action button */}
        <div className="flex-shrink-0">
          {task.status === 'pending' && (
            <button
              onClick={() => handleAction('in_progress')}
              disabled={updating}
              className="inline-flex items-center gap-1.5 rounded-2xl bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition hover:bg-blue-100 disabled:opacity-50"
            >
              <PlayCircle className="h-3.5 w-3.5" />
              Start
            </button>
          )}
          {task.status === 'in_progress' && (
            <button
              onClick={() => handleAction('completed')}
              disabled={updating}
              className="inline-flex items-center gap-1.5 rounded-2xl bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-50"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Complete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Create Task Form ──────────────────────────────────────────────────────────

function CreateTaskForm({
  deptId,
  allDepartments,
  onCreated,
  onClose,
}: {
  deptId: string;
  allDepartments: Department[];
  onCreated: () => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [targetDeptId, setTargetDeptId] = useState('');
  const [priority, setPriority] = useState<CreateDepartmentTaskParams['priority']>('medium');
  const [dueDate, setDueDate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const otherDepts = allDepartments.filter((d) => d.id !== deptId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !targetDeptId) return;

    setSubmitting(true);
    setErrorMsg('');
    try {
      await createDepartmentTask({
        title: title.trim(),
        from_department_id: deptId,
        to_department_id: targetDeptId,
        description: description.trim() || undefined,
        priority,
        due_date: dueDate || undefined,
      });
      setSuccessMsg('Task created successfully!');
      setTitle('');
      setDescription('');
      setTargetDeptId('');
      setPriority('medium');
      setDueDate('');
      onCreated();
      setTimeout(() => {
        setSuccessMsg('');
        onClose();
      }, 1500);
    } catch (err) {
      setErrorMsg('Failed to create task. Please try again.');
      console.error('Create task error:', err);
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20 transition';

  const selectClass =
    'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20 transition appearance-none';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.2 }}
      className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
    >
      <div className="mb-5 flex items-center justify-between">
        <h3 className="font-semibold text-slate-900">Create Handoff Task</h3>
        <button
          onClick={onClose}
          className="rounded-xl p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {successMsg && (
        <div className="mb-4 rounded-xl bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-700">
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="mb-4 rounded-xl bg-red-50 px-4 py-2.5 text-sm font-medium text-red-700">
          {errorMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What needs to be done?"
            required
            className={inputClass}
          />
        </div>

        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional details..."
            rows={2}
            className={`${inputClass} resize-none`}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              Target Department *
            </label>
            <div className="relative">
              <select
                value={targetDeptId}
                onChange={(e) => setTargetDeptId(e.target.value)}
                required
                className={selectClass}
              >
                <option value="">Select department...</option>
                {otherDepts.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              Priority
            </label>
            <div className="relative">
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as CreateDepartmentTaskParams['priority'])}
                className={selectClass}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            </div>
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            Due Date
          </label>
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className={inputClass}
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-2xl px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !title.trim() || !targetDeptId}
            className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-500 to-blue-600 px-5 py-2 text-sm font-medium text-white shadow-sm transition hover:from-indigo-600 hover:to-blue-700 disabled:opacity-50"
          >
            {submitting ? 'Creating...' : 'Create Task'}
          </button>
        </div>
      </form>
    </motion.div>
  );
}

// ── Loading Skeleton ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <PremiumShell>
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="h-8 w-48 animate-pulse rounded-xl bg-slate-200" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-[28px] bg-slate-100" />
          ))}
        </div>
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-[28px] bg-slate-100" />
          ))}
        </div>
      </div>
    </PremiumShell>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type TaskTab = 'inbound' | 'outbound';

interface PageProps {
  params: Promise<{ deptId: string }>;
}

export default function DepartmentDetailPage({ params }: PageProps) {
  const [deptId, setDeptId] = useState<string>('');
  const [department, setDepartment] = useState<Department | null>(null);
  const [health, setHealth] = useState<DepartmentHealthSummary | null>(null);
  const [allDepartments, setAllDepartments] = useState<Department[]>([]);
  const [inboundTasks, setInboundTasks] = useState<DepartmentTask[]>([]);
  const [outboundTasks, setOutboundTasks] = useState<DepartmentTask[]>([]);
  const [activeTab, setActiveTab] = useState<TaskTab>('inbound');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [outboundLoaded, setOutboundLoaded] = useState(false);

  // Resolve params (Next.js 15 async params)
  useEffect(() => {
    params.then(({ deptId: id }) => setDeptId(id));
  }, [params]);

  const loadCoreData = useCallback(async (id: string) => {
    try {
      const [depts, healthList, tasks] = await Promise.all([
        listDepartments(),
        getDepartmentHealth(),
        getDepartmentTasks(id, 'inbound'),
      ]);
      const dept = depts.find((d) => d.id === id) ?? null;
      const deptHealth = healthList.find((h) => h.department_id === id) ?? null;
      setAllDepartments(depts);
      setDepartment(dept);
      setHealth(deptHealth);
      setInboundTasks(tasks);
    } catch (err) {
      console.error('Failed to load department detail:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (deptId) loadCoreData(deptId);
  }, [deptId, loadCoreData]);

  // Lazy-load outbound tab
  useEffect(() => {
    if (activeTab === 'outbound' && !outboundLoaded && deptId) {
      getDepartmentTasks(deptId, 'outbound')
        .then((tasks) => {
          setOutboundTasks(tasks);
          setOutboundLoaded(true);
        })
        .catch((err) => console.error('Failed to load outbound tasks:', err));
    }
  }, [activeTab, outboundLoaded, deptId]);

  async function handleStatusChange(taskId: string, status: DepartmentTask['status']) {
    await updateDepartmentTaskStatus(taskId, status);
    // Refresh current tab
    if (activeTab === 'inbound' && deptId) {
      const tasks = await getDepartmentTasks(deptId, 'inbound');
      setInboundTasks(tasks);
    } else if (activeTab === 'outbound' && deptId) {
      const tasks = await getDepartmentTasks(deptId, 'outbound');
      setOutboundTasks(tasks);
    }
    // Refresh health
    const healthList = await getDepartmentHealth();
    const deptHealth = healthList.find((h) => h.department_id === deptId) ?? null;
    setHealth(deptHealth);
  }

  function handleTaskCreated() {
    if (!deptId) return;
    // Refresh inbound tasks and health after creation
    getDepartmentTasks(deptId, 'inbound').then(setInboundTasks).catch(console.error);
    setOutboundLoaded(false); // force outbound reload next time tab is visited
    getDepartmentHealth()
      .then((list) => setHealth(list.find((h) => h.department_id === deptId) ?? null))
      .catch(console.error);
  }

  if (loading || !deptId) {
    return (
      <DashboardErrorBoundary fallbackTitle="Department Error">
        <LoadingSkeleton />
      </DashboardErrorBoundary>
    );
  }

  const healthStatus = health?.health_status ?? 'green';
  const activeTasks = health?.active_tasks ?? 0;
  const completed30d = health?.completed_30d ?? 0;
  const total30d = health?.total_30d ?? 0;
  const completionRate = total30d > 0 ? Math.round((completed30d / total30d) * 100) : 100;
  const healthCfg = HEALTH_CONFIG[healthStatus];

  const currentTasks = activeTab === 'inbound' ? inboundTasks : outboundTasks;

  return (
    <DashboardErrorBoundary fallbackTitle="Department Error">
      <PremiumShell>
        <motion.div
          className="mx-auto max-w-7xl space-y-8"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Back link */}
          <Link
            href="/departments"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            All Departments
          </Link>

          {/* Header */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-400 to-blue-500 shadow-lg">
                <Activity className="h-6 w-6 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
                    {department?.name ?? deptId}
                  </h1>
                  <HealthBadge status={healthStatus} />
                </div>
                <div className="mt-1 flex items-center gap-2">
                  {department?.type && (
                    <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-500">
                      {department.type}
                    </span>
                  )}
                  {department?.status && (
                    <span className="text-xs text-slate-400">{department.status}</span>
                  )}
                </div>
              </div>
            </div>

            <button
              onClick={() => setShowCreateForm((v) => !v)}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-500 to-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:from-indigo-600 hover:to-blue-700"
            >
              <Plus className="h-4 w-4" />
              New Handoff Task
            </button>
          </div>

          {/* Create Task Form */}
          {showCreateForm && (
            <CreateTaskForm
              deptId={deptId}
              allDepartments={allDepartments}
              onCreated={handleTaskCreated}
              onClose={() => setShowCreateForm(false)}
            />
          )}

          {/* KPI Row */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard
              label="Active Tasks"
              value={activeTasks}
              icon={ListTodo}
              gradient="from-indigo-400 to-blue-500"
              delay={0}
            />
            <MetricCard
              label="Completed (30d)"
              value={completed30d}
              icon={CheckCircle2}
              gradient="from-emerald-400 to-green-500"
              delay={0.05}
            />
            <MetricCard
              label="Completion Rate"
              value={`${completionRate}%`}
              icon={TrendingUp}
              gradient="from-violet-400 to-purple-500"
              delay={0.1}
            />
            <MetricCard
              label="Health Status"
              value={healthCfg.label}
              icon={Heart}
              gradient={healthCfg.gradient}
              delay={0.15}
            />
          </div>

          {/* Tab Bar */}
          <div className="flex items-center gap-1 rounded-2xl bg-slate-100 p-1">
            {(['inbound', 'outbound'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${
                  activeTab === tab
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <ArrowRightLeft className="h-4 w-4" />
                {tab === 'inbound' ? 'Inbound Tasks' : 'Outbound Tasks'}
              </button>
            ))}
          </div>

          {/* Task List */}
          <div className="space-y-4">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {activeTab === 'inbound' ? 'Inbound' : 'Outbound'} Tasks ({currentTasks.length})
            </h2>
            {currentTasks.length === 0 ? (
              <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                <p className="text-sm italic text-slate-400">
                  No {activeTab} tasks for this department
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {currentTasks.map((task) => (
                  <TaskCard key={task.id} task={task} onStatusChange={handleStatusChange} />
                ))}
              </div>
            )}
          </div>
        </motion.div>
      </PremiumShell>
    </DashboardErrorBoundary>
  );
}
