'use client';

import { useState } from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import MetricCard from '@/components/ui/MetricCard';
import { motion, AnimatePresence } from 'framer-motion';
import {
    BookOpen,
    CheckCircle2,
    Clock,
    Award,
    Play,
    ArrowRight,
    Sparkles,
    GraduationCap,
} from 'lucide-react';

const TUTORIALS = [
    { id: 1, title: 'Getting Started with Pikar-AI', category: 'Getting Started', difficulty: 'Beginner' as const, duration: '15 min', lessons: 5, progress: 100, gradient: 'from-teal-400 to-emerald-500', description: 'Learn the basics of navigating your AI executive dashboard and setting up your first workflow.' },
    { id: 2, title: 'Mastering the 11 AI Agents', category: 'AI Agents', difficulty: 'Intermediate' as const, duration: '45 min', lessons: 11, progress: 64, gradient: 'from-violet-400 to-purple-500', description: 'Deep dive into each specialized agent — financial, content, strategic, sales, and more.' },
    { id: 3, title: 'Building Custom Workflows', category: 'Workflows', difficulty: 'Advanced' as const, duration: '30 min', lessons: 8, progress: 0, gradient: 'from-sky-400 to-blue-500', description: 'Create automated workflow pipelines that chain multiple agents for complex business processes.' },
    { id: 4, title: 'Financial Dashboard Mastery', category: 'Analytics', difficulty: 'Intermediate' as const, duration: '20 min', lessons: 6, progress: 33, gradient: 'from-amber-400 to-orange-500', description: 'Understand revenue tracking, invoice management, and financial forecasting features.' },
    { id: 5, title: 'Content Calendar & Publishing', category: 'AI Agents', difficulty: 'Beginner' as const, duration: '25 min', lessons: 7, progress: 0, gradient: 'from-rose-400 to-pink-500', description: 'Master multi-platform content creation, scheduling, and performance analytics.' },
    { id: 6, title: 'Connecting Integrations', category: 'Integrations', difficulty: 'Intermediate' as const, duration: '35 min', lessons: 9, progress: 100, gradient: 'from-emerald-400 to-teal-500', description: 'Set up Google Workspace, social media accounts, Stripe, and third-party MCP tools.' },
];

const CATEGORIES = ['All', 'Getting Started', 'AI Agents', 'Workflows', 'Analytics', 'Integrations'];

const RECOMMENDED = [
    { id: 7, title: 'Advanced Agent Orchestration', category: 'AI Agents', difficulty: 'Advanced' as const, duration: '40 min', lessons: 10, progress: 0, gradient: 'from-indigo-400 to-violet-500', description: 'Learn to chain agents together for multi-step business automation and executive decision support.' },
    { id: 8, title: 'Sales Pipeline Optimization', category: 'Analytics', difficulty: 'Intermediate' as const, duration: '25 min', lessons: 7, progress: 0, gradient: 'from-cyan-400 to-sky-500', description: 'Leverage AI-driven insights to optimize your sales funnel and forecast revenue accurately.' },
    { id: 9, title: 'Compliance & Risk Management', category: 'AI Agents', difficulty: 'Intermediate' as const, duration: '30 min', lessons: 8, progress: 0, gradient: 'from-fuchsia-400 to-pink-500', description: 'Configure the compliance agent to monitor regulations and flag potential risks automatically.' },
];

const DIFFICULTY_STYLES = {
    Beginner: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Intermediate: 'bg-amber-50 text-amber-700 border-amber-200',
    Advanced: 'bg-rose-50 text-rose-700 border-rose-200',
};

