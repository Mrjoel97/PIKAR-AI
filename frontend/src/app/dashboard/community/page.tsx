'use client';

import { useState, useEffect, useCallback } from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import MetricCard from '@/components/ui/MetricCard';
import DashboardSkeleton from '@/components/ui/DashboardSkeleton';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import EmptyState from '@/components/ui/EmptyState';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Users,
    MessageSquare,
    Calendar,
    GitPullRequest,
    ExternalLink,
    Sparkles,
    ArrowRight,
    Clock,
    Trophy,
    Plus,
    X,
    AlertCircle,
    ThumbsUp,
} from 'lucide-react';
import {
    listPosts,
    createPost,
    toggleUpvote,
    type CommunityPost,
} from '@/services/community';

const CATEGORY_COLORS: Record<string, string> = {
    general: 'bg-slate-100 text-slate-600',
    workflows: 'bg-amber-50 text-amber-700',
    agents: 'bg-violet-50 text-violet-700',
    finance: 'bg-emerald-50 text-emerald-700',
    integrations: 'bg-blue-50 text-blue-700',
    compliance: 'bg-rose-50 text-rose-700',
    content: 'bg-pink-50 text-pink-700',
    sales: 'bg-cyan-50 text-cyan-700',
};

const AVATAR_GRADIENTS = [
    'from-teal-400 to-emerald-500',
    'from-violet-400 to-purple-500',
    'from-amber-400 to-orange-500',
    'from-blue-400 to-indigo-500',
    'from-rose-400 to-pink-500',
    'from-cyan-400 to-teal-500',
];

const EVENTS = [
    { id: 1, title: 'Weekly Office Hours', date: 'Every Thursday', time: '2:00 PM EST', type: 'recurring' as const, attendees: 45 },
    { id: 2, title: 'Workflow Masterclass: Multi-Agent Pipelines', date: 'Mar 22, 2026', time: '11:00 AM EST', type: 'workshop' as const, attendees: 128 },
    { id: 3, title: 'Community AMA with CEO', date: 'Mar 28, 2026', time: '3:00 PM EST', type: 'ama' as const, attendees: 312 },
    { id: 4, title: 'Pikar-AI v2.0 Launch Party', date: 'Apr 5, 2026', time: '1:00 PM EST', type: 'launch' as const, attendees: 500 },
];

const EVENT_TYPE_STYLES: Record<string, string> = {
    recurring: 'bg-slate-100 text-slate-600',
    workshop: 'bg-blue-50 text-blue-600',
    ama: 'bg-violet-50 text-violet-600',
    launch: 'bg-teal-50 text-teal-600',
};

const EVENT_TYPE_LABELS: Record<string, string> = {
    recurring: 'Recurring',
    workshop: 'Workshop',
    ama: 'AMA',
    launch: 'Launch',
};

function getInitials(name: string) {
    return name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
}

