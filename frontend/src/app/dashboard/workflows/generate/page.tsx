'use client';

import React, { useState } from 'react';
import PremiumShell from '@/components/layout/PremiumShell';
import { generateWorkflow } from '@/services/workflows';
import { SparklesIcon } from '@heroicons/react/24/solid';
import { toast } from 'sonner';

const CATEGORIES = [
    'Custom', 'Strategy', 'Marketing', 'Sales', 'Operations',
    'HR', 'Product', 'Support', 'Finance', 'Legal', 'Data'
];

export default function GenerateWorkflowPage() {
    const [description, setDescription] = useState('');
    const [category, setCategory] = useState('Custom');
    const [generating, setGenerating] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!description.trim()) {
            toast.error('Please describe the workflow you want to generate');
            return;
        }

        setGenerating(true);
        try {
            await generateWorkflow(description, category.toLowerCase());
            toast.success('Workflow generation initiated!');
            // Since it returns 501 currently or mock, we just notify.
        } catch (error: any) {
            // Check for the expected 501 / coming soon message logic from service
            if (error.message.includes('AI generation coming soon')) {
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

    return (
        <PremiumShell>
            <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8 text-center">
                    <div className="inline-flex items-center justify-center p-3 bg-purple-100 rounded-full mb-4">
                        <SparklesIcon className="h-8 w-8 text-purple-600" />
                    </div>
                    <h1 className="text-3xl font-bold text-slate-900">Generate with AI</h1>
                    <p className="mt-2 text-lg text-slate-500">
                        Describe your process, and our AI will design a custom workflow for you in seconds.
                    </p>
                </div>

                {/* Form */}
                <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-8">
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
                                        <SparklesIcon className="animate-spin h-5 w-5 mr-3" />
                                        Generating Magic...
                                    </>
                                ) : (
                                    <>
                                        <SparklesIcon className="h-5 w-5 mr-2" />
                                        Generate Workflow
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                </div>

                {/* Info Box */}
                <div className="mt-8 bg-blue-50 rounded-2xl p-6 border border-blue-100">
                    <h4 className="text-sm font-semibold text-blue-900 mb-2">How it works</h4>
                    <ul className="text-sm text-blue-700 space-y-2 list-disc pl-5">
                        <li>AI analyzes your description to understand the process.</li>
                        <li>It identifies key steps, roles, and necessary approvals.</li>
                        <li>A draft workflow is created which you can customize before activating.</li>
                    </ul>
                </div>
            </div>
        </PremiumShell>
    );
}