function TutorialCard({ tutorial, index }: { tutorial: typeof TUTORIALS[number]; index: number }) {
    const isCompleted = tutorial.progress === 100;
    const isInProgress = tutorial.progress > 0 && tutorial.progress < 100;

    return (
        <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10, transition: { duration: 0.2 } }}
            transition={{ duration: 0.5, delay: index * 0.08, ease: [0.21, 0.47, 0.32, 0.98] }}
            layout
            className="rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden flex flex-col transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]"
        >
            {/* Gradient header band */}
            <div className={`h-2.5 bg-gradient-to-r ${tutorial.gradient}`} />

            <div className="p-6 flex flex-col flex-1">
                {/* Badges */}
                <div className="flex items-center gap-2 mb-3">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-100">
                        {tutorial.category}
                    </span>
                    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full border ${DIFFICULTY_STYLES[tutorial.difficulty]}`}>
                        {tutorial.difficulty}
                    </span>
                </div>

                {/* Title */}
                <h3 className="text-lg font-semibold text-slate-900 tracking-tight mb-2">
                    {tutorial.title}
                </h3>

                {/* Description */}
                <p className="text-sm text-slate-500 leading-relaxed line-clamp-2 mb-4">
                    {tutorial.description}
                </p>

                {/* Meta info */}
                <div className="flex items-center gap-4 text-xs text-slate-400 mb-4">
                    <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        {tutorial.duration}
                    </span>
                    <span className="flex items-center gap-1.5">
                        <BookOpen className="h-3.5 w-3.5" />
                        {tutorial.lessons} lessons
                    </span>
                </div>

                {/* Spacer to push bottom content down */}
                <div className="flex-1" />

                {/* Progress bar */}
                <div className="mb-4">
                    <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-medium text-slate-500">
                            {isCompleted ? 'Completed' : isInProgress ? 'In Progress' : 'Not Started'}
                        </span>
                        <span className="text-[11px] font-semibold text-slate-600">{tutorial.progress}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${tutorial.progress}%` }}
                            transition={{ duration: 0.8, delay: index * 0.08 + 0.3, ease: [0.21, 0.47, 0.32, 0.98] }}
                            className={`h-full rounded-full bg-gradient-to-r ${
                                isCompleted
                                    ? 'from-emerald-400 to-teal-500'
                                    : isInProgress
                                    ? 'from-amber-400 to-orange-400'
                                    : 'from-slate-300 to-slate-300'
                            }`}
                        />
                    </div>
                </div>

                {/* Action button */}
                <button
                    className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-2xl text-sm font-semibold transition-all ${
                        isCompleted
                            ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                            : isInProgress
                            ? 'bg-teal-600 text-white hover:bg-teal-700 shadow-md shadow-teal-200'
                            : 'bg-slate-900 text-white hover:bg-slate-800 shadow-md shadow-slate-200'
                    }`}
                >
                    {isCompleted ? (
                        <>
                            <CheckCircle2 className="h-4 w-4" />
                            Review Course
                        </>
                    ) : isInProgress ? (
                        <>
                            <Play className="h-4 w-4" />
                            Continue
                        </>
                    ) : (
                        <>
                            <Play className="h-4 w-4" />
                            Start Course
                        </>
                    )}
                </button>
            </div>
        </motion.div>
    );
}

export default function LearningPage() {
    const [activeCategory, setActiveCategory] = useState('All');

    const filteredTutorials = activeCategory === 'All'
        ? TUTORIALS
        : TUTORIALS.filter((t) => t.category === activeCategory);

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
                            Learning Hub
                        </h1>
                        <p className="mt-1 text-sm text-slate-500">
                            Master every feature of your AI executive system
                        </p>
                    </div>
                    <button className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-teal-200 transition-colors hover:bg-teal-700">
                        <GraduationCap className="h-4 w-4" />
                        Browse All Courses
                    </button>
                </motion.div>

                {/* KPI Row */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <MetricCard
                        label="Available Courses"
                        value={24}
                        icon={BookOpen}
                        gradient="from-teal-400 to-emerald-500"
                        delay={0.05}
                    />
                    <MetricCard
                        label="Completed"
                        value={8}
                        icon={CheckCircle2}
                        gradient="from-violet-400 to-purple-500"
                        delay={0.1}
                    />
                    <MetricCard
                        label="In Progress"
                        value={3}
                        icon={Clock}
                        gradient="from-amber-400 to-orange-500"
                        delay={0.15}
                    />
                    <MetricCard
                        label="Certificates"
                        value={5}
                        icon={Award}
                        gradient="from-rose-400 to-pink-500"
                        delay={0.2}
                    />
                </div>

                {/* Category Filter Pills */}
                <motion.div
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.25 }}
                >
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-3">
                        Categories
                    </p>
                    <div className="inline-flex flex-wrap gap-1 rounded-2xl bg-slate-100 p-1">
                        {CATEGORIES.map((cat) => (
                            <button
                                key={cat}
                                onClick={() => setActiveCategory(cat)}
                                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                                    activeCategory === cat
                                        ? 'bg-white text-slate-900 shadow-sm'
                                        : 'text-slate-500 hover:text-slate-700'
                                }`}
                            >
                                {cat}
                            </button>
                        ))}
                    </div>
                </motion.div>

                {/* Tutorial Grid */}
                <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-4">
                        {activeCategory === 'All' ? 'All Courses' : activeCategory}
                        <span className="ml-2 text-slate-300">({filteredTutorials.length})</span>
                    </p>
                    <AnimatePresence mode="popLayout">
                        <motion.div
                            layout
                            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                        >
                            {filteredTutorials.map((tutorial, i) => (
                                <TutorialCard key={tutorial.id} tutorial={tutorial} index={i} />
                            ))}
                        </motion.div>
                    </AnimatePresence>

                    {filteredTutorials.length === 0 && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex flex-col items-center justify-center py-16 text-center"
                        >
                            <BookOpen className="h-10 w-10 text-slate-300 mb-3" />
                            <p className="text-sm text-slate-400">No courses found in this category.</p>
                        </motion.div>
                    )}
                </div>

                {/* Recommended for You */}
                <motion.div
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                >
                    <div className="flex items-center gap-3 mb-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-md">
                            <Sparkles className="h-4 w-4 text-white" />
                        </div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                            Recommended for You
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {RECOMMENDED.map((tutorial, i) => (
                            <motion.div
                                key={tutorial.id}
                                initial={{ opacity: 0, y: 18 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: 0.35 + i * 0.08, ease: [0.21, 0.47, 0.32, 0.98] }}
                                className="rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]"
                            >
                                <div className={`h-24 bg-gradient-to-br ${tutorial.gradient} flex items-end p-5`}>
                                    <h3 className="text-lg font-semibold text-white tracking-tight drop-shadow-sm">
                                        {tutorial.title}
                                    </h3>
                                </div>
                                <div className="p-5">
                                    <p className="text-sm text-slate-500 leading-relaxed line-clamp-2 mb-4">
                                        {tutorial.description}
                                    </p>
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3 text-xs text-slate-400">
                                            <span className="flex items-center gap-1">
                                                <Clock className="h-3.5 w-3.5" />
                                                {tutorial.duration}
                                            </span>
                                            <span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold uppercase tracking-wider ${DIFFICULTY_STYLES[tutorial.difficulty]}`}>
                                                {tutorial.difficulty}
                                            </span>
                                        </div>
                                        <button className="flex items-center gap-1.5 text-sm font-semibold text-teal-600 hover:text-teal-700 transition-colors">
                                            Start
                                            <ArrowRight className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>
            </div>
        </PremiumShell>
    );
}
