'use client';

import { useState, useEffect, useCallback } from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import MetricCard from '@/components/ui/MetricCard';
import DashboardSkeleton from '@/components/ui/DashboardSkeleton';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import EmptyState from '@/components/ui/EmptyState';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Clock,
    Ticket,
    CheckCircle2,
    ThumbsUp,
    MessageSquare,
    Mail,
    Phone,
    ChevronDown,
    BookOpen,
    Code2,
    PlayCircle,
    Users,
    Activity,
    FileText,
    ExternalLink,
    Plus,
    AlertCircle,
    X,
} from 'lucide-react';
import {
    listTickets,
    createTicket,
    type SupportTicket,
} from '@/services/support';

const STATUS_STYLES: Record<string, string> = {
    new: 'bg-blue-50 text-blue-700 border-blue-200',
    open: 'bg-sky-50 text-sky-700 border-sky-200',
    in_progress: 'bg-amber-50 text-amber-700 border-amber-200',
    waiting: 'bg-slate-50 text-slate-600 border-slate-200',
    resolved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    closed: 'bg-slate-100 text-slate-500 border-slate-200',
};

const PRIORITY_STYLES: Record<string, string> = {
    low: 'bg-slate-50 text-slate-600',
    normal: 'bg-blue-50 text-blue-700',
    high: 'bg-amber-50 text-amber-700',
    urgent: 'bg-red-50 text-red-700',
};

const FAQ_ITEMS = [
    {
        question: 'How do I connect my Google Workspace?',
        answer:
            'Navigate to Settings > Integrations and click "Connect Google Workspace." You\'ll be guided through an OAuth flow to grant Pikar AI read and write access to Gmail, Calendar, Drive, and Sheets. Once authorized, all connected services appear in your integration dashboard.',
    },
    {
        question: 'Can I customize the AI agent instructions?',
        answer:
            'Absolutely. Each of the 10 specialized agents has its own instruction set you can edit from the Agents page. You can adjust tone, priorities, and domain-specific rules. Changes take effect immediately for new conversations.',
    },
    {
        question: 'How does the workflow automation engine work?',
        answer:
            'The workflow engine lets you define multi-step automations that chain agent actions together. You can set triggers (time-based, event-based, or manual), define execution contracts with trust classification, and monitor each run in real-time from the Workflows dashboard.',
    },
    {
        question: "What's included in my subscription plan?",
        answer:
            'Your plan includes access to all 10 specialized AI agents, the Executive Agent orchestrator, unlimited workflow automations, and priority support. Usage-based features like video generation and deep research have monthly quotas visible in your billing portal.',
    },
    {
        question: 'How do I export my data?',
        answer:
            'Go to Settings > Data Management and select "Export." You can export conversations, workflow history, analytics, and agent configurations in JSON or CSV format. Exports are processed asynchronously and you\'ll receive a download link via email.',
    },
    {
        question: 'Is my data encrypted and secure?',
        answer:
            'Yes. All data is encrypted at rest using AES-256 and in transit via TLS 1.3. We use Supabase with row-level security policies, and sensitive credentials are stored in Google Secret Manager. We undergo regular third-party security audits.',
    },
];

const QUICK_LINKS = [
    { icon: BookOpen, title: 'Documentation', description: 'Comprehensive guides and API docs', href: '#' },
    { icon: Code2, title: 'API Reference', description: 'Endpoints, schemas, and examples', href: '#' },
    { icon: PlayCircle, title: 'Video Tutorials', description: 'Step-by-step visual walkthroughs', href: '#' },
    { icon: Users, title: 'Community Forum', description: 'Connect with other Pikar users', href: '#' },
    { icon: Activity, title: 'Status Page', description: 'Real-time system health and uptime', href: '#' },
    { icon: FileText, title: 'Changelog', description: 'Latest updates and release notes', href: '#' },
];

