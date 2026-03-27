'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { listWorkflowTemplates, startWorkflow, WorkflowTemplate } from '@/services/workflows';
import WorkflowTemplateCard from '@/components/workflows/WorkflowTemplateCard';
import PremiumShell from '@/components/layout/PremiumShell';
import { Search, X, Workflow, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { toast } from 'sonner';

const CATEGORIES = [
    'All', 'Strategy', 'Marketing', 'Sales', 'Operations',
    'HR', 'Product', 'Support', 'Finance', 'Legal', 'Data', 'Content'
];

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-12 w-64 rounded-xl bg-slate-100" />
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-10 w-24 rounded-full bg-slate-100" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="h-64 rounded-[28px] bg-slate-100" />
        ))}
      </div>
    </div>
  );
}

export default function WorkflowTemplatesPage() {
    const router = useRouter();
    const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedCategory, setSelectedCategory] = useState('All');
    const [searchQuery, setSearchQuery] = useState('');

    // Start Workflow Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
    const [workflowTopic, setWorkflowTopic] = useState('');
    const [starting, setStarting] = useState(false);

    useEffect(() => {
        fetchTemplates();
    }, [selectedCategory]);

    const fetchTemplates = async () => {
        setLoading(true);
        setError(null);
        try {
            const category = selectedCategory === 'All' ? undefined : selectedCategory.toLowerCase();
            const data = await listWorkflowTemplates(category);
            setTemplates(data);
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to load templates';
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleStartClick = (template: WorkflowTemplate) => {
        setSelectedTemplate(template);
        setWorkflowTopic('');
        setIsModalOpen(true);
    };

    const handleEditClick = (template: WorkflowTemplate) => {
        if (!template?.id) {
            toast.error('This workflow template is missing an ID and cannot be opened.');
            return;
        }
        router.push(`/dashboard/workflows/editor/${template.id}`);
    };

    const handleConfirmStart = async () => {
        if (!selectedTemplate) return;

        setStarting(true);
        try {
            await startWorkflow(selectedTemplate.name, workflowTopic);
            toast.success('Workflow started successfully');
            setIsModalOpen(false);
            router.push('/dashboard/workflows/active');
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to start workflow';
            toast.error(errorMessage);
        } finally {
            setStarting(false);
        }
    };

    const filteredTemplates = templates.filter((t) => {
        const name = typeof t?.name === 'string' ? t.name : '';
        const description = typeof t?.description === 'string' ? t.description : '';
        const q = searchQuery.toLowerCase();
        return name.toLowerCase().includes(q) || description.toLowerCase().includes(q);
    });

    return (
        <DashboardErrorBoundary fallbackTitle="Workflow Templates Error">
            <PremiumShell>
                <motion.div
                    className="mx-auto max-w-7xl p-6"
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <div className="mb-4">
                        <Breadcrumb items={[
                            { label: 'Home', href: '/dashboard' },
                            { label: 'Workflows', href: '/dashboard/workflows/templates' },
                            { label: 'Templates' },
                        ]} />
                    </div>

                    <div className="mb-8 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-400 to-indigo-500 shadow-lg shadow-blue-200">
                                <Workflow className="h-6 w-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                                    Workflow Templates
                                </h1>
                                <p className="mt-0.5 text-sm text-slate-500">
                                    Choose from our library of verified templates to automate your repetitive tasks.
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={() => router.push('/dashboard/workflows/editor/new')}
                            className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700"
                        >
                            <Plus className="h-4 w-4" />
                            Create Draft
                        </button>
                    </div>

                    {/* Filters */}
                    <div className="flex flex-col sm:flex-row justify-between items-center mb-6 space-y-4 sm:space-y-0">
                        <div className="flex overflow-x-auto pb-2 sm:pb-0 hide-scrollbar w-full sm:w-auto space-x-2">
                            {CATEGORIES.map(category => (
                                <button
                                    key={category}
                                    onClick={() => setSelectedCategory(category)}
                                    className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${selectedCategory === category
                                            ? 'bg-slate-900 text-white'
                                            : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
                                        }`}
                                >
                                    {category}
                                </button>
                            ))}
                        </div>

                        <div className="relative w-full sm:w-64">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <Search className="h-4 w-4 text-slate-400" />
                            </div>
                            <input
                                type="text"
                                placeholder="Search templates..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-xl leading-5 bg-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 focus:border-slate-400 sm:text-sm"
                            />
                        </div>
                    </div>

                    {/* Content */}
                    {loading ? (
                        <LoadingSkeleton />
                    ) : error ? (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-600">
                            {error}
                            <button
                                onClick={fetchTemplates}
                                className="block mx-auto mt-4 text-sm underline hover:text-red-800"
                            >
                                Try Again
                            </button>
                        </div>
                    ) : filteredTemplates.length === 0 ? (
                        <div className="bg-slate-50 border border-dashed border-slate-200 rounded-[28px] p-12 text-center">
                            <h3 className="text-lg font-medium text-slate-900">No templates found</h3>
                            <p className="mt-2 text-slate-500">Try adjusting your filters or search query.</p>
                            <button
                                onClick={() => { setSelectedCategory('All'); setSearchQuery(''); }}
                                className="mt-4 text-blue-600 hover:underline"
                            >
                                Clear all filters
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {filteredTemplates.map(template => (
                                <WorkflowTemplateCard
                                    key={template.id || `${template.name}-${template.category}`}
                                    template={{
                                        ...template,
                                        name: typeof template.name === 'string' ? template.name : 'Untitled Workflow',
                                        description: typeof template.description === 'string' ? template.description : '',
                                        category: typeof template.category === 'string' ? template.category : 'custom',
                                    }}
                                    onStart={handleStartClick}
                                    onEdit={handleEditClick}
                                />
                            ))}
                        </div>
                    )}
                </motion.div>

                {/* Start Workflow Modal */}
                <AnimatePresence>
                    {isModalOpen && selectedTemplate && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4"
                        >
                            <motion.div
                                initial={{ opacity: 0, y: 10, scale: 0.98 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 10, scale: 0.98 }}
                                className="w-full max-w-lg rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                            >
                                {/* Modal header */}
                                <div className="flex items-start justify-between mb-4">
                                    <h3 className="text-lg font-semibold text-slate-900">Start Workflow</h3>
                                    <button onClick={() => setIsModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
                                        <X className="h-5 w-5" />
                                    </button>
                                </div>
                                <p className="text-sm text-slate-500 mb-4">
                                    Starting <span className="font-semibold text-slate-700">{selectedTemplate.name}</span>. Provide context below.
                                </p>
                                <label className="block text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-2">
                                    Topic / Context (Optional)
                                </label>
                                <input
                                    type="text"
                                    className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                                    placeholder="e.g. Q4 Marketing Strategy"
                                    value={workflowTopic}
                                    onChange={(e) => setWorkflowTopic(e.target.value)}
                                />
                                <div className="flex justify-end gap-2 mt-6">
                                    <button
                                        onClick={() => setIsModalOpen(false)}
                                        className="px-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleConfirmStart}
                                        disabled={starting}
                                        className="px-5 py-2.5 rounded-xl bg-teal-600 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
                                    >
                                        {starting ? 'Starting...' : 'Start Workflow'}
                                    </button>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
