'use client';

import { PremiumShell } from '@/components/layout/PremiumShell';
import MetricCard from '@/components/ui/MetricCard';
import { motion } from 'framer-motion';
import {
  Users,
  MessageSquare,
  Calendar,
  GitPullRequest,
  ExternalLink,
  Heart,
  Sparkles,
  ArrowRight,
  Clock,
  Trophy,
} from 'lucide-react';

const DISCUSSIONS = [
  { id: 1, title: 'Best workflow templates for e-commerce', author: 'Alex M.', replies: 23, likes: 45, category: 'Workflows', time: '2 hours ago' },
  { id: 2, title: 'Tips for getting the most out of AI agents', author: 'Priya K.', replies: 18, likes: 67, category: 'AI Agents', time: '5 hours ago' },
  { id: 3, title: 'Financial forecasting accuracy improvements', author: 'Jordan T.', replies: 12, likes: 31, category: 'Finance', time: '1 day ago' },
  { id: 4, title: 'New integration: connecting Notion to Pikar-AI', author: 'Sam L.', replies: 34, likes: 89, category: 'Integrations', time: '1 day ago' },
  { id: 5, title: 'Compliance automation for GDPR — share your setup', author: 'Maria R.', replies: 8, likes: 22, category: 'Compliance', time: '2 days ago' },
];

const EVENTS = [
  { id: 1, title: 'Weekly Office Hours', date: 'Every Thursday', time: '2:00 PM EST', type: 'recurring' as const, attendees: 45 },
  { id: 2, title: 'Workflow Masterclass: Multi-Agent Pipelines', date: 'Mar 22, 2026', time: '11:00 AM EST', type: 'workshop' as const, attendees: 128 },
  { id: 3, title: 'Community AMA with CEO', date: 'Mar 28, 2026', time: '3:00 PM EST', type: 'ama' as const, attendees: 312 },
  { id: 4, title: 'Pikar-AI v2.0 Launch Party', date: 'Apr 5, 2026', time: '1:00 PM EST', type: 'launch' as const, attendees: 500 },
];

const CONTRIBUTORS = [
  { name: 'Sarah C.', contributions: 234, role: 'Power User' },
  { name: 'Alex M.', contributions: 189, role: 'Workflow Expert' },
  { name: 'Priya K.', contributions: 167, role: 'AI Pioneer' },
  { name: 'Jordan T.', contributions: 145, role: 'Finance Pro' },
  { name: 'Sam L.', contributions: 132, role: 'Integration Guru' },
  { name: 'Maria R.', contributions: 98, role: 'Compliance Lead' },
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

const CATEGORY_COLORS: Record<string, string> = {
  Workflows: 'bg-amber-50 text-amber-700',
  'AI Agents': 'bg-violet-50 text-violet-700',
  Finance: 'bg-emerald-50 text-emerald-700',
  Integrations: 'bg-blue-50 text-blue-700',
  Compliance: 'bg-rose-50 text-rose-700',
};

const AVATAR_GRADIENTS = [
  'from-teal-400 to-emerald-500',
  'from-violet-400 to-purple-500',
  'from-amber-400 to-orange-500',
  'from-blue-400 to-indigo-500',
  'from-rose-400 to-pink-500',
  'from-cyan-400 to-teal-500',
];

function getInitials(name: string) {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase();
}

export default function CommunityPage() {
  return (
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
          <a
            href="https://discord.gg/pikar-ai"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition-all hover:bg-teal-700 hover:shadow-teal-700/30 active:scale-[0.98]"
          >
            Join Discord
            <ExternalLink className="h-4 w-4" />
          </a>
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
            label="Active Discussions"
            value={156}
            icon={MessageSquare}
            gradient="from-violet-400 to-purple-500"
            delay={0.1}
          />
          <MetricCard
            label="Events This Month"
            value={4}
            icon={Calendar}
            gradient="from-amber-400 to-orange-500"
            delay={0.15}
          />
          <MetricCard
            label="Contributions"
            value="1.2k"
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
          {/* Trending Discussions */}
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
          >
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              Trending Discussions
            </h3>
            <div className="mt-5 space-y-4">
              {DISCUSSIONS.map((d, i) => (
                <motion.div
                  key={d.id}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, delay: 0.35 + i * 0.06 }}
                  className="group flex items-start gap-3.5 rounded-2xl p-3 transition-colors hover:bg-slate-50 cursor-pointer"
                >
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${AVATAR_GRADIENTS[i % AVATAR_GRADIENTS.length]} text-[11px] font-bold text-white shadow-sm`}>
                    {getInitials(d.author)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 group-hover:text-teal-700 transition-colors truncate">
                      {d.title}
                    </p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                      <span className="font-medium text-slate-500">
                        {d.author}
                      </span>
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${CATEGORY_COLORS[d.category] || 'bg-slate-100 text-slate-600'}`}>
                        {d.category}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" />
                        {d.replies}
                      </span>
                      <span className="flex items-center gap-1">
                        <Heart className="h-3 w-3" />
                        {d.likes}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {d.time}
                      </span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Upcoming Events */}
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

        {/* Top Contributors */}
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
            {CONTRIBUTORS.map((c, i) => (
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
                  <p className="text-sm font-semibold text-slate-900">
                    {c.name}
                  </p>
                  <span className="mt-0.5 inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-medium text-slate-500">
                    {c.role}
                  </span>
                </div>
                <p className="text-lg font-bold text-teal-600">
                  {c.contributions}
                </p>
                <p className="text-[10px] uppercase tracking-wider text-slate-400">
                  contributions
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </PremiumShell>
  );
}
