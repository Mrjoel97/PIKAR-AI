'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React from 'react';
import { useSessionMap } from '@/contexts/SessionMapContext';
import { useSessionControl } from '@/contexts/SessionControlContext';
import { MessageSquare, Trash2, Clock, Loader2 } from 'lucide-react';
import { SessionStatusBadge } from './SessionStatusBadge';
import { NewChatButton } from './NewChatButton';

interface SessionListProps {
    onSelectSession: (sessionId: string) => void;
    className?: string;
}

export function SessionList({ onSelectSession, className = '' }: SessionListProps) {
    const { sessions, isLoadingSessions, activeSessions } = useSessionMap();
    const { visibleSessionId, deleteChat } = useSessionControl();

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (isLoadingSessions) {
        return (
            <div className={`flex flex-col items-center justify-center p-8 text-slate-400 ${className}`}>
                <Loader2 className="w-6 h-6 animate-spin mb-2" />
                <span className="text-sm">Loading history...</span>
            </div>
        );
    }

    if (sessions.length === 0) {
        return (
            <div className={`p-8 text-center text-slate-500 text-sm ${className}`}>
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No past conversations</p>
            </div>
        );
    }

    // Split sessions into active (streaming or hasUnread) and the rest
    const activeSessions_ = sessions.filter((session) => {
        const state = activeSessions.get(session.id);
        return state && (state.status === 'streaming' || state.hasUnread);
    });
    const restSessions = sessions.filter((session) => {
        const state = activeSessions.get(session.id);
        return !state || (state.status !== 'streaming' && !state.hasUnread);
    });
    const hasActiveSessions = activeSessions_.length > 0;

    const renderSession = (session: typeof sessions[number]) => {
        const activeState = activeSessions.get(session.id);
        const isStreaming = activeState?.status === 'streaming';
        const hasUnread = activeState?.hasUnread ?? false;
        const isCurrent = visibleSessionId === session.id;

        return (
            <div
                key={session.id}
                className={`
                    group flex items-center justify-between p-3 rounded-lg transition-colors cursor-pointer border
                    ${isCurrent
                        ? 'bg-indigo-50 border-indigo-200 dark:bg-indigo-900/20 dark:border-indigo-800'
                        : 'bg-white border-transparent hover:bg-slate-50 dark:bg-slate-800/50 dark:hover:bg-slate-800 dark:border-slate-800'
                    }
                `}
                onClick={() => onSelectSession(session.id)}
            >
                <div className="flex flex-col min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                        <MessageSquare size={14} className={isCurrent ? 'text-indigo-500' : 'text-slate-400'} />
                        <span className={`text-sm font-medium truncate ${isCurrent
                                ? 'text-indigo-700 dark:text-indigo-300'
                                : 'text-slate-700 dark:text-slate-200'
                            }`}>
                            {session.title || `Session ${session.id.slice(0, 8)}`}
                        </span>
                        <span className="ml-auto shrink-0">
                            <SessionStatusBadge
                                status={activeState?.status ?? 'idle'}
                                hasUnread={hasUnread}
                            />
                        </span>
                    </div>

                    <div className="flex items-center gap-1 text-xs text-slate-400">
                        <Clock size={10} />
                        <span>{formatDate(session.updatedAt || session.createdAt)}</span>
                    </div>
                </div>

                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        if (confirm('Are you sure you want to delete this session?')) {
                            deleteChat(session.id);
                        }
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-500 rounded transition"
                    title="Delete session"
                >
                    <Trash2 size={14} />
                </button>
            </div>
        );
    };

    return (
        <div className={`flex flex-col space-y-2 max-h-[600px] overflow-y-auto ${className}`}>
            <div className="px-1 mb-1">
                <NewChatButton />
            </div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2 mb-2">
                Recent Sessions
            </h3>

            {hasActiveSessions && (
                <>
                    <p className="text-[10px] font-semibold text-teal-600 uppercase tracking-wider px-2">
                        Active
                    </p>
                    {activeSessions_.map(renderSession)}
                    <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
                </>
            )}

            {restSessions.map(renderSession)}
        </div>
    );
}
