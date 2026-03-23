'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useChatSession, ChatSession } from '@/contexts/ChatSessionContext';
import { usePersona } from '@/contexts/PersonaContext';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import MetricCard from '@/components/ui/MetricCard';
import {
    MessageSquare,
    Clock,
    Trash2,
    ArrowRight,
    Search,
    Calendar,
    MessagesSquare,
    CalendarDays,
    TrendingUp,
} from 'lucide-react';

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

function LoadingSkeleton() {
    return (
        <div className="animate-pulse space-y-6">
            <div className="flex items-center justify-between">
                <div className="h-8 w-56 rounded bg-slate-200" />
                <div className="h-10 w-36 rounded bg-slate-200" />
            </div>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="h-24 rounded-2xl bg-slate-100" />
                ))}
            </div>
            <div className="h-12 rounded-xl bg-slate-100" />
            {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 rounded-xl bg-slate-100" />
            ))}
        </div>
    );
}

export default function HistoryPage() {
    const router = useRouter();
    const { persona } = usePersona();
    const {
        sessions,
        isLoadingSessions,
        selectChat,
        deleteChat,
        refreshSessions,
    } = useChatSession();

    const [searchQuery, setSearchQuery] = useState('');
    const [deletingId, setDeletingId] = useState<string | null>(null);

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

    // KPI stats
    const todayCount = useMemo(() => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return sessions.filter(s => new Date(s.updatedAt) >= today).length;
    }, [sessions]);

    const weekCount = useMemo(() => {
        const week = new Date();
        week.setDate(week.getDate() - 7);
        return sessions.filter(s => new Date(s.updatedAt) >= week).length;
    }, [sessions]);

    const avgPerDay = useMemo(() => {
        if (sessions.length === 0) return '0';
        const dates = new Set(sessions.map(s => new Date(s.updatedAt).toDateString()));
        return (sessions.length / Math.max(dates.size, 1)).toFixed(1);
    }, [sessions]);

    // Handle session selection
    const handleSelectSession = (sessionId: string) => {
        selectChat(sessionId);
        router.push(`/dashboard/workspace?session=${encodeURIComponent(sessionId)}`);
    };

    // Handle session deletion
    const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (deletingId) return;

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
    const formatTime = (dateInput: string | Date) => {
        const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    };

    const formatDate = (dateInput: string | Date) => {
        const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
        });
    };

    return (
        <DashboardErrorBoundary fallbackTitle="History Error">
        <PremiumShell>
            <div className="min-h-screen bg-white p-6 md:p-10">
                {isLoadingSessions && sessions.length === 0 ? (
                    <LoadingSkeleton />
                ) : (
                    <>
                        {/* Header */}
                        <div className="mb-8 flex items-center justify-between">
                            <div>
                                <h1 className="text-2xl font-bold text-slate-900">Chat History</h1>
                                <p className="mt-1 text-sm text-slate-500">
                                    Browse and continue your past conversations
                                </p>
                            </div>
                            <button
                                onClick={() => router.push('/dashboard/workspace')}
                                className="rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-teal-700 transition-colors"
                            >
                                New Chat
                            </button>
                        </div>

                        {/* KPI Row */}
                        <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
                            <MetricCard
                                label="Total Chats"
                                value={sessions.length.toString()}
                                icon={MessagesSquare}
                                color="text-teal-600"
                                bg="bg-teal-50"
                            />
                            <MetricCard
                                label="Today"
                                value={todayCount.toString()}
                                icon={Clock}
                                color="text-blue-600"
                                bg="bg-blue-50"
                            />
                            <MetricCard
                                label="This Week"
                                value={weekCount.toString()}
                                icon={CalendarDays}
                                color="text-violet-600"
                                bg="bg-violet-50"
                            />
                            <MetricCard
                                label="Avg / Day"
                                value={avgPerDay}
                                icon={TrendingUp}
                                color="text-amber-600"
                                bg="bg-amber-50"
                            />
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
                                    className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-4 text-slate-900 placeholder-slate-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-teal-500"
                                />
                            </div>
                        </div>

                        {/* Empty State */}
                        {sessions.length === 0 && (
                            <div className="rounded-2xl border border-slate-100 bg-white p-12 text-center shadow-sm">
                                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-50">
                                    <MessageSquare className="text-slate-300" size={32} />
                                </div>
                                <h3 className="text-lg font-semibold text-slate-600">No conversations yet</h3>
                                <p className="mt-1 text-sm text-slate-500">Start a new chat to begin your conversation history</p>
                                <button
                                    onClick={() => router.push('/dashboard/workspace')}
                                    className="mt-6 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-6 py-3 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
                                >
                                    Start New Chat
                                    <ArrowRight size={18} />
                                </button>
                            </div>
                        )}

                        {/* No Search Results */}
                        {sessions.length > 0 && filteredSessions.length === 0 && (
                            <div className="rounded-2xl border border-slate-100 bg-white p-12 text-center shadow-sm">
                                <Search className="mx-auto mb-4 text-slate-300" size={40} />
                                <h3 className="text-lg font-semibold text-slate-600">No matches found</h3>
                                <p className="mt-1 text-sm text-slate-500">Try a different search term</p>
                            </div>
                        )}

                        {/* Session List by Date Category */}
                        {filteredSessions.length > 0 && (
                            <div className="space-y-6">
                                {Object.entries(categorizedSessions).map(([category, categorySessions]) => {
                                    if (categorySessions.length === 0) return null;

                                    return (
                                        <div key={category} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
                                            {/* Category Header */}
                                            <div className="mb-4 flex items-center gap-2">
                                                <Calendar size={14} className="text-slate-400" />
                                                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                                                    {category}
                                                </h2>
                                                <div className="flex-1 h-px bg-slate-100"></div>
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
                                                            ? session.preview.replace(/\n/g, ' ').slice(0, 80) + (session.preview.length > 80 ? '\u2026' : '')
                                                            : 'New conversation');

                                                    return (
                                                        <div
                                                            key={session.id}
                                                            onClick={() => handleSelectSession(session.id)}
                                                            className="group flex cursor-pointer items-start gap-4 rounded-xl border border-slate-50 bg-slate-50/50 p-4 transition-all hover:border-teal-200 hover:shadow-md"
                                                        >
                                                            {/* Icon */}
                                                            <div className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-100 to-cyan-100">
                                                                <MessageSquare size={18} className="text-teal-600" />
                                                            </div>

                                                            {/* Content */}
                                                            <div className="min-w-0 flex-1">
                                                                <h3 className="text-base font-bold leading-snug text-slate-900 transition-colors group-hover:text-teal-700 line-clamp-2">
                                                                    {headline}
                                                                </h3>
                                                                {session.preview && isContentTitle && (
                                                                    <p className="mt-1 text-sm text-slate-500 line-clamp-1">
                                                                        {session.preview}
                                                                    </p>
                                                                )}
                                                                <p className="mt-1.5 text-xs text-slate-400">
                                                                    {category === 'Today' || category === 'Yesterday'
                                                                        ? formatTime(session.updatedAt)
                                                                        : formatDate(session.updatedAt)
                                                                    }
                                                                </p>
                                                            </div>

                                                            {/* Actions */}
                                                            <div className="flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
                                                                <button
                                                                    onClick={(e) => handleDeleteSession(session.id, e)}
                                                                    disabled={deletingId === session.id}
                                                                    className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 disabled:opacity-50"
                                                                    title="Delete conversation"
                                                                >
                                                                    {deletingId === session.id ? (
                                                                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-red-500 border-t-transparent"></div>
                                                                    ) : (
                                                                        <Trash2 size={16} />
                                                                    )}
                                                                </button>
                                                            </div>

                                                            {/* Arrow */}
                                                            <ArrowRight
                                                                size={16}
                                                                className="mt-1 flex-shrink-0 text-slate-300 transition-all group-hover:translate-x-1 group-hover:text-teal-500"
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
                    </>
                )}
            </div>
        </PremiumShell>
        </DashboardErrorBoundary>
    );
}
