'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview /dashboard/team — Team Dashboard page.
 *
 * Gated to startup+ tier via GatedPage. Shows aggregate KPI tiles, per-member
 * breakdown for admins, shared initiatives/workflows tabs, resource-grouped
 * activity feed, team member list, invite link generator, and role reference.
 * Uses WorkspaceContext for workspace state.
 */

import React, { useState, useEffect } from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { PermissionGate } from '@/components/ui/PermissionGate';
import { UpgradePrompt } from '@/components/ui/UpgradePrompt';
import { TeamMemberList } from '@/components/team/TeamMemberList';
import { InviteLinkGenerator } from '@/components/team/InviteLinkGenerator';
import { useWorkspace } from '@/contexts/WorkspaceContext';
import { useFeatureGate } from '@/hooks/useFeatureGate';
import { fetchWithAuth } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

interface TeamKPIs {
    total_initiatives: number;
    total_workflows: number;
    active_workflows: number;
    total_tasks: number;
    total_approvals: number;
    member_count: number;
}

interface MemberKPI {
    user_id: string;
    display_name: string;
    email: string;
    initiative_count: number;
    workflow_count: number;
    task_count: number;
}

interface SharedInitiative {
    id: string;
    name: string;
    status?: string;
    updated_at?: string;
    created_by?: string;
}

interface SharedWorkflow {
    id: string;
    template_name: string;
    status?: string;
    updated_at?: string;
    created_by?: string;
}

interface ActivityEvent {
    action_type: string;
    user_id: string;
    created_at: string;
    details?: Record<string, unknown>;
}

interface ActivityCluster {
    resource_type: string;
    resource_id: string;
    resource_name: string;
    events: ActivityEvent[];
}

// ============================================================================
// Loading shimmer
// ============================================================================

function TeamPageShimmer() {
    return (
        <div className="flex flex-col gap-6 animate-pulse">
            <div className="h-8 w-48 rounded-xl bg-slate-100" />
            <div className="h-4 w-64 rounded bg-slate-100" />
            <div className="h-32 rounded-2xl bg-slate-100" />
            <div className="h-64 rounded-2xl bg-slate-100" />
            <div className="h-40 rounded-2xl bg-slate-100" />
        </div>
    );
}

// ============================================================================
// TeamKPITiles
// ============================================================================

const KPI_LABELS: Array<{ key: keyof TeamKPIs; label: string }> = [
    { key: 'total_initiatives', label: 'Initiatives' },
    { key: 'total_workflows', label: 'Total Workflows' },
    { key: 'active_workflows', label: 'Active Workflows' },
    { key: 'total_tasks', label: 'Tasks' },
    { key: 'total_approvals', label: 'Pending Approvals' },
    { key: 'member_count', label: 'Team Members' },
];

function TeamKPITiles() {
    const [kpis, setKpis] = useState<TeamKPIs | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchWithAuth('/teams/analytics')
            .then((data: unknown) => {
                const d = data as { kpis?: TeamKPIs };
                setKpis(d.kpis ?? (data as TeamKPIs));
            })
            .catch(() => setKpis(null))
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm animate-pulse h-24" />
                ))}
            </div>
        );
    }

    if (!kpis) return null;

    return (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {KPI_LABELS.map(({ key, label }) => (
                <div key={key} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
                    <p className="text-3xl font-bold text-slate-900">{kpis[key] ?? 0}</p>
                    <p className="text-sm text-slate-500 mt-1">{label}</p>
                </div>
            ))}
        </div>
    );
}

// ============================================================================
// MemberBreakdown (admin only)
// ============================================================================

