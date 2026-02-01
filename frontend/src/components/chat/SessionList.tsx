'use client';

import React from 'react';
import { useSessionHistory, SessionSummary } from '@/hooks/useSessionHistory';
import { MessageSquare, Trash2, Clock, Loader2 } from 'lucide-react';

interface SessionListProps {
    currentSessionId?: string;
    onSelectSession: (sessionId: string) => void;
    className?: string;
}

export function SessionList({ currentSessionId, onSelectSession, className = '' }: SessionListProps) {
    const { sessions, isLoading, error, deleteSession } = useSessionHistory();

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (isLoading) {
        return (
            <div className={`flex flex-col items-center justify-center p-8 text-slate-400 ${className}`}>
                <Loader2 className="w-6 h-6 animate-spin mb-2" />
                <span className="text-sm">Loading history...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className={`p-4 text-center text-red-500 text-sm ${className}`}>
                Failed to load history
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

    return (
        <div className={`flex flex-col space-y-2 max-h-[600px] overflow-y-auto ${className}`}>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2 mb-2">
                Recent Sessions
            </h3>

            {sessions.map((session) => (
                <div
                    key={session.session_id}
                    className={`
            group flex items-center justify-between p-3 rounded-lg transition-colors cursor-pointer border
            ${currentSessionId === session.session_id
                            ? 'bg-indigo-50 border-indigo-200 dark:bg-indigo-900/20 dark:border-indigo-800'
                            : 'bg-white border-transparent hover:bg-slate-50 dark:bg-slate-800/50 dark:hover:bg-slate-800 dark:border-slate-800'
                        }
          `}
                    onClick={() => onSelectSession(session.session_id)}
                >
                    <div className="flex flex-col min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                            <MessageSquare size={14} className={currentSessionId === session.session_id ? 'text-indigo-500' : 'text-slate-400'} />
                            <span className={`text-sm font-medium truncate ${currentSessionId === session.session_id
                                    ? 'text-indigo-700 dark:text-indigo-300'
                                    : 'text-slate-700 dark:text-slate-200'
                                }`}>
                                {/* Fallback title if state doesn't have one */}
                                {session.state?.title || `Session ${session.session_id.slice(0, 8)}`}
                            </span>
                        </div>

                        <div className="flex items-center gap-1 text-xs text-slate-400">
                            <Clock size={10} />
                            <span>{formatDate(session.updated_at || session.created_at)}</span>
                        </div>
                    </div>

                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            if (confirm('Are you sure you want to delete this session?')) {
                                deleteSession(session.session_id);
                            }
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-500 rounded transition"
                        title="Delete session"
                    >
                        <Trash2 size={14} />
                    </button>
                </div>
            ))}
        </div>
    );
}
