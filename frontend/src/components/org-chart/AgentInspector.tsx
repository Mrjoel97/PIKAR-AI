'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useState } from 'react';
import {
    X,
    Brain,
    Wrench,
    ChevronDown,
    ChevronRight,
    Cpu,
    Activity,
    Zap,
} from 'lucide-react';

// Matches the enhanced OrgNode returned by the backend
export interface OrgNodeData {
    id: string;
    type: 'user' | 'agent';
    label: string;
    role?: string;
    reports_to?: string;
    status: 'active' | 'idle' | 'offline' | 'busy';
    tools: string[];
    tool_kinds?: Record<string, string>;
    tool_count: number;
    capabilities: string;
    model: string;
    // Live activity fields
    last_activity_at?: string | null;
    active_workflows: number;
    recent_decisions: number;
}

interface AgentInspectorProps {
    agent: OrgNodeData | null; // null = closed
    onClose: () => void;
}

function timeAgo(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Never';
    const diff = Date.now() - new Date(dateStr).getTime();
    if (diff < 0) return 'Just now';
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

function StatusDot({ status }: { status: string }) {
    const color =
        status === 'active'
            ? 'bg-emerald-400'
            : status === 'busy'
              ? 'bg-amber-400'
              : 'bg-slate-500';

    return (
        <span className="relative flex h-3 w-3">
            {status === 'active' && (
                <span
                    className={`absolute inline-flex h-full w-full animate-ping rounded-full ${color} opacity-75`}
                />
            )}
            <span className={`relative inline-flex h-3 w-3 rounded-full ${color}`} />
        </span>
    );
}

function CollapsibleSection({
    title,
    icon: Icon,
    defaultOpen = true,
    badge,
    children,
}: {
    title: string;
    icon: React.ElementType;
    defaultOpen?: boolean;
    badge?: string | number;
    children: React.ReactNode;
}) {
    const [open, setOpen] = useState(defaultOpen);

    return (
        <div className="border-t border-slate-700/50">
            <button
                onClick={() => setOpen(!open)}
                className="flex w-full items-center gap-2 px-5 py-3 text-left text-sm font-semibold text-slate-300 transition-colors hover:bg-slate-700/30"
            >
                {open ? (
                    <ChevronDown className="h-4 w-4 text-slate-500" />
                ) : (
                    <ChevronRight className="h-4 w-4 text-slate-500" />
                )}
                <Icon className="h-4 w-4 text-indigo-400" />
                <span>{title}</span>
                {badge !== undefined && (
                    <span className="ml-auto rounded-full bg-indigo-500/20 px-2 py-0.5 text-xs font-medium text-indigo-300">
                        {badge}
                    </span>
                )}
            </button>
            {open && <div className="px-5 pb-4">{children}</div>}
        </div>
    );
}

function ToolKindBadge({ kind }: { kind: string | undefined }) {
    if (!kind) return null;
    if (kind === 'action') {
        return (
            <span className="ml-auto shrink-0 rounded-full bg-blue-50 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
                ACTION
            </span>
        );
    }
    if (kind === 'knowledge') {
        return (
            <span className="ml-auto shrink-0 rounded-full bg-amber-50 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-amber-600 dark:bg-amber-900/30 dark:text-amber-400">
                GUIDE
            </span>
        );
    }
    return null;
}

export default function AgentInspector({ agent, onClose }: AgentInspectorProps) {
    if (!agent) return null;

    const isAgent = agent.type === 'agent';

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Slide-in panel */}
            <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col overflow-hidden bg-slate-800 shadow-2xl transition-transform duration-300 ease-out border-l border-slate-700">
                {/* Header */}
                <div className="flex items-start gap-4 bg-gradient-to-r from-slate-800 to-slate-900 px-5 py-5">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg">
                        {isAgent ? (
                            <Cpu className="h-6 w-6 text-white" />
                        ) : (
                            <Zap className="h-6 w-6 text-white" />
                        )}
                    </div>
                    <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                            <h2 className="truncate text-lg font-bold text-white">
                                {agent.label}
                            </h2>
                            <StatusDot status={agent.status} />
                        </div>
                        <p className="mt-0.5 text-sm text-slate-400">{agent.role}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto">
                    {/* Brain section */}
                    <CollapsibleSection title="Brain" icon={Brain} defaultOpen={true}>
                        <div className="space-y-3">
                            {/* Live status */}
                            <div className="flex items-center gap-2 rounded-lg bg-slate-700/40 px-3 py-2">
                                <Activity className="h-4 w-4 shrink-0 text-emerald-400" />
                                <div className="flex-1">
                                    <div className="flex items-center justify-between">
                                        <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
                                            Status
                                        </div>
                                        <span
                                            className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
                                                agent.status === 'active'
                                                    ? 'bg-emerald-500/20 text-emerald-300'
                                                    : agent.status === 'busy'
                                                      ? 'bg-amber-500/20 text-amber-300'
                                                      : 'bg-slate-600/40 text-slate-400'
                                            }`}
                                        >
                                            <StatusDot status={agent.status} />
                                            {agent.status === 'active'
                                                ? 'Active'
                                                : agent.status === 'busy'
                                                  ? 'Busy'
                                                  : agent.status === 'idle'
                                                    ? 'Idle'
                                                    : 'Offline'}
                                        </span>
                                    </div>
                                    {isAgent && (
                                        <div className="mt-1 text-sm text-slate-400">
                                            Last active: {timeAgo(agent.last_activity_at)}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Activity metrics */}
                            {isAgent && (
                                <div className="grid grid-cols-2 gap-2">
                                    <div className="rounded-lg bg-slate-700/40 px-3 py-2 text-center">
                                        <div className="text-lg font-bold text-indigo-300">
                                            {agent.active_workflows}
                                        </div>
                                        <div className="text-xs text-slate-500">
                                            {agent.active_workflows === 1
                                                ? 'workflow running'
                                                : 'workflows running'}
                                        </div>
                                    </div>
                                    <div className="rounded-lg bg-slate-700/40 px-3 py-2 text-center">
                                        <div className="text-lg font-bold text-purple-300">
                                            {agent.recent_decisions}
                                        </div>
                                        <div className="text-xs text-slate-500">
                                            {agent.recent_decisions === 1
                                                ? 'decision (24h)'
                                                : 'decisions (24h)'}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Model */}
                            {agent.model && (
                                <div className="flex items-center gap-2 rounded-lg bg-slate-700/40 px-3 py-2">
                                    <Cpu className="h-4 w-4 shrink-0 text-purple-400" />
                                    <div>
                                        <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
                                            Model
                                        </div>
                                        <div className="text-sm font-medium text-slate-200">
                                            {agent.model}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Capabilities */}
                            {agent.capabilities && (
                                <div className="rounded-lg bg-slate-700/40 px-3 py-2">
                                    <div className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                                        Capabilities
                                    </div>
                                    <p className="text-sm leading-relaxed text-slate-300">
                                        {agent.capabilities}
                                    </p>
                                </div>
                            )}
                        </div>
                    </CollapsibleSection>

                    {/* Hands section */}
                    <CollapsibleSection
                        title="Hands"
                        icon={Wrench}
                        defaultOpen={true}
                        badge={agent.tool_count}
                    >
                        {agent.tools.length > 0 ? (
                            <ul className="max-h-80 space-y-1 overflow-y-auto pr-1">
                                {agent.tools.map((tool) => (
                                    <li
                                        key={tool}
                                        className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-slate-300 transition-colors hover:bg-slate-700/40"
                                    >
                                        <Wrench className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                                        <span className="font-mono text-xs">{tool}</span>
                                        <ToolKindBadge kind={agent.tool_kinds?.[tool]} />
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="text-sm italic text-slate-500">
                                No direct tools &mdash; delegates to sub-agents
                            </p>
                        )}
                    </CollapsibleSection>
                </div>

                {/* Footer */}
                <div className="border-t border-slate-700/50 bg-slate-800/80 px-5 py-3">
                    <p className="text-center text-xs text-slate-500">
                        Agent ID: <span className="font-mono">{agent.id}</span>
                    </p>
                </div>
            </div>
        </>
    );
}