function MemberBreakdown() {
    const [members, setMembers] = useState<MemberKPI[]>([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        fetchWithAuth('/teams/analytics')
            .then((data: unknown) => {
                const d = data as { member_breakdown?: MemberKPI[] | null };
                setMembers(d.member_breakdown ?? []);
            })
            .catch(() => setMembers([]))
            .finally(() => setLoading(false));
    }, []);

    if (loading || members.length === 0) return null;

    return (
        <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
            <button
                onClick={() => setExpanded((v) => !v)}
                className="flex items-center justify-between w-full text-left"
            >
                <h2 className="text-base font-semibold text-slate-900">Per-Member Breakdown</h2>
                <svg
                    className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>
            {expanded && (
                <div className="mt-4 overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-slate-500 uppercase tracking-wide border-b border-slate-100">
                                <th className="text-left pb-2 font-medium">Member</th>
                                <th className="text-right pb-2 font-medium">Initiatives</th>
                                <th className="text-right pb-2 font-medium">Workflows</th>
                                <th className="text-right pb-2 font-medium">Tasks</th>
                            </tr>
                        </thead>
                        <tbody>
                            {members.map((m) => (
                                <tr key={m.user_id} className="border-b border-slate-50 last:border-0">
                                    <td className="py-2">
                                        <p className="font-medium text-slate-800">{m.display_name || m.email}</p>
                                        {m.display_name && <p className="text-xs text-slate-400">{m.email}</p>}
                                    </td>
                                    <td className="py-2 text-right text-slate-600">{m.initiative_count}</td>
                                    <td className="py-2 text-right text-slate-600">{m.workflow_count}</td>
                                    <td className="py-2 text-right text-slate-600">{m.task_count}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    );
}

// ============================================================================
// SharedWork (tabs for initiatives + workflows)
// ============================================================================

function SharedWork() {
    const [tab, setTab] = useState<'initiatives' | 'workflows'>('initiatives');
    const [initiatives, setInitiatives] = useState<SharedInitiative[]>([]);
    const [workflows, setWorkflows] = useState<SharedWorkflow[]>([]);
    const [loading, setLoading] = useState(false);
    const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set());

    async function loadTab(t: 'initiatives' | 'workflows') {
        if (loadedTabs.has(t)) return;
        setLoading(true);
        try {
            if (t === 'initiatives') {
                const data = await fetchWithAuth('/teams/shared/initiatives') as SharedInitiative[] | { initiatives?: SharedInitiative[] };
                setInitiatives(Array.isArray(data) ? data : (data.initiatives ?? []));
            } else {
                const data = await fetchWithAuth('/teams/shared/workflows') as SharedWorkflow[] | { workflows?: SharedWorkflow[] };
                setWorkflows(Array.isArray(data) ? data : (data.workflows ?? []));
            }
            setLoadedTabs((prev) => new Set([...prev, t]));
        } catch {
            // silently handle
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        void loadTab('initiatives');
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    function handleTabChange(t: 'initiatives' | 'workflows') {
        setTab(t);
        void loadTab(t);
    }

    const items = tab === 'initiatives' ? initiatives : workflows;

    return (
        <section className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-100 px-6 pt-4 pb-0">
                <h2 className="text-base font-semibold text-slate-900 mb-3">Shared Work</h2>
                <div className="flex gap-1">
                    {(['initiatives', 'workflows'] as const).map((t) => (
                        <button
                            key={t}
                            onClick={() => handleTabChange(t)}
                            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                                tab === t
                                    ? 'bg-white text-teal-700 border-t border-l border-r border-slate-200 -mb-px'
                                    : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            {t === 'initiatives' ? 'Shared Initiatives' : 'Shared Workflows'}
                        </button>
                    ))}
                </div>
            </div>
            <div className="p-6">
                {loading ? (
                    <div className="space-y-3">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-10 rounded-xl bg-slate-100 animate-pulse" />
                        ))}
                    </div>
                ) : items.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-6">
                        No shared {tab} yet.
                    </p>
                ) : (
                    <div className="space-y-2">
                        {items.map((item) => (
                            <div key={item.id} className="flex items-center gap-3 rounded-xl bg-slate-50 px-4 py-3">
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-slate-800 truncate">
                                        {'name' in item ? item.name : (item as SharedWorkflow).template_name}
                                    </p>
                                    <div className="flex items-center gap-2 mt-0.5">
                                        {item.status && (
                                            <span className="text-xs text-slate-500 capitalize">{item.status}</span>
                                        )}
                                        {item.updated_at && (
                                            <span className="text-xs text-slate-400">
                                                Updated {new Date(item.updated_at).toLocaleDateString()}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                {item.created_by && (
                                    <span className="text-xs text-slate-400 shrink-0">{item.created_by}</span>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </section>
    );
}

// ============================================================================
// ActivityFeed
// ============================================================================

function relativeTime(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
}

function ActivityFeed() {
    const [clusters, setClusters] = useState<ActivityCluster[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchWithAuth('/teams/activity')
            .then((data: unknown) => {
                const d = data as ActivityCluster[] | { activity?: ActivityCluster[] };
                setClusters(Array.isArray(d) ? d : (d.activity ?? []));
            })
            .catch(() => setClusters([]))
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
                <h2 className="text-base font-semibold text-slate-900 mb-4">Activity</h2>
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-16 rounded-xl bg-slate-100 animate-pulse" />
                    ))}
                </div>
            </section>
        );
    }

    if (clusters.length === 0) {
        return (
            <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
                <h2 className="text-base font-semibold text-slate-900 mb-2">Activity</h2>
                <p className="text-sm text-slate-400">No recent activity in your workspace.</p>
            </section>
        );
    }

    return (
        <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900 mb-4">Activity</h2>
            <div className="space-y-4">
                {clusters.map((cluster) => (
                    <div key={cluster.resource_id} className="rounded-xl border border-slate-100 bg-slate-50 overflow-hidden">
                        <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-100/80 border-b border-slate-100">
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                                {cluster.resource_type}
                            </span>
                            <span className="text-sm font-medium text-slate-800 truncate">{cluster.resource_name}</span>
                        </div>
                        <div className="divide-y divide-slate-100">
                            {cluster.events.slice(0, 5).map((ev, idx) => (
                                <div key={idx} className="flex items-center gap-3 px-4 py-2 text-xs">
                                    <span className="w-2 h-2 rounded-full bg-teal-400 shrink-0" />
                                    <span className="text-slate-700 font-medium capitalize">{ev.action_type.replace(/_/g, ' ')}</span>
                                    <span className="text-slate-400 truncate">by {ev.user_id}</span>
                                    <span className="text-slate-400 ml-auto shrink-0">{relativeTime(ev.created_at)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}

// ============================================================================
// Role info card
// ============================================================================

const ROLES = [
    {
        name: 'Admin',
        color: 'indigo',
        description: 'Full access — can manage team members, change roles, and access billing.',
    },
    {
        name: 'Editor',
        color: 'emerald',
        description: 'Can create and edit initiatives, workflows, and content. Cannot manage the team.',
    },
    {
        name: 'Viewer',
        color: 'amber',
        description: 'Read-only access to all shared workspace content.',
    },
] as const;

function RoleInfoCard() {
    return (
        <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-base font-semibold text-slate-900">Role Reference</h2>
            <div className="flex flex-col gap-3">
                {ROLES.map((r) => (
                    <div key={r.name} className="flex items-start gap-3">
                        <span
                            className={[
                                'mt-0.5 shrink-0 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold',
                                r.color === 'indigo'
                                    ? 'bg-indigo-100 text-indigo-700'
                                    : r.color === 'emerald'
                                    ? 'bg-emerald-100 text-emerald-700'
                                    : 'bg-amber-100 text-amber-700',
                            ].join(' ')}
                        >
                            {r.name[0]}
                        </span>
                        <div>
                            <p className="text-sm font-medium text-slate-800">{r.name}</p>
                            <p className="text-xs text-slate-500">{r.description}</p>
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}

// ============================================================================
// Page content (inside GatedPage)
// ============================================================================

function TeamAnalytics() {
    const { ready, workspaceId, workspaceName, role, isOwner } = useWorkspace();
    // AUTH-03: workspace RBAC (member list + role management) is always available.
    // Plan 49-03 ships an un-gated sibling router (app/routers/teams_rbac.py) for
    // the PATCH role endpoint so the upgrade prompt only applies to team analytics
    // widgets (KPIs, member breakdown, shared work, activity feed). The member
    // list and invite generator remain accessible to any workspace admin.
    const teamsGate = useFeatureGate('teams');

    if (!ready) {
        return <TeamPageShimmer />;
    }

    const isAdminOrOwner = isOwner || role === 'admin' || role === 'owner';
    const ownerPlaceholder = '';
    const analyticsAllowed = teamsGate.allowed && !teamsGate.isLoading;

    return (
        <div className="flex flex-col gap-6">
            {/* Page header */}
            <div>
                <h1 className="text-2xl font-bold text-slate-900">Team Dashboard</h1>
                {workspaceName && (
                    <p className="mt-1 text-sm text-slate-500">
                        Workspace: <span className="font-medium text-slate-700">{workspaceName}</span>
                    </p>
                )}
            </div>

            {/* Team analytics widgets — gated to startup+ tier (the `teams` feature). */}
            {analyticsAllowed ? (
                <>
                    {/* KPI tiles — aggregate stats */}
                    <TeamKPITiles />

                    {/* Per-member breakdown — admin only */}
                    {isAdminOrOwner && <MemberBreakdown />}

                    {/* Shared initiatives + workflows tabs */}
                    <SharedWork />

                    {/* Resource-grouped activity feed */}
                    <ActivityFeed />
                </>
            ) : (
                !teamsGate.isLoading && (
                    <UpgradePrompt featureKey="teams" variant="card" />
                )
            )}

            {/* Team member list — visible to all roles, available on every tier
                because AUTH-03 ships an un-gated PATCH /teams/members/{uid}/role. */}
            {workspaceId ? (
                <TeamMemberList
                    workspaceId={workspaceId}
                    currentUserRole={role}
                    ownerId={ownerPlaceholder}
                />
            ) : (
                <div className="rounded-2xl border border-slate-100 bg-white px-6 py-10 text-center shadow-sm">
                    <p className="text-sm text-slate-500">
                        Your workspace is being set up. Refresh in a moment.
                    </p>
                </div>
            )}

            {/* Invite section — admin only, available on every tier (un-gated). */}
            {workspaceId && (
                <PermissionGate require="manage-team" fallback="hide">
                    <InviteLinkGenerator workspaceId={workspaceId} />
                </PermissionGate>
            )}

            {/* Role reference card */}
            <RoleInfoCard />
        </div>
    );
}

// ============================================================================
// Page
// ============================================================================

export default function TeamPage() {
    // AUTH-03 (Phase 49 Plan 03): the page is no longer wrapped in
    // <GatedPage featureKey="teams"> so workspace admins on any tier can reach
    // the member list and role-management UI. The `teams` feature gate now
    // applies only to the analytics widgets inside <TeamAnalytics> via
    // useFeatureGate('teams').
    return (
        <DashboardErrorBoundary fallbackTitle="Team Error">
            <PremiumShell>
                <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
                    <TeamAnalytics />
                </div>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