function CreatePostModal({
    onClose,
    onCreated,
}: {
    onClose: () => void;
    onCreated: () => void;
}) {
    const [title, setTitle] = useState('');
    const [body, setBody] = useState('');
    const [category, setCategory] = useState('general');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);
        try {
            await createPost({ title, body, category });
            onCreated();
            onClose();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create post');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="w-full max-w-lg rounded-[28px] bg-white p-8 shadow-[0_18px_60px_-35px_rgba(15,23,42,0.5)]"
            >
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-slate-900">New Discussion</h2>
                    <button onClick={onClose} className="rounded-full p-2 hover:bg-slate-100 transition-colors">
                        <X className="h-5 w-5 text-slate-400" />
                    </button>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            required
                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all"
                            placeholder="What's on your mind?"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                        <select
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all"
                        >
                            {Object.keys(CATEGORY_COLORS).map((cat) => (
                                <option key={cat} value={cat}>
                                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Body</label>
                        <textarea
                            value={body}
                            onChange={(e) => setBody(e.target.value)}
                            required
                            rows={5}
                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all resize-none"
                            placeholder="Share your thoughts, tips, or questions..."
                        />
                    </div>
                    {error && (
                        <div className="flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
                            <AlertCircle className="h-4 w-4 flex-shrink-0" />
                            {error}
                        </div>
                    )}
                    <button
                        type="submit"
                        disabled={submitting}
                        className="w-full rounded-2xl bg-teal-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition-all hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {submitting ? 'Posting...' : 'Post Discussion'}
                    </button>
                </form>
            </motion.div>
        </div>
    );
}

export default function CommunityPage() {
    const [posts, setPosts] = useState<CommunityPost[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [sortMode, setSortMode] = useState<'recent' | 'popular'>('recent');

    const fetchPosts = useCallback(async () => {
        try {
            setError(null);
            const data = await listPosts({ sort: sortMode, limit: 20 });
            setPosts(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load posts');
        } finally {
            setLoading(false);
        }
    }, [sortMode]);

    useEffect(() => {
        fetchPosts();
    }, [fetchPosts]);

    const handleUpvote = async (postId: string) => {
        try {
            const result = await toggleUpvote(postId);
            setPosts((prev) =>
                prev.map((p) =>
                    p.id === postId ? { ...p, upvotes: result.upvotes } : p,
                ),
            );
        } catch {
            // Silently fail
        }
    };

    return (
        <DashboardErrorBoundary fallbackTitle="Community Error">
            <PremiumShell>
                <div className="space-y-8">
                    {/* Header */}
                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
                    >
                        <div>
                            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                                Community
                            </h1>
                            <p className="mt-1 text-sm text-slate-500">
                                Connect, learn, and grow with fellow Pikar-AI users.
                            </p>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition-all hover:bg-teal-700 hover:shadow-teal-700/30 active:scale-[0.98]"
                            >
                                <Plus className="h-4 w-4" />
                                New Discussion
                            </button>
                            <a
                                href="https://discord.gg/pikar-ai"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:bg-slate-50 active:scale-[0.98]"
                            >
                                Join Discord
                                <ExternalLink className="h-4 w-4" />
                            </a>
                        </div>
                    </motion.div>

                    {/* KPI Row */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                        <MetricCard
                            label="Members"
                            value="2,847"
                            icon={Users}
                            gradient="from-teal-400 to-emerald-500"
                            delay={0.05}
                        />
                        <MetricCard
                            label="Discussions"
                            value={loading ? '...' : posts.length}
                            icon={MessageSquare}
                            gradient="from-violet-400 to-purple-500"
                            delay={0.1}
                        />
                        <MetricCard
                            label="Events This Month"
                            value={EVENTS.length}
                            icon={Calendar}
                            gradient="from-amber-400 to-orange-500"
                            delay={0.15}
                        />
                        <MetricCard
                            label="Total Upvotes"
                            value={loading ? '...' : posts.reduce((sum, p) => sum + p.upvotes, 0)}
                            icon={GitPullRequest}
                            gradient="from-blue-400 to-indigo-500"
                            delay={0.2}
                        />
                    </div>

                    {/* Featured Spotlight Banner */}
                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.25 }}
                        className="relative overflow-hidden rounded-[28px] bg-gradient-to-r from-teal-700 to-teal-900 p-8 sm:p-10 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                    >
                        <div className="absolute top-6 right-8 opacity-10">
                            <Sparkles className="h-32 w-32 text-white" />
                        </div>
                        <div className="relative z-10 max-w-2xl">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-teal-200">
                                Community Spotlight
                            </p>
                            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white">
                                How Sarah scaled her agency to $2M ARR using Pikar-AI
                            </h2>
                            <p className="mt-3 text-sm leading-relaxed text-teal-100/80">
                                Discover how Sarah C. leveraged multi-agent workflows, automated
                                financial forecasting, and AI-driven content pipelines to transform
                                her consulting agency into a seven-figure business in under 12
                                months.
                            </p>
                            <button className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-white/15 px-5 py-2.5 text-sm font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/25 active:scale-[0.98]">
                                Read Story
                                <ArrowRight className="h-4 w-4" />
                            </button>
                        </div>
                    </motion.div>

                    {/* Two-column grid: Discussions + Events */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Discussions */}
                        <motion.div
                            initial={{ opacity: 0, y: 18 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.3 }}
                            className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                        >
                            <div className="flex items-center justify-between mb-5">
                                <h3 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                                    Discussions
                                </h3>
                                <div className="inline-flex gap-1 rounded-xl bg-slate-100 p-0.5">
                                    <button
                                        onClick={() => setSortMode('recent')}
                                        className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${sortMode === 'recent' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
                                    >
                                        Recent
                                    </button>
                                    <button
                                        onClick={() => setSortMode('popular')}
                                        className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${sortMode === 'popular' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
                                    >
                                        Popular
                                    </button>
                                </div>
                            </div>
                            {loading ? (
                                <DashboardSkeleton rows={3} columns={1} showMetricCards={false} />
                            ) : error ? (
                                <div className="flex items-center gap-3 rounded-xl bg-rose-50 px-4 py-3">
                                    <AlertCircle className="h-4 w-4 text-rose-500" />
                                    <p className="text-sm text-rose-700">{error}</p>
                                    <button
                                        onClick={() => { setLoading(true); fetchPosts(); }}
                                        className="ml-auto text-xs font-semibold text-rose-700 hover:underline"
                                    >
                                        Retry
                                    </button>
                                </div>
                            ) : posts.length === 0 ? (
                                <EmptyState
                                    icon={MessageSquare}
                                    title="No discussions yet"
                                    description="Be the first to start a conversation! Click 'New Discussion' to share your thoughts."
                                    gradient="from-violet-400 to-purple-500"
                                    actionLabel="Start Discussion"
                                    onAction={() => setShowCreateModal(true)}
                                />
                            ) : (
                                <div className="space-y-4">
                                    {posts.map((post, i) => (
                                        <motion.div
                                            key={post.id}
                                            initial={{ opacity: 0, x: -12 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ duration: 0.4, delay: 0.35 + i * 0.06 }}
                                            className="group flex items-start gap-3.5 rounded-2xl p-3 transition-colors hover:bg-slate-50 cursor-pointer"
                                        >
                                            <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${AVATAR_GRADIENTS[i % AVATAR_GRADIENTS.length]} text-[11px] font-bold text-white shadow-sm`}>
                                                {getInitials(post.author_name)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-slate-900 group-hover:text-teal-700 transition-colors truncate">
                                                    {post.title}
                                                </p>
                                                <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                                                    <span className="font-medium text-slate-500">
                                                        {post.author_name}
                                                    </span>
                                                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${CATEGORY_COLORS[post.category] || 'bg-slate-100 text-slate-600'}`}>
                                                        {post.category}
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                        <MessageSquare className="h-3 w-3" />
                                                        {post.reply_count}
                                                    </span>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handleUpvote(post.id); }}
                                                        className="flex items-center gap-1 hover:text-teal-600 transition-colors"
                                                    >
                                                        <ThumbsUp className="h-3 w-3" />
                                                        {post.upvotes}
                                                    </button>
                                                    <span className="flex items-center gap-1">
                                                        <Clock className="h-3 w-3" />
                                                        {new Date(post.created_at).toLocaleDateString()}
                                                    </span>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </motion.div>

                        {/* Upcoming Events (static for now) */}
                        <motion.div
                            initial={{ opacity: 0, y: 18 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.35 }}
                            className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                        >
                            <h3 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                                Upcoming Events
                            </h3>
                            <div className="mt-5 space-y-4">
                                {EVENTS.map((e, i) => (
                                    <motion.div
                                        key={e.id}
                                        initial={{ opacity: 0, x: 12 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ duration: 0.4, delay: 0.4 + i * 0.06 }}
                                        className="flex items-start gap-4 rounded-2xl border border-slate-100 p-4 transition-all hover:border-slate-200 hover:shadow-sm"
                                    >
                                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-50">
                                            <Calendar className="h-5 w-5 text-slate-500" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-2">
                                                <p className="text-sm font-medium text-slate-900 truncate">
                                                    {e.title}
                                                </p>
                                                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${EVENT_TYPE_STYLES[e.type]}`}>
                                                    {EVENT_TYPE_LABELS[e.type]}
                                                </span>
                                            </div>
                                            <p className="mt-1 text-xs text-slate-400">
                                                {e.date} &middot; {e.time}
                                            </p>
                                            <div className="mt-3 flex items-center justify-between">
                                                <span className="flex items-center gap-1.5 text-xs text-slate-400">
                                                    <Users className="h-3.5 w-3.5" />
                                                    {e.attendees} attending
                                                </span>
                                                <button className="rounded-2xl bg-teal-600 px-4 py-1.5 text-[11px] font-semibold text-white shadow-sm transition-all hover:bg-teal-700 active:scale-[0.97]">
                                                    {e.type === 'recurring' ? 'Join' : 'RSVP'}
                                                </button>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </motion.div>
                    </div>

                    {/* Top Contributors (static) */}
                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.45 }}
                        className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                    >
                        <div className="flex items-center gap-2 mb-5">
                            <Trophy className="h-4 w-4 text-amber-500" />
                            <h3 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                                Top Contributors
                            </h3>
                        </div>
                        <div className="flex gap-5 overflow-x-auto pb-2 no-scrollbar">
                            {[
                                { name: 'Sarah C.', contributions: 234, role: 'Power User' },
                                { name: 'Alex M.', contributions: 189, role: 'Workflow Expert' },
                                { name: 'Priya K.', contributions: 167, role: 'AI Pioneer' },
                                { name: 'Jordan T.', contributions: 145, role: 'Finance Pro' },
                                { name: 'Sam L.', contributions: 132, role: 'Integration Guru' },
                                { name: 'Maria R.', contributions: 98, role: 'Compliance Lead' },
                            ].map((c, i) => (
                                <motion.div
                                    key={c.name}
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ duration: 0.4, delay: 0.5 + i * 0.06 }}
                                    className="flex flex-col items-center gap-2.5 rounded-2xl border border-slate-100 p-5 min-w-[140px] transition-all hover:border-slate-200 hover:shadow-sm"
                                >
                                    <div className={`flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br ${AVATAR_GRADIENTS[i]} text-base font-bold text-white shadow-lg`}>
                                        {getInitials(c.name)}
                                    </div>
                                    <div className="text-center">
                                        <p className="text-sm font-semibold text-slate-900">{c.name}</p>
                                        <span className="mt-0.5 inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-medium text-slate-500">
                                            {c.role}
                                        </span>
                                    </div>
                                    <p className="text-lg font-bold text-teal-600">{c.contributions}</p>
                                    <p className="text-[10px] uppercase tracking-wider text-slate-400">contributions</p>
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>
                </div>

                {/* Create Post Modal */}
                <AnimatePresence>
                    {showCreateModal && (
                        <CreatePostModal
                            onClose={() => setShowCreateModal(false)}
                            onCreated={() => { setLoading(true); fetchPosts(); }}
                        />
                    )}
                </AnimatePresence>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
