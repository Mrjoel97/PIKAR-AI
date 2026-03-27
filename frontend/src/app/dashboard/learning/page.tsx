'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect, useCallback } from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import MetricCard from '@/components/ui/MetricCard';
import DashboardSkeleton from '@/components/ui/DashboardSkeleton';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import EmptyState from '@/components/ui/EmptyState';
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
    AlertCircle,
} from 'lucide-react';
import {
    getCourses,
    getProgress,
    startCourse,
    type Course,
    type LearningProgress,
} from '@/services/learning';

const DIFFICULTY_STYLES = {
    beginner: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    intermediate: 'bg-amber-50 text-amber-700 border-amber-200',
    advanced: 'bg-rose-50 text-rose-700 border-rose-200',
};

const DEFAULT_GRADIENTS = [
    'from-teal-400 to-emerald-500',
    'from-violet-400 to-purple-500',
    'from-sky-400 to-blue-500',
    'from-amber-400 to-orange-500',
    'from-rose-400 to-pink-500',
    'from-emerald-400 to-teal-500',
];

const CATEGORIES = ['All', 'onboarding', 'productivity', 'finance', 'sales', 'content', 'automation', 'compliance'];

function TutorialCard({
    course,
    progress,
    index,
    onStart,
}: {
    course: Course;
    progress?: LearningProgress;
    index: number;
    onStart: (courseId: string) => void;
}) {
    const progressPercent = progress?.progress_percent ?? 0;
    const isCompleted = progressPercent >= 100;
    const isInProgress = progressPercent > 0 && progressPercent < 100;
    const gradient = course.thumbnail_gradient || DEFAULT_GRADIENTS[index % DEFAULT_GRADIENTS.length];
    const difficulty = course.difficulty as keyof typeof DIFFICULTY_STYLES;

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
            <div className={`h-2.5 bg-gradient-to-r ${gradient}`} />

            <div className="p-6 flex flex-col flex-1">
                {/* Badges */}
                <div className="flex items-center gap-2 mb-3">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-100">
                        {course.category}
                    </span>
                    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full border ${DIFFICULTY_STYLES[difficulty] || DIFFICULTY_STYLES.beginner}`}>
                        {course.difficulty}
                    </span>
                </div>

                {/* Title */}
                <h3 className="text-lg font-semibold text-slate-900 tracking-tight mb-2">
                    {course.title}
                </h3>

                {/* Description */}
                <p className="text-sm text-slate-500 leading-relaxed line-clamp-2 mb-4">
                    {course.description || 'Explore this course to learn more.'}
                </p>

                {/* Meta info */}
                <div className="flex items-center gap-4 text-xs text-slate-400 mb-4">
                    <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        {course.duration_minutes} min
                    </span>
                    <span className="flex items-center gap-1.5">
                        <BookOpen className="h-3.5 w-3.5" />
                        {course.lessons_count} lessons
                    </span>
                </div>

                {/* Spacer */}
                <div className="flex-1" />

                {/* Progress bar */}
                <div className="mb-4">
                    <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-medium text-slate-500">
                            {isCompleted ? 'Completed' : isInProgress ? 'In Progress' : 'Not Started'}
                        </span>
                        <span className="text-[11px] font-semibold text-slate-600">{Math.round(progressPercent)}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${progressPercent}%` }}
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
                    onClick={() => !isCompleted && onStart(course.id)}
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
    const [courses, setCourses] = useState<Course[]>([]);
    const [progressMap, setProgressMap] = useState<Record<string, LearningProgress>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = useCallback(async () => {
        try {
            setError(null);
            const [coursesData, progressData] = await Promise.all([
                getCourses(),
                getProgress(),
            ]);
            setCourses(coursesData);
            const map: Record<string, LearningProgress> = {};
            for (const p of progressData) {
                map[p.course_id] = p;
            }
            setProgressMap(map);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load learning data');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleStartCourse = async (courseId: string) => {
        try {
            const progress = await startCourse(courseId);
            setProgressMap((prev) => ({ ...prev, [courseId]: progress }));
        } catch {
            // Silently fail — user can retry
        }
    };

    const filteredCourses = activeCategory === 'All'
        ? courses
        : courses.filter((c) => c.category === activeCategory);

    const recommendedCourses = courses.filter((c) => c.is_recommended && !progressMap[c.id]);
    const completedCount = Object.values(progressMap).filter((p) => p.status === 'completed').length;
    const inProgressCount = Object.values(progressMap).filter((p) => p.status === 'in_progress').length;

    // Derive unique categories from actual data
    const dynamicCategories = ['All', ...Array.from(new Set(courses.map((c) => c.category)))];
    const displayCategories = courses.length > 0 ? dynamicCategories : CATEGORIES;

    if (loading) {
        return (
            <PremiumShell>
                <DashboardSkeleton rows={3} columns={3} showMetricCards={true} />
            </PremiumShell>
        );
    }

    return (
        <DashboardErrorBoundary fallbackTitle="Learning Hub Error">
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
                            value={courses.length}
                            icon={BookOpen}
                            gradient="from-teal-400 to-emerald-500"
                            delay={0.05}
                        />
                        <MetricCard
                            label="Completed"
                            value={completedCount}
                            icon={CheckCircle2}
                            gradient="from-violet-400 to-purple-500"
                            delay={0.1}
                        />
                        <MetricCard
                            label="In Progress"
                            value={inProgressCount}
                            icon={Clock}
                            gradient="from-amber-400 to-orange-500"
                            delay={0.15}
                        />
                        <MetricCard
                            label="Certificates"
                            value={completedCount}
                            icon={Award}
                            gradient="from-rose-400 to-pink-500"
                            delay={0.2}
                        />
                    </div>

                    {error && (
                        <div className="flex items-center gap-3 rounded-[28px] border border-rose-200 bg-rose-50 px-6 py-5">
                            <AlertCircle className="h-5 w-5 text-rose-500 flex-shrink-0" />
                            <p className="text-sm text-rose-700">{error}</p>
                            <button
                                onClick={() => { setLoading(true); fetchData(); }}
                                className="ml-auto rounded-xl bg-rose-100 px-4 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-200 transition-colors"
                            >
                                Retry
                            </button>
                        </div>
                    )}

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
                            {displayCategories.map((cat) => (
                                <button
                                    key={cat}
                                    onClick={() => setActiveCategory(cat)}
                                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all capitalize ${
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

                    {/* Course Grid */}
                    <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-4">
                            {activeCategory === 'All' ? 'All Courses' : activeCategory}
                            <span className="ml-2 text-slate-300">({filteredCourses.length})</span>
                        </p>
                        {filteredCourses.length === 0 ? (
                            <EmptyState
                                icon={BookOpen}
                                title="No courses found"
                                description={courses.length === 0
                                    ? 'Courses will appear here once they are added to the platform.'
                                    : 'No courses found in this category. Try selecting a different filter.'}
                                gradient="from-teal-400 to-emerald-500"
                            />
                        ) : (
                            <AnimatePresence mode="popLayout">
                                <motion.div layout className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {filteredCourses.map((course, i) => (
                                        <TutorialCard
                                            key={course.id}
                                            course={course}
                                            progress={progressMap[course.id]}
                                            index={i}
                                            onStart={handleStartCourse}
                                        />
                                    ))}
                                </motion.div>
                            </AnimatePresence>
                        )}
                    </div>

                    {/* Recommended for You */}
                    {recommendedCourses.length > 0 && (
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
                                {recommendedCourses.slice(0, 3).map((course, i) => {
                                    const gradient = course.thumbnail_gradient || DEFAULT_GRADIENTS[i % DEFAULT_GRADIENTS.length];
                                    return (
                                        <motion.div
                                            key={course.id}
                                            initial={{ opacity: 0, y: 18 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ duration: 0.5, delay: 0.35 + i * 0.08, ease: [0.21, 0.47, 0.32, 0.98] }}
                                            className="rounded-[28px] border border-slate-100/80 bg-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden transition-shadow hover:shadow-[0_24px_70px_-30px_rgba(15,23,42,0.45)]"
                                        >
                                            <div className={`h-24 bg-gradient-to-br ${gradient} flex items-end p-5`}>
                                                <h3 className="text-lg font-semibold text-white tracking-tight drop-shadow-sm">
                                                    {course.title}
                                                </h3>
                                            </div>
                                            <div className="p-5">
                                                <p className="text-sm text-slate-500 leading-relaxed line-clamp-2 mb-4">
                                                    {course.description || 'Explore this recommended course.'}
                                                </p>
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-3 text-xs text-slate-400">
                                                        <span className="flex items-center gap-1">
                                                            <Clock className="h-3.5 w-3.5" />
                                                            {course.duration_minutes} min
                                                        </span>
                                                        <span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold uppercase tracking-wider ${DIFFICULTY_STYLES[course.difficulty] || DIFFICULTY_STYLES.beginner}`}>
                                                            {course.difficulty}
                                                        </span>
                                                    </div>
                                                    <button
                                                        onClick={() => handleStartCourse(course.id)}
                                                        className="flex items-center gap-1.5 text-sm font-semibold text-teal-600 hover:text-teal-700 transition-colors"
                                                    >
                                                        Start
                                                        <ArrowRight className="h-3.5 w-3.5" />
                                                    </button>
                                                </div>
                                            </div>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        </motion.div>
                    )}
                </div>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
