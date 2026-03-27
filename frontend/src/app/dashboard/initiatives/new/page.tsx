'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { createClient } from '@/lib/supabase/client';
import { usePersona } from '@/contexts/PersonaContext';
import {
    PlusCircle,
    ArrowLeft,
    Sparkles,
    Lightbulb,
    Target,
    FlaskConical,
    Hammer,
    Rocket,
    ChevronRight,
} from 'lucide-react';

interface Template {
    id: string;
    title: string;
    description: string;
    persona: string;
    category: string;
    icon: string;
    priority: string;
    phases: Array<{ name: string; steps: string[] }>;
    kpis: string[];
}

const PHASE_ICONS = [
    { name: 'Ideation & Empathy', icon: <Lightbulb size={16} className="text-amber-500" /> },
    { name: 'Validation & Research', icon: <Target size={16} className="text-blue-500" /> },
    { name: 'Prototype & Test', icon: <FlaskConical size={16} className="text-purple-500" /> },
    { name: 'Build Product/Service', icon: <Hammer size={16} className="text-indigo-500" /> },
    { name: 'Scale Business', icon: <Rocket size={16} className="text-emerald-500" /> },
];

export default function NewInitiativePage() {
    const router = useRouter();
    const { persona } = usePersona();
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
    const [showBlankForm, setShowBlankForm] = useState(false);
    const [creating, setCreating] = useState(false);

    // Blank form state
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState('medium');

    const breadcrumbItems = [
        { label: 'Home', href: '/dashboard' },
        { label: 'Initiatives', href: '/dashboard/initiatives' },
        { label: 'New' },
    ];

    useEffect(() => {
        fetchTemplates();
    }, [persona]);

    async function fetchTemplates() {
        try {
            const supabase = createClient();
            let query = supabase.from('initiative_templates').select('*');

            if (persona) {
                query = query.eq('persona', persona);
            }

            const { data, error } = await query.order('title');
            if (error) {
                const msg =
                    (error as { message?: string }).message ??
                    (error as { error_description?: string }).error_description ??
                    String(error?.code ?? 'Unknown error');
                console.warn('Initiative templates fetch failed (table may not be migrated yet):', msg);
                setTemplates([]);
                return;
            }
            setTemplates(data ?? []);
        } catch (err: unknown) {
            const msg =
                err instanceof Error
                    ? err.message
                    : typeof err === 'object' && err !== null && 'message' in err
                    ? String((err as { message: unknown }).message)
                    : 'Failed to load templates';
            console.warn('Error fetching initiative templates:', msg);
            setTemplates([]);
        } finally {
            setLoading(false);
        }
    }

    const handleCreateFromTemplate = useCallback(async (template: Template) => {
        setCreating(true);
        try {
            const supabase = createClient();
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error('Not authenticated');

            const { data, error } = await supabase
                .from('initiatives')
                .insert({
                    title: template.title,
                    description: template.description,
                    priority: template.priority,
                    status: 'not_started',
                    progress: 0,
                    phase: 'ideation',
                    phase_progress: { ideation: 0, validation: 0, prototype: 0, build: 0, scale: 0 },
                    template_id: template.id,
                    user_id: user.id,
                    metadata: {
                        template_title: template.title,
                        phases: template.phases,
                        kpis: template.kpis,
                    },
                })
                .select()
                .single();

            if (error) throw error;
            router.push(`/dashboard/initiatives/${data.id}`);
        } catch (err) {
            console.error('Error creating initiative:', err);
            alert('Failed to create initiative. Please try again.');
        } finally {
            setCreating(false);
        }
    }, [router]);

    const handleCreateBlank = useCallback(async () => {
        if (!title.trim()) return;
        setCreating(true);
        try {
            const supabase = createClient();
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error('Not authenticated');

            const { data, error } = await supabase
                .from('initiatives')
                .insert({
                    title: title.trim(),
                    description: description.trim(),
                    priority,
                    status: 'not_started',
                    progress: 0,
                    phase: 'ideation',
                    phase_progress: { ideation: 0, validation: 0, prototype: 0, build: 0, scale: 0 },
                    user_id: user.id,
                    metadata: {},
                })
                .select()
                .single();

            if (error) throw error;
            router.push(`/dashboard/initiatives/${data.id}`);
        } catch (err) {
            console.error('Error creating initiative:', err);
            alert('Failed to create initiative. Please try again.');
        } finally {
            setCreating(false);
        }
    }, [title, description, priority, router]);

    // Template detail view
    if (selectedTemplate) {
        return (
            <PremiumShell>
                <div className="mb-6">
                    <Breadcrumb items={[...breadcrumbItems.slice(0, -1), { label: selectedTemplate.title }]} />
                </div>
                <div className="max-w-4xl mx-auto space-y-6">
                    <button
                        onClick={() => setSelectedTemplate(null)}
                        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
                    >
                        <ArrowLeft size={16} /> Back to templates
                    </button>

                    <div className="bg-white rounded-[28px] border border-slate-100/80 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden">
                        <div className="p-8 border-b border-slate-100">
                            <div className="flex items-start gap-4">
                                <span className="text-4xl">{selectedTemplate.icon}</span>
                                <div className="flex-1">
                                    <h1 className="text-2xl font-outfit font-bold text-slate-900">{selectedTemplate.title}</h1>
                                    <p className="text-slate-500 mt-1">{selectedTemplate.description}</p>
                                    <div className="flex items-center gap-2 mt-3">
                                        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 capitalize">{selectedTemplate.persona}</span>
                                        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 capitalize">{selectedTemplate.category}</span>
                                        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 capitalize">{selectedTemplate.priority} priority</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Phases */}
                        <div className="p-8 space-y-6">
                            <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">5-Phase Framework</h2>
                            <div className="space-y-4">
                                {selectedTemplate.phases.map((phase, idx) => (
                                    <div key={phase.name} className="relative pl-8">
                                        <div className="absolute left-0 top-0.5">
                                            {PHASE_ICONS[idx]?.icon || <div className="w-4 h-4 rounded-full bg-slate-300" />}
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-700 capitalize mb-2">
                                                Phase {idx + 1}: {phase.name}
                                            </h3>
                                            <ul className="space-y-1">
                                                {phase.steps.map((step, si) => (
                                                    <li key={si} className="flex items-start gap-2 text-sm text-slate-500">
                                                        <ChevronRight size={14} className="mt-0.5 shrink-0 text-slate-300" />
                                                        {step}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* KPIs */}
                        {selectedTemplate.kpis && selectedTemplate.kpis.length > 0 && (
                            <div className="px-8 pb-8">
                                <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-3">Key Performance Indicators</h2>
                                <div className="flex flex-wrap gap-2">
                                    {selectedTemplate.kpis.map((kpi, i) => (
                                        <span key={i} className="px-3 py-1.5 rounded-full text-xs font-medium bg-teal-50 text-teal-700 border border-teal-100">
                                            {kpi}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Action */}
                        <div className="p-8 bg-slate-50 border-t border-slate-100">
                            <button
                                onClick={() => handleCreateFromTemplate(selectedTemplate)}
                                disabled={creating}
                                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-teal-900 text-white rounded-xl font-semibold hover:bg-teal-800 transition-colors disabled:opacity-50"
                            >
                                {creating ? (
                                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                                ) : (
                                    <>
                                        <Rocket size={18} />
                                        Start This Initiative
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </PremiumShell>
        );
    }

    // Blank form view
    if (showBlankForm) {
        return (
            <PremiumShell>
                <div className="mb-6">
                    <Breadcrumb items={breadcrumbItems} />
                </div>
                <div className="max-w-2xl mx-auto space-y-6">
                    <button
                        onClick={() => setShowBlankForm(false)}
                        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
                    >
                        <ArrowLeft size={16} /> Back to templates
                    </button>

                    <div className="bg-white rounded-[28px] border border-slate-100/80 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] p-8">
                        <h1 className="text-2xl font-outfit font-bold text-slate-900 mb-6">Create Blank Initiative</h1>

                        <div className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1.5">Title *</label>
                                <input
                                    type="text"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="e.g., Launch Mobile App"
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1.5">Description</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Describe the goals and scope of this initiative..."
                                    rows={4}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400 resize-none"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1.5">Priority</label>
                                <select
                                    value={priority}
                                    onChange={(e) => setPriority(e.target.value)}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                                >
                                    <option value="low">Low</option>
                                    <option value="medium">Medium</option>
                                    <option value="high">High</option>
                                    <option value="critical">Critical</option>
                                </select>
                            </div>

                            {/* Phase Preview */}
                            <div className="pt-4 border-t border-slate-100">
                                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Initiative Framework</p>
                                <div className="flex items-center gap-1">
                                    {PHASE_ICONS.map((p, i) => (
                                        <React.Fragment key={p.name}>
                                            <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-50 text-xs font-medium text-slate-600">
                                                {p.icon}
                                                <span className="hidden sm:inline">{p.name.split(' ')[0]}</span>
                                            </div>
                                            {i < PHASE_ICONS.length - 1 && <ChevronRight size={14} className="text-slate-300" />}
                                        </React.Fragment>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={handleCreateBlank}
                                disabled={!title.trim() || creating}
                                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-teal-900 text-white rounded-xl font-semibold hover:bg-teal-800 transition-colors disabled:opacity-50 mt-4"
                            >
                                {creating ? (
                                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                                ) : (
                                    <>
                                        <PlusCircle size={18} />
                                        Create Initiative
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </PremiumShell>
        );
    }

    // Template picker (default view)
    return (
        <PremiumShell>
            <div className="mb-6">
                <Breadcrumb items={breadcrumbItems} />
            </div>

            <motion.div
                className="space-y-6 max-w-6xl mx-auto"
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                {/* Gradient Icon Header */}
                <div className="flex items-center gap-4 mb-6">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg shadow-amber-200">
                        <Lightbulb className="h-6 w-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">New Initiative</h1>
                        <p className="mt-0.5 text-sm text-slate-500">Choose a template or start from scratch</p>
                    </div>
                </div>

                {/* Blank Initiative Card */}
                <motion.button
                    onClick={() => setShowBlankForm(true)}
                    whileHover={{ y: -2, boxShadow: '0 8px 30px -10px rgba(0,0,0,0.1)' }}
                    className="w-full bg-white rounded-[28px] p-6 border-2 border-dashed border-slate-200 hover:border-teal-400 transition-colors text-left flex items-center gap-4"
                >
                    <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
                        <Sparkles size={24} className="text-slate-400" />
                    </div>
                    <div>
                        <h3 className="text-base font-semibold text-slate-700">Blank Initiative</h3>
                        <p className="text-sm text-slate-400">Start from scratch with the 5-phase framework</p>
                    </div>
                    <ArrowLeft size={18} className="ml-auto text-slate-300 rotate-180" />
                </motion.button>

                {/* Templates Grid */}
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-2 border-teal-500 border-t-transparent" />
                    </div>
                ) : templates.length > 0 ? (
                    <>
                        <div>
                            <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400 mb-1">
                                Templates for {persona ? persona.charAt(0).toUpperCase() + persona.slice(1) : 'You'}
                            </h2>
                            <p className="text-sm text-slate-400">Pre-configured initiatives with suggested workflows and KPIs</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <AnimatePresence>
                                {templates.map((t, idx) => (
                                    <motion.button
                                        key={t.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.04 }}
                                        whileHover={{ y: -3, boxShadow: '0 12px 30px -10px rgba(0,0,0,0.1)' }}
                                        onClick={() => setSelectedTemplate(t)}
                                        className="bg-white rounded-[28px] p-5 border border-slate-100/80 shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] text-left hover:shadow-[0_12px_40px_-15px_rgba(15,23,42,0.3)] transition-all"
                                    >
                                        <div className="flex items-start gap-3 mb-3">
                                            <span className="text-2xl">{t.icon}</span>
                                            <div className="flex-1 min-w-0">
                                                <h3 className="text-sm font-semibold text-slate-800 truncate">{t.title}</h3>
                                                <p className="text-xs text-slate-400 line-clamp-2 mt-0.5">{t.description}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-500 capitalize">{t.category}</span>
                                            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-50 text-blue-600 capitalize">{t.priority}</span>
                                            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-teal-50 text-teal-600">{t.phases?.length || 5} phases</span>
                                        </div>
                                    </motion.button>
                                ))}
                            </AnimatePresence>
                        </div>
                    </>
                ) : (
                    <div className="text-center py-8 text-slate-400">
                        No templates available for your persona. Start with a blank initiative above.
                    </div>
                )}
            </motion.div>
        </PremiumShell>
    );
}
