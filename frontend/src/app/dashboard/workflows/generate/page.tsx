'use client';

import React, { useState } from 'react';
import PremiumShell from '@/components/layout/PremiumShell';
import { generateWorkflow, startWorkflowByTemplateId } from '@/services/workflows';
import { useRouter } from 'next/navigation';
import { Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { toast } from 'sonner';

const CATEGORIES = [
    'Custom', 'Strategy', 'Marketing', 'Sales', 'Operations',
    'HR', 'Product', 'Support', 'Finance', 'Legal', 'Data'
];

export default function GenerateWorkflowPage() {
    const router = useRouter();
    const [description, setDescription] = useState('');
    const [category, setCategory] = useState('Custom');
    const [generating, setGenerating] = useState(false);
    const [result, setResult] = useState<{ template_id?: string; name?: string; message?: string } | null>(null);
    const [starting, setStarting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!description.trim()) {
            toast.error('Please describe the workflow you want to generate');
            return;
        }

        setGenerating(true);
        try {
            const generated = await generateWorkflow(description, category.toLowerCase());
            setResult(generated);
            toast.success('Workflow generation initiated!');
        } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : '';
            // Check for the expected 501 / coming soon message logic from service
            if (errorMessage.includes('AI generation coming soon')) {
                toast.info('AI Workflow Generation is coming soon!', {
                    description: 'We have registered your interest.'
                });
            } else {
                toast.error('Failed to generate workflow');
            }
        } finally {
            setGenerating(false);
        }
    };

    const handleStartGenerated = async () => {
        if (!result?.template_id) return;
        setStarting(true);
        try {
            await startWorkflowByTemplateId(result.template_id, description.slice(0, 200), undefined, 'user_ui');
            toast.success('Generated workflow started');
            router.push('/dashboard/workflows/active');
        } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to start generated workflow';
            toast.error(errorMessage);
        } finally {
            setStarting(false);
        }
    };

    return (
        <DashboardErrorBoundary fallbackTitle="Generate Workflow Error">
            <PremiumShell>
                <motion.div
                    className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <div className="mb-6">
                        <Breadcrumb items={[
                            { label: 'Home', href: '/dashboard' },
                            { label: 'Workflows', href: '/dashboard/workflows/templates' },
                            { label: 'Generate' },
                        ]} />
                    </div>

                    {/* Header */}
                    <div className="mb-8 text-center">
                        <div className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-400 to-purple-500 p-3 shadow-lg shadow-purple-200 mb-4">
                            <Sparkles className="h-8 w-8 text-white" />
                        </div>
                        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Generate with AI</h1>
                        <p className="mt-2 text-lg text-slate-500">
                            Describe your process, and our AI will design a custom workflow for you in seconds.
                        </p>
                    </div>

                    {/* Form */}
                    <div className="bg-white rounded-[28px] shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] border border-slate-100/80 p-8">
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div>
                                <label htmlFor="description" className="block text-sm font-medium text-slate-700 mb-2">
                                    Describe your workflow
                                </label>
                                <textarea
                                    id="description"
                                    rows={6}
                                    className="block w-full rounded-xl border-slate-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-4 border"
                                    placeholder="E.g., I need a workflow to onboard new marketing partners. It should check their contract status, trigger an email welcome sequence, and set up a task for the finance team..."
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                />
                            </div>

                            <div>
                                <label htmlFor="category" className="block text-sm font-medium text-slate-700 mb-2">
                                    Category
                                </label>
                                <select
                                    id="category"
                                    className="block w-full rounded-xl border-slate-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-3 border"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                >
                                    {CATEGORIES.map(cat => (
                                        <option key={cat} value={cat}>{cat}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="pt-4">
                                <button
                                    type="submit"
                                    disabled={generating}
                                    className="w-full flex justify-center items-center py-4 px-6 border border-transparent rounded-xl shadow-sm text-lg font-medium text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                >
                                    {generating ? (
                                        <>
                                            <Sparkles className="animate-spin h-5 w-5 mr-3" />
                                            Generating Magic...
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles className="h-5 w-5 mr-2" />
                                            Generate Workflow
                                        </>
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>

                    {/* Info Box */}
                    <div className="mt-8 bg-blue-50 rounded-[28px] p-6 border border-blue-100">
                        <h4 className="text-sm font-semibold text-blue-900 mb-2">How it works</h4>
                        <ul className="text-sm text-blue-700 space-y-2 list-disc pl-5">
                            <li>AI analyzes your description to understand the process.</li>
                            <li>It identifies key steps, roles, and necessary approvals.</li>
                            <li>A draft workflow is created which you can customize before activating.</li>
                        </ul>
                    </div>

                    {result?.template_id && (
                        <div className="mt-6 bg-emerald-50 rounded-[28px] p-6 border border-emerald-100">
                            <h4 className="text-sm font-semibold text-emerald-900 mb-2">Generated workflow ready</h4>
                            <p className="text-sm text-emerald-800">
                                {result.name || 'Workflow template'} has been generated and saved.
                            </p>
                            <div className="mt-4 flex items-center gap-2">
                                <button
                                    onClick={handleStartGenerated}
                                    disabled={starting}
                                    className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
                                >
                                    {starting ? 'Starting...' : 'Start Now'}
                                </button>
                                <button
                                    onClick={() => router.push(`/dashboard/workflows/editor/${result.template_id}`)}
                                    className="px-4 py-2 rounded-xl bg-white text-emerald-700 text-sm font-medium border border-emerald-200 hover:bg-emerald-100"
                                >
                                    Open Full Editor
                                </button>
                            </div>
                        </div>
                    )}
                </motion.div>
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