function CreateTicketModal({
    onClose,
    onCreated,
}: {
    onClose: () => void;
    onCreated: () => void;
}) {
    const [subject, setSubject] = useState('');
    const [description, setDescription] = useState('');
    const [email, setEmail] = useState('');
    const [priority, setPriority] = useState<'low' | 'normal' | 'high' | 'urgent'>('normal');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);
        try {
            await createTicket({ subject, description, customer_email: email, priority });
            onCreated();
            onClose();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create ticket');
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
                    <h2 className="text-xl font-semibold text-slate-900">Open a Ticket</h2>
                    <button onClick={onClose} className="rounded-full p-2 hover:bg-slate-100 transition-colors">
                        <X className="h-5 w-5 text-slate-400" />
                    </button>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Subject</label>
                        <input
                            type="text"
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                            required
                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all"
                            placeholder="Brief description of the issue"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all"
                            placeholder="your@email.com"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Priority</label>
                        <select
                            value={priority}
                            onChange={(e) => setPriority(e.target.value as 'low' | 'normal' | 'high' | 'urgent')}
                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all"
                        >
                            <option value="low">Low</option>
                            <option value="normal">Normal</option>
                            <option value="high">High</option>
                            <option value="urgent">Urgent</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            required
                            rows={4}
                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all resize-none"
                            placeholder="Describe your issue in detail..."
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
                        {submitting ? 'Submitting...' : 'Submit Ticket'}
                    </button>
                </form>
            </motion.div>
        </div>
    );
}

