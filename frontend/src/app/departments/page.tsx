'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Play,
  Pause,
  RefreshCw,
  Building2,
  Zap,
  BookOpen,
  ArrowRightLeft,
  ToggleLeft,
  ToggleRight,
  Clock,
} from 'lucide-react';
import PremiumShell from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import MetricCard from '@/components/ui/MetricCard';
import StatusBadge from '@/components/ui/StatusBadge';
import {
  listDepartments,
  toggleDepartment,
  triggerDepartmentHeartbeat,
  getDepartmentTriggers,
  toggleTrigger,
  getDepartmentDecisionLog,
  getInterDeptRequests,
  type Department,
  type ProactiveTrigger,
  type DecisionLogEntry,
  type InterDeptRequest,
} from '@/services/departments';

type TabKey = 'overview' | 'triggers' | 'decisions' | 'requests';

const TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: 'overview', label: 'Overview', icon: Building2 },
  { key: 'triggers', label: 'Triggers', icon: Zap },
  { key: 'decisions', label: 'Decision Log', icon: BookOpen },
  { key: 'requests', label: 'Requests', icon: ArrowRightLeft },
];

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

/* ---------- Loading Skeleton ---------- */

function LoadingSkeleton() {
  return (
    <PremiumShell>
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="h-8 w-64 animate-pulse rounded-xl bg-slate-200" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-[28px] bg-slate-100" />
          ))}
        </div>
        <div className="h-12 animate-pulse rounded-xl bg-slate-100" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-[28px] bg-slate-100" />
          ))}
        </div>
      </div>
    </PremiumShell>
  );
}

/* ---------- Overview Tab ---------- */

