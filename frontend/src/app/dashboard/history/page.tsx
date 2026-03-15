'use client';

import { useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useChatSession, ChatSession } from '@/contexts/ChatSessionContext';
import { usePersona } from '@/contexts/PersonaContext';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { MessageSquare, Clock, Trash2, ArrowRight, Search, Calendar } from 'lucide-react';
import { useState } from 'react';

// Helper to categorize sessions by date
function categorizeByDate(sessions: ChatSession[]): Record<string, ChatSession[]> {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    const lastMonth = new Date(today);
    lastMonth.setMonth(lastMonth.getMonth() - 1);

    const categories: Record<string, ChatSession[]> = {
        'Today': [],
        'Yesterday': [],
        'This Week': [],
        'This Month': [],
        'Older': [],
    };

    for (const session of sessions) {
        const sessionDate = new Date(session.updatedAt);
        const sessionDay = new Date(sessionDate.getFullYear(), sessionDate.getMonth(), sessionDate.getDate());

        if (sessionDay.getTime() === today.getTime()) {
            categories['Today'].push(session);
        } else if (sessionDay.getTime() === yesterday.getTime()) {
            categories['Yesterday'].push(session);
        } else if (sessionDay >= lastWeek) {
            categories['This Week'].push(session);
        } else if (sessionDay >= lastMonth) {
            categories['This Month'].push(session);
        } else {
            categories['Older'].push(session);
        }
    }

    return categories;
}

