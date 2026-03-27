'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React from 'react';
import { WidgetProps } from './WidgetRegistry';
import { APIConnectionsWidgetData, APIConnectionData } from '@/types/widgets';
import { Link2, Unplug, Server, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

function statusColor(status: string): string {
    switch (status) {
        case 'healthy':
            return 'bg-emerald-500';
        case 'stale':
            return 'bg-amber-500';
        case 'error':
            return 'bg-red-500';
        default:
            return 'bg-slate-400';
    }
}

function StatusIcon({ status }: { status: string }) {
    switch (status) {
        case 'healthy':
            return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
        case 'stale':
            return <AlertTriangle className="w-4 h-4 text-amber-500" />;
        case 'error':
            return <XCircle className="w-4 h-4 text-red-500" />;
        default:
            return <CheckCircle2 className="w-4 h-4 text-slate-400" />;
    }
}

function relativeTime(dateStr: string): string {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        if (diffHours < 1) return 'Connected just now';
        if (diffHours < 24) return `Connected ${diffHours}h ago`;
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays === 1) return 'Connected 1 day ago';
        return `Connected ${diffDays} days ago`;
    } catch {
        return '';
    }
}

function ConnectionCard({
    connection,
    onDisconnect,
}: {
    connection: APIConnectionData;
    onDisconnect: () => void;
}) {
    return (
        <div className="group flex items-center justify-between p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-sm transition-all bg-slate-50/50 dark:bg-slate-800/50">
            <div className="flex items-center gap-3 min-w-0">
                <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
                    <Server className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div className="min-w-0">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                            {connection.api_name}
                        </span>
                        <span className="flex-shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400">
                            {connection.endpoint_count} endpoint{connection.endpoint_count !== 1 ? 's' : ''}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                        <div className="flex items-center gap-1">
                            <div className={`w-1.5 h-1.5 rounded-full ${statusColor(connection.status)}`} />
                            <StatusIcon status={connection.status} />
                            <span className="text-[11px] text-slate-500 dark:text-slate-400 capitalize">
                                {connection.status}
                            </span>
                        </div>
                        {connection.connected_at && (
                            <span className="text-[11px] text-slate-400 dark:text-slate-500">
                                {relativeTime(connection.connected_at)}
                            </span>
                        )}
                    </div>
                </div>
            </div>
            <button
                onClick={onDisconnect}
                className="flex-shrink-0 p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 transition-all"
                title={`Disconnect ${connection.api_name}`}
                aria-label={`Disconnect ${connection.api_name}`}
            >
                <Unplug className="w-4 h-4 text-slate-400 hover:text-red-500" />
            </button>
        </div>
    );
}

export default function APIConnectionsWidget({ definition, onAction }: WidgetProps) {
    const data = definition.data as unknown as APIConnectionsWidgetData;
    const connections = data?.connections || [];

    if (connections.length === 0) {
        return (
            <div className="p-6 text-center text-slate-500 dark:text-slate-400">
                <Link2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm font-medium mb-1">No APIs connected</p>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                    Ask your agent to connect an API by providing an OpenAPI spec URL.
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-white dark:bg-slate-900">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Link2 className="w-5 h-5 text-indigo-500" />
                    <div>
                        <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                            {definition.title || 'API Connections'}
                        </h3>
                        <p className="text-xs text-slate-500">
                            External services connected via OpenAPI
                        </p>
                    </div>
                </div>
                <div className="text-xs font-medium px-2 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-full">
                    {connections.length} Connected
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {connections.map((connection) => (
                    <ConnectionCard
                        key={connection.api_name}
                        connection={connection}
                        onDisconnect={() =>
                            onAction?.('disconnect_api', { api_name: connection.api_name })
                        }
                    />
                ))}
            </div>
        </div>
    );
}
