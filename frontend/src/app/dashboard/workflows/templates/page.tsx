'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { listWorkflowTemplates, startWorkflow, WorkflowTemplate } from '@/services/workflows';
import WorkflowTemplateCard from '@/components/workflows/WorkflowTemplateCard';
import PremiumShell from '@/components/layout/PremiumShell';
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { toast } from 'sonner';

const CATEGORIES = [
    'All', 'Strategy', 'Marketing', 'Sales', 'Operations',
    'HR', 'Product', 'Support', 'Finance', 'Legal', 'Data', 'Content'
];

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
        <PremiumShell>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <h1 className="text-2xl font-bold text-slate-900">Workflow Templates</h1>
                            <p className="mt-1 text-sm text-slate-500">
                                Choose from our library of verified templates to automate your repetitive tasks.
                            </p>
                        </div>
                        <button
                            onClick={() => router.push('/dashboard/workflows/editor/new')}
                            className="inline-flex items-center px-4 py-2 rounded-xl bg-slate-900 text-white text-sm hover:bg-slate-800"
                        >
                            Create Draft
                        </button>
                    </div>
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
                            <MagnifyingGlassIcon className="h-4 w-4 text-slate-400" />
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
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="bg-white rounded-3xl p-6 h-64 animate-pulse">
                                <div className="h-4 bg-slate-200 rounded w-1/4 mb-4"></div>
                                <div className="h-6 bg-slate-200 rounded w-3/4 mb-4"></div>
                                <div className="h-4 bg-slate-200 rounded w-full mb-2"></div>
                                <div className="h-4 bg-slate-200 rounded w-5/6 mb-6"></div>
                                <div className="h-10 bg-slate-200 rounded-xl w-full mt-auto"></div>
                            </div>
                        ))}
                    </div>
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
                    <div className="bg-slate-50 border border-slate-200 rounded-3xl p-12 text-center">
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
            </div>

            {/* Start Workflow Modal */}
            {isModalOpen && selectedTemplate && (
                <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
                    <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" onClick={() => setIsModalOpen(false)}></div>
                        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                        <div className="inline-block align-bottom bg-white rounded-2xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                            <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                                <div className="sm:flex sm:items-start">
                                    <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                                        <div className="flex justify-between items-start">
                                            <h3 className="text-lg leading-6 font-medium text-slate-900" id="modal-title">
                                                Start Workflow
                                            </h3>
                                            <button
                                                onClick={() => setIsModalOpen(false)}
                                                className="bg-white rounded-md text-slate-400 hover:text-slate-500 focus:outline-none"
                                            >
                                                <span className="sr-only">Close</span>
                                                <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                                            </button>
                                        </div>
                                        <div className="mt-2">
                                            <p className="text-sm text-slate-500 mb-4">
                                                You are about to start the <span className="font-semibold text-slate-700">{selectedTemplate.name}</span> workflow.
                                                Please provide some context or a specific topic.
                                            </p>
                                            <label htmlFor="topic" className="block text-sm font-medium text-slate-700 mb-1">
                                                Topic / Context (Optional)
                                            </label>
                                            <input
                                                type="text"
                                                name="topic"
                                                id="topic"
                                                className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-slate-300 rounded-md p-2 border"
                                                placeholder="e.g. Q4 Marketing Strategy"
                                                value={workflowTopic}
                                                onChange={(e) => setWorkflowTopic(e.target.value)}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-slate-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                                <button
                                    type="button"
                                    onClick={handleConfirmStart}
                                    disabled={starting}
                                    className="w-full inline-flex justify-center rounded-xl border border-transparent shadow-sm px-4 py-2 bg-slate-900 text-base font-medium text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {starting ? 'Starting...' : 'Start Workflow'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setIsModalOpen(false)}
                                    className="mt-3 w-full inline-flex justify-center rounded-xl border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </PremiumShell>
    );
}