export default function SupportPage() {
    const [openFaqs, setOpenFaqs] = useState<Set<number>>(new Set());
    const [tickets, setTickets] = useState<SupportTicket[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showCreateModal, setShowCreateModal] = useState(false);

    const fetchTickets = useCallback(async () => {
        try {
            setError(null);
            const data = await listTickets({ limit: 20 });
            setTickets(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load tickets');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTickets();
    }, [fetchTickets]);

    const toggleFaq = (index: number) => {
        setOpenFaqs((prev) => {
            const next = new Set(prev);
            if (next.has(index)) next.delete(index);
            else next.add(index);
            return next;
        });
    };

    const openCount = tickets.filter((t) => !['resolved', 'closed'].includes(t.status)).length;
    const resolvedCount = tickets.filter((t) => t.status === 'resolved').length;

    return (
        <DashboardErrorBoundary fallbackTitle="Support Center Error">
            <PremiumShell>
                <div className="space-y-8">
                    {/* Header */}
                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
                    >
                        <div>
                            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                                Support Center
                            </h1>
                            <p className="mt-1 text-sm text-slate-500">
                                Get help from our team or find answers in our resources.
                            </p>
                        </div>
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition-all hover:bg-teal-700 hover:shadow-xl hover:shadow-teal-600/30 active:scale-[0.97]"
                        >
                            <Plus className="h-4 w-4" />
                            Open a Ticket
                        </button>
                    </motion.div>

                    {/* KPI Row */}
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        <MetricCard
                            label="Avg Response Time"
                            value="< 2 hrs"
                            icon={Clock}
                            gradient="from-teal-400 to-emerald-500"
                            delay={0}
                        />
                        <MetricCard
                            label="Open Tickets"
                            value={loading ? '...' : openCount}
                            icon={Ticket}
                            gradient="from-blue-400 to-indigo-500"
                            delay={0.08}
                        />
                        <MetricCard
                            label="Resolved"
                            value={loading ? '...' : resolvedCount}
                            icon={CheckCircle2}
                            gradient="from-violet-400 to-purple-500"
                            delay={0.16}
                        />
                        <MetricCard
                            label="Satisfaction"
                            value="98%"
                            icon={ThumbsUp}
                            gradient="from-amber-400 to-orange-500"
                            delay={0.24}
                        />
                    </div>

                    {/* Your Tickets Section */}
                    <div>
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.5, delay: 0.28 }}
                            className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400"
                        >
                            Your Tickets
                        </motion.p>
                        {loading ? (
                            <DashboardSkeleton rows={2} columns={1} showMetricCards={false} />
                        ) : error ? (
                            <div className="flex items-center gap-3 rounded-[28px] border border-rose-200 bg-rose-50 px-6 py-5">
                                <AlertCircle className="h-5 w-5 text-rose-500 flex-shrink-0" />
                                <p className="text-sm text-rose-700">{error}</p>
                                <button
                                    onClick={() => { setLoading(true); fetchTickets(); }}
                                    className="ml-auto rounded-xl bg-rose-100 px-4 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-200 transition-colors"
                                >
                                    Retry
                                </button>
                            </div>
                        ) : tickets.length === 0 ? (
                            <EmptyState
                                icon={Ticket}
                                title="No tickets yet"
                                description="You haven't opened any support tickets. Click the button above to get started."
                                gradient="from-blue-400 to-indigo-500"
                            />
                        ) : (
                            <div className="space-y-3">
                                {tickets.map((ticket, i) => (
                                    <motion.div
                                        key={ticket.id}
                                        initial={{ opacity: 0, y: 12 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.4, delay: 0.3 + i * 0.05 }}
                                        className="rounded-2xl border border-slate-100/80 bg-white p-5 shadow-[0_4px_24px_-12px_rgba(15,23,42,0.12)] transition-shadow hover:shadow-[0_8px_32px_-12px_rgba(15,23,42,0.18)]"
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1 min-w-0">
                                                <h4 className="text-sm font-semibold text-slate-900 truncate">
                                                    {ticket.subject}
                                                </h4>
                                                <p className="mt-1 text-xs text-slate-500 line-clamp-1">
                                                    {ticket.description}
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-2 flex-shrink-0">
                                                <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${PRIORITY_STYLES[ticket.priority] || ''}`}>
                                                    {ticket.priority}
                                                </span>
                                                <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${STATUS_STYLES[ticket.status] || ''}`}>
                                                    {ticket.status.replace('_', ' ')}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
                                            <span>{ticket.customer_email}</span>
                                            <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Contact Options Grid */}
                    <div>
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.5, delay: 0.3 }}
                            className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400"
                        >
                            Contact Options
                        </motion.p>
                        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                            {/* AI Concierge */}
                            <motion.div
                                initial={{ opacity: 0, y: 18 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: 0.35 }}
                                className="group rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)] overflow-hidden"
                            >
                                <div className="bg-gradient-to-r from-teal-500 to-emerald-500 px-6 py-5">
                                    <div className="flex items-center gap-3">
                                        <div className="rounded-xl bg-white/20 p-2.5 backdrop-blur-sm">
                                            <MessageSquare className="h-5 w-5 text-white" />
                                        </div>
                                        <h3 className="text-lg font-semibold text-white">AI Concierge</h3>
                                    </div>
                                </div>
                                <div className="p-6">
                                    <p className="text-sm leading-relaxed text-slate-600">
                                        Get instant answers from our AI assistant. Available 24/7 for quick questions.
                                    </p>
                                    <button className="mt-5 w-full rounded-2xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-teal-600/20 transition-all hover:bg-teal-700 hover:shadow-lg hover:shadow-teal-600/25 active:scale-[0.97]">
                                        Start Chat
                                    </button>
                                </div>
                            </motion.div>

                            {/* Email Support */}
                            <motion.div
                                initial={{ opacity: 0, y: 18 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: 0.42 }}
                                className="group rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)] overflow-hidden"
                            >
                                <div className="bg-gradient-to-r from-blue-500 to-indigo-500 px-6 py-5">
                                    <div className="flex items-center gap-3">
                                        <div className="rounded-xl bg-white/20 p-2.5 backdrop-blur-sm">
                                            <Mail className="h-5 w-5 text-white" />
                                        </div>
                                        <h3 className="text-lg font-semibold text-white">Email Support</h3>
                                    </div>
                                </div>
                                <div className="p-6">
                                    <p className="text-sm leading-relaxed text-slate-600">
                                        Send us a detailed message. We typically respond within 2 hours.
                                    </p>
                                    <button className="mt-5 w-full rounded-2xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-blue-600/20 transition-all hover:bg-blue-700 hover:shadow-lg hover:shadow-blue-600/25 active:scale-[0.97]">
                                        Send Email
                                    </button>
                                </div>
                            </motion.div>

                            {/* Priority Call */}
                            <motion.div
                                initial={{ opacity: 0, y: 18 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: 0.49 }}
                                className="group rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)] overflow-hidden"
                            >
                                <div className="bg-gradient-to-r from-violet-500 to-purple-500 px-6 py-5">
                                    <div className="flex items-center gap-3">
                                        <div className="rounded-xl bg-white/20 p-2.5 backdrop-blur-sm">
                                            <Phone className="h-5 w-5 text-white" />
                                        </div>
                                        <h3 className="text-lg font-semibold text-white">Priority Call</h3>
                                    </div>
                                </div>
                                <div className="p-6">
                                    <p className="text-sm leading-relaxed text-slate-600">
                                        Schedule a 1-on-1 call with our support team for complex issues.
                                    </p>
                                    <button className="mt-5 w-full rounded-2xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-violet-600/20 transition-all hover:bg-violet-700 hover:shadow-lg hover:shadow-violet-600/25 active:scale-[0.97]">
                                        Schedule Call
                                    </button>
                                </div>
                            </motion.div>
                        </div>
                    </div>

                    {/* FAQ Section */}
                    <div>
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.5, delay: 0.55 }}
                            className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400"
                        >
                            Frequently Asked Questions
                        </motion.p>
                        <div className="space-y-3">
                            {FAQ_ITEMS.map((item, index) => (
                                <motion.div
                                    key={index}
                                    initial={{ opacity: 0, y: 18 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: 0.58 + index * 0.06 }}
                                    className="rounded-2xl border border-slate-100/80 bg-white shadow-[0_4px_24px_-12px_rgba(15,23,42,0.12)] transition-shadow hover:shadow-[0_8px_32px_-12px_rgba(15,23,42,0.18)]"
                                >
                                    <button
                                        onClick={() => toggleFaq(index)}
                                        className="flex w-full items-center justify-between px-6 py-4 text-left"
                                    >
                                        <span className="text-sm font-medium text-slate-800 pr-4">
                                            {item.question}
                                        </span>
                                        <motion.span
                                            animate={{ rotate: openFaqs.has(index) ? 180 : 0 }}
                                            transition={{ duration: 0.25, ease: 'easeInOut' }}
                                            className="flex-shrink-0 text-slate-400"
                                        >
                                            <ChevronDown className="h-4 w-4" />
                                        </motion.span>
                                    </button>
                                    <AnimatePresence initial={false}>
                                        {openFaqs.has(index) && (
                                            <motion.div
                                                initial={{ height: 0, opacity: 0 }}
                                                animate={{ height: 'auto', opacity: 1 }}
                                                exit={{ height: 0, opacity: 0 }}
                                                transition={{ duration: 0.25, ease: 'easeInOut' }}
                                                className="overflow-hidden"
                                            >
                                                <div className="border-t border-slate-100 px-6 pb-5 pt-4">
                                                    <p className="text-sm leading-relaxed text-slate-600">
                                                        {item.answer}
                                                    </p>
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </motion.div>
                            ))}
                        </div>
                    </div>

                    {/* Quick Links Section */}
                    <div>
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.5, delay: 0.9 }}
                            className="mb-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400"
                        >
                            Helpful Resources
                        </motion.p>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                            {QUICK_LINKS.map((link, index) => {
                                const Icon = link.icon;
                                return (
                                    <motion.a
                                        key={link.title}
                                        href={link.href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        initial={{ opacity: 0, y: 18 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5, delay: 0.93 + index * 0.06 }}
                                        className="group flex items-start gap-4 rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-all hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)] hover:border-teal-200"
                                    >
                                        <div className="flex-shrink-0 rounded-2xl bg-slate-50 p-3 transition-colors group-hover:bg-teal-50">
                                            <Icon className="h-5 w-5 text-slate-500 transition-colors group-hover:text-teal-600" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <h4 className="text-sm font-semibold text-slate-800">
                                                    {link.title}
                                                </h4>
                                                <ExternalLink className="h-3 w-3 text-slate-300 transition-colors group-hover:text-teal-500" />
                                            </div>
                                            <p className="mt-0.5 text-xs text-slate-500">
                                                {link.description}
                                            </p>
                                        </div>
                                    </motion.a>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Create Ticket Modal */}
                <AnimatePresence>
                    {showCreateModal && (
                        <CreateTicketModal
                            onClose={() => setShowCreateModal(false)}
                            onCreated={() => { setLoading(true); fetchTickets(); }}
                        />
                    )}
                </AnimatePresence>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