export default function HistoryPage() {
    const router = useRouter();
    const { persona } = usePersona();
    const { 
        sessions, 
        isLoadingSessions, 
        selectChat, 
        deleteChat,
        refreshSessions 
    } = useChatSession();
    
    const [searchQuery, setSearchQuery] = useState('');
    const [deletingId, setDeletingId] = useState<string | null>(null);

    // Refresh sessions on mount and when page becomes visible (e.g. navigate back or tab focus)
    useEffect(() => {
        refreshSessions();
    }, [refreshSessions]);
    useEffect(() => {
        const onVisible = () => refreshSessions();
        document.addEventListener('visibilitychange', onVisible);
        return () => document.removeEventListener('visibilitychange', onVisible);
    }, [refreshSessions]);

    // Filter sessions by search query
    const filteredSessions = useMemo(() => {
        if (!searchQuery.trim()) return sessions;
        const query = searchQuery.toLowerCase();
        return sessions.filter(s => 
            s.title.toLowerCase().includes(query) ||
            (s.preview && s.preview.toLowerCase().includes(query))
        );
    }, [sessions, searchQuery]);

    // Categorize filtered sessions by date
    const categorizedSessions = useMemo(() => {
        return categorizeByDate(filteredSessions);
    }, [filteredSessions]);

    // Handle session selection - navigate to workspace with the session in URL so the chat
    // loads that session even if React state hasn't updated yet (avoids "new chat" instead of selected)
    const handleSelectSession = (sessionId: string) => {
        selectChat(sessionId);
        router.push(`/dashboard/workspace?session=${encodeURIComponent(sessionId)}`);
    };

    // Handle session deletion
    const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (deletingId) return; // Prevent double-click
        
        setDeletingId(sessionId);
        try {
            await deleteChat(sessionId);
        } catch (error) {
            console.error('Failed to delete session:', error);
        } finally {
            setDeletingId(null);
        }
    };

    // Format date for display
    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
    };

    const formatDate = (date: Date) => {
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
        });
    };

    return (
        <DashboardErrorBoundary fallbackTitle="History Error">
        <PremiumShell>
            <div className="max-w-4xl mx-auto p-6">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
                        <Clock className="text-teal-600" size={28} />
                        Chat History
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Browse and continue your past conversations
                    </p>
                </div>

                {/* Search */}
                <div className="mb-6">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search conversations..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                        />
                    </div>
                </div>

                {/* Loading State */}
                {isLoadingSessions && (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
                    </div>
                )}

                {/* Empty State */}
                {!isLoadingSessions && sessions.length === 0 && (
                    <div className="text-center py-16 bg-slate-50 dark:bg-slate-800/50 rounded-2xl">
                        <MessageSquare className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={48} />
                        <h3 className="text-lg font-semibold text-slate-600 dark:text-slate-300 mb-2">
                            No conversations yet
                        </h3>
                        <p className="text-slate-500 dark:text-slate-400 mb-6">
                            Start a new chat to begin your conversation history
                        </p>
                        <button
                            onClick={() => router.push('/dashboard/workspace')}
                            className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white rounded-xl hover:bg-teal-700 transition-colors font-medium"
                        >
                            Start New Chat
                            <ArrowRight size={18} />
                        </button>
                    </div>
                )}

                {/* No Search Results */}
                {!isLoadingSessions && sessions.length > 0 && filteredSessions.length === 0 && (
                    <div className="text-center py-12 bg-slate-50 dark:bg-slate-800/50 rounded-2xl">
                        <Search className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={40} />
                        <h3 className="text-lg font-semibold text-slate-600 dark:text-slate-300 mb-2">
                            No matches found
                        </h3>
                        <p className="text-slate-500 dark:text-slate-400">
                            Try a different search term
                        </p>
                    </div>
                )}

                {/* Session List by Date Category */}
                {!isLoadingSessions && filteredSessions.length > 0 && (
                    <div className="space-y-8">
                        {Object.entries(categorizedSessions).map(([category, categorySessions]) => {
                            if (categorySessions.length === 0) return null;
                            
                            return (
                                <div key={category}>
                                    {/* Category Header */}
                                    <div className="flex items-center gap-2 mb-3">
                                        <Calendar size={16} className="text-slate-400" />
                                        <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                                            {category}
                                        </h2>
                                        <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700"></div>
                                        <span className="text-xs text-slate-400">
                                            {categorySessions.length} {categorySessions.length === 1 ? 'chat' : 'chats'}
                                        </span>
                                    </div>

                                    {/* Sessions in Category */}
                                    <div className="space-y-2">
                                        {categorySessions.map((session) => {
                                            const isContentTitle = session.title && 
                                                !session.title.startsWith('Chat from') && 
                                                session.title !== 'Untitled Chat';
                                            const headline = isContentTitle
                                                ? session.title
                                                : (session.preview
                                                    ? session.preview.replace(/\n/g, ' ').slice(0, 80) + (session.preview.length > 80 ? '…' : '')
                                                    : 'New conversation');
                                            
                                            return (
                                                <div
                                                    key={session.id}
                                                    onClick={() => handleSelectSession(session.id)}
                                                    className="group flex items-start gap-4 p-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-teal-300 dark:hover:border-teal-600 hover:shadow-md transition-all cursor-pointer"
                                                >
                                                    {/* Icon */}
                                                    <div className="flex-shrink-0 w-10 h-10 mt-0.5 bg-gradient-to-br from-teal-100 to-cyan-100 dark:from-teal-900/30 dark:to-cyan-900/30 rounded-lg flex items-center justify-center">
                                                        <MessageSquare size={18} className="text-teal-600 dark:text-teal-400" />
                                                    </div>

                                                    {/* Headline: so users can see what the chat was about */}
                                                    <div className="flex-1 min-w-0">
                                                        <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 group-hover:text-teal-700 dark:group-hover:text-teal-400 transition-colors line-clamp-2 leading-snug">
                                                            {headline}
                                                        </h3>
                                                        {session.preview && isContentTitle && (
                                                            <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-1 mt-1">
                                                                {session.preview}
                                                            </p>
                                                        )}
                                                        {/* Show date inline below content for better context */}
                                                        <p className="text-xs text-slate-400 mt-1.5">
                                                            {category === 'Today' || category === 'Yesterday'
                                                                ? formatTime(session.updatedAt)
                                                                : formatDate(session.updatedAt)
                                                            }
                                                        </p>
                                                    </div>

                                                    {/* Actions */}
                                                    <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <button
                                                            onClick={(e) => handleDeleteSession(session.id, e)}
                                                            disabled={deletingId === session.id}
                                                            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
                                                            title="Delete conversation"
                                                        >
                                                            {deletingId === session.id ? (
                                                                <div className="w-4 h-4 border-2 border-red-500 border-t-transparent rounded-full animate-spin"></div>
                                                            ) : (
                                                                <Trash2 size={16} />
                                                            )}
                                                        </button>
                                                    </div>

                                                    {/* Arrow indicator */}
                                                    <ArrowRight 
                                                        size={16} 
                                                        className="flex-shrink-0 mt-1 text-slate-300 dark:text-slate-600 group-hover:text-teal-500 group-hover:translate-x-1 transition-all" 
                                                    />
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </PremiumShell>
        </DashboardErrorBoundary>
    );
}