function OverviewTab({
  departments,
  onToggle,
}: {
  departments: Department[];
  onToggle: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
        Departments ({departments.length})
      </h2>
      {departments.length === 0 ? (
        <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
          <p className="text-sm text-slate-400 italic">No departments configured</p>
        </div>
      ) : (
        <div className="space-y-3">
          {departments.map((dept) => (
            <div
              key={dept.id}
              className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className={`h-3 w-3 rounded-full ${
                      dept.status === 'RUNNING' ? 'bg-green-500 animate-pulse' : dept.status === 'ERROR' ? 'bg-red-500' : 'bg-amber-500'
                    }`}
                  />
                  <div>
                    <p className="font-semibold text-slate-900">{dept.name}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                        {dept.type}
                      </span>
                      <span className="text-xs text-slate-400">
                        Last heartbeat: {formatRelativeTime(dept.last_heartbeat)}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => onToggle(dept.id)}
                  className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-medium transition ${
                    dept.status === 'RUNNING'
                      ? 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                      : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                  }`}
                >
                  {dept.status === 'RUNNING' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  {dept.status === 'RUNNING' ? 'Pause' : 'Start'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Triggers Tab ---------- */

function TriggersTab({
  triggers,
  onToggle,
}: {
  triggers: ProactiveTrigger[];
  onToggle: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
        Proactive Triggers ({triggers.length})
      </h2>
      {triggers.length === 0 ? (
        <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
          <Zap className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-3 text-sm text-slate-400 italic">No triggers configured</p>
        </div>
      ) : (
        <div className="space-y-3">
          {triggers.map((trigger) => (
            <div
              key={trigger.id}
              className="flex items-center justify-between rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
            >
              <div className="space-y-1">
                <p className="font-semibold text-slate-900">{trigger.name}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={trigger.condition_type} />
                  <span className="text-xs text-slate-400">Action: {trigger.action_type}</span>
                  <span className="text-xs text-slate-400">
                    Cooldown: {trigger.cooldown_hours}h | Max: {trigger.max_triggers_per_day}/day
                  </span>
                  {trigger.last_triggered_at && (
                    <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                      <Clock className="h-3 w-3" />
                      Last: {formatRelativeTime(trigger.last_triggered_at)}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => onToggle(trigger.id)}
                className={`flex-shrink-0 ${trigger.enabled ? 'text-emerald-500' : 'text-slate-300'} transition hover:opacity-80`}
                title={trigger.enabled ? 'Disable trigger' : 'Enable trigger'}
              >
                {trigger.enabled ? <ToggleRight className="h-8 w-8" /> : <ToggleLeft className="h-8 w-8" />}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Decision Log Tab ---------- */

function DecisionLogTab({ decisions }: { decisions: DecisionLogEntry[] }) {
  return (
    <div className="space-y-4">
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
        Decision Log — Last 24h ({decisions.length})
      </h2>
      {decisions.length === 0 ? (
        <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
          <p className="text-sm text-slate-400 italic">No decisions in the last 24 hours</p>
        </div>
      ) : (
        <div className="rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left">
                  <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Time</th>
                  <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Department</th>
                  <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Type</th>
                  <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Outcome</th>
                  <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Logic</th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((d) => (
                  <tr key={d.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                    <td className="px-5 py-3 text-xs text-slate-500 whitespace-nowrap">
                      {formatRelativeTime(d.cycle_timestamp)}
                    </td>
                    <td className="px-5 py-3 font-medium text-slate-900">{d.department_name || 'Unknown'}</td>
                    <td className="px-5 py-3"><StatusBadge status={d.decision_type} /></td>
                    <td className="px-5 py-3"><StatusBadge status={d.outcome} /></td>
                    <td className="px-5 py-3 text-xs text-slate-500 max-w-xs truncate">{d.decision_logic || '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Requests Tab ---------- */

function RequestsTab({ requests }: { requests: InterDeptRequest[] }) {
  return (
    <div className="space-y-4">
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
        Inter-Department Requests ({requests.length})
      </h2>
      {requests.length === 0 ? (
        <div className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
          <p className="text-sm text-slate-400 italic">No inter-department requests</p>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((req) => (
            <div
              key={req.id}
              className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900">{req.from_department_name}</span>
                    <ArrowRightLeft className="h-4 w-4 text-slate-400" />
                    <span className="font-semibold text-slate-900">{req.to_department_name}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={req.request_type} />
                    <StatusBadge status={req.status} />
                    <span className="text-xs text-slate-400">Priority: {req.priority}</span>
                    <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                      <Clock className="h-3 w-3" />
                      {formatRelativeTime(req.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Main Page ---------- */

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [triggers, setTriggers] = useState<ProactiveTrigger[]>([]);
  const [decisions, setDecisions] = useState<DecisionLogEntry[]>([]);
  const [requests, setRequests] = useState<InterDeptRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [ticking, setTicking] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  const fetchAll = useCallback(async () => {
    try {
      const depts = await listDepartments();
      setDepartments(depts);
    } catch (err) {
      console.error('Failed to load departments:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load departments on mount + poll
  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  // Lazy-load tab data
  useEffect(() => {
    let cancelled = false;
    async function loadTabData() {
      try {
        if (activeTab === 'triggers') {
          const data = await getDepartmentTriggers();
          if (!cancelled) setTriggers(data);
        } else if (activeTab === 'decisions') {
          const data = await getDepartmentDecisionLog();
          if (!cancelled) setDecisions(data);
        } else if (activeTab === 'requests') {
          const data = await getInterDeptRequests();
          if (!cancelled) setRequests(data);
        }
      } catch (err) {
        console.error(`Failed to load ${activeTab} data:`, err);
      }
    }
    loadTabData();
    return () => { cancelled = true; };
  }, [activeTab]);

  const handleToggleDept = async (id: string) => {
    await toggleDepartment(id);
    fetchAll();
  };

  const handleToggleTrigger = async (id: string) => {
    await toggleTrigger(id);
    const data = await getDepartmentTriggers();
    setTriggers(data);
  };

  const handleManualTick = async () => {
    setTicking(true);
    try {
      await triggerDepartmentHeartbeat();
      fetchAll();
    } finally {
      setTicking(false);
    }
  };

  const runningCount = departments.filter((d) => d.status === 'RUNNING').length;
  const pausedCount = departments.filter((d) => d.status === 'PAUSED').length;
  const errorCount = departments.filter((d) => d.status === 'ERROR').length;

  if (loading) {
    return (
      <DashboardErrorBoundary fallbackTitle="Departments Error">
        <LoadingSkeleton />
      </DashboardErrorBoundary>
    );
  }

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
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-400 to-blue-500 shadow-lg">
                <Building2 className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                  Autonomous Departments
                </h1>
                <p className="text-sm text-slate-500">Manage your 24/7 AI workforce</p>
              </div>
            </div>
            <button
              onClick={handleManualTick}
              disabled={ticking}
              className="inline-flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-200 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${ticking ? 'animate-spin' : ''}`} />
              Force Heartbeat
            </button>
          </div>

          {/* KPI Row */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard
              label="Total"
              value={departments.length}
              icon={Building2}
              gradient="from-indigo-400 to-blue-500"
              delay={0}
            />
            <MetricCard
              label="Running"
              value={runningCount}
              icon={Play}
              gradient="from-emerald-400 to-green-500"
              delay={0.05}
            />
            <MetricCard
              label="Paused"
              value={pausedCount}
              icon={Pause}
              gradient="from-amber-400 to-orange-500"
              delay={0.1}
            />
            <MetricCard
              label="Errors"
              value={errorCount}
              icon={Zap}
              gradient="from-rose-400 to-red-500"
              delay={0.15}
            />
          </div>

          {/* Tab Bar */}
          <div className="flex items-center gap-1 rounded-2xl bg-slate-100 p-1">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${
                    activeTab === tab.key
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && (
            <OverviewTab departments={departments} onToggle={handleToggleDept} />
          )}
          {activeTab === 'triggers' && (
            <TriggersTab triggers={triggers} onToggle={handleToggleTrigger} />
          )}
          {activeTab === 'decisions' && <DecisionLogTab decisions={decisions} />}
          {activeTab === 'requests' && <RequestsTab requests={requests} />}
        </motion.div>
      </PremiumShell>
    </DashboardErrorBoundary>
  );
}
