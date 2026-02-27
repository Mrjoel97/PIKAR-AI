'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { createClient } from '@/lib/supabase/client';
import { fetchWithAuth } from '@/services/api';
import { usePersona } from '@/contexts/PersonaContext';
import {
    Search,
    Map,
    Rocket,
    ChevronRight,
    Users,
    Building2,
    Crown,
    Lightbulb,
} from 'lucide-react';

interface Journey {
    id: string;
    persona: string;
    title: string;
    description: string;
    stages: Array<{ name: string; status?: string }>;
    kpis: string[] | null;
    category?: string | null;
    primary_workflow_template_name?: string | null;
    outcomes_prompt?: string | null;
}

const PERSONA_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string; bgColor: string }> = {
    solopreneur: { label: 'Solopreneur', icon: <Users size={16} />, color: 'text-amber-700', bgColor: 'bg-amber-50 border-amber-200' },
    startup: { label: 'Startup', icon: <Rocket size={16} />, color: 'text-blue-700', bgColor: 'bg-blue-50 border-blue-200' },
    sme: { label: 'SME', icon: <Building2 size={16} />, color: 'text-purple-700', bgColor: 'bg-purple-50 border-purple-200' },
    enterprise: { label: 'Enterprise', icon: <Crown size={16} />, color: 'text-indigo-700', bgColor: 'bg-indigo-50 border-indigo-200' },
};

export default function UserJourneysPage() {
    const router = useRouter();
    const { persona } = usePersona();
    const [journeys, setJourneys] = useState<Journey[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedPersona, setSelectedPersona] = useState<string>(persona || 'all');
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [creating, setCreating] = useState<string | null>(null);
    const [outcomesModalJourney, setOutcomesModalJourney] = useState<Journey | null>(null);
    const [desiredOutcomesInput, setDesiredOutcomesInput] = useState('');
    const [timelineInput, setTimelineInput] = useState('');

    const breadcrumbItems = [
        { label: 'Home', href: '/dashboard' },
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'User Journeys' },
    ];

    useEffect(() => {
        fetchJourneys();
    }, [selectedPersona]);

    async function fetchJourneys() {
        setLoading(true);
        try {
            const supabase = createClient();
            let query = supabase.from('user_journeys').select('*');

            if (selectedPersona && selectedPersona !== 'all') {
                query = query.eq('persona', selectedPersona);
            }

            const { data, error } = await query.order('title');
            if (error) throw error;
            setJourneys(data || []);
        } catch (err) {
            console.error('Error fetching journeys:', err);
        } finally {
            setLoading(false);
        }
    }

    const createInitiativeFromJourney = useCallback(async (
        journey: Journey,
        options?: { desired_outcomes?: string; timeline?: string }
    ) => {
        setCreating(journey.id);
        try {
            const supabase = createClient();
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) {
                alert('Please sign in to create an initiative.');
                return;
            }

            // Prefer backend API (bypasses RLS issues, consistent auth)
            try {
                const res = await fetchWithAuth('/initiatives/from-journey', {
                    method: 'POST',
                    body: JSON.stringify({
                        journey_id: journey.id,
                        desired_outcomes: options?.desired_outcomes,
                        timeline: options?.timeline,
                    }),
                });
                const json = await res.json();
                const initiativeId = json?.initiative?.id;
                if (initiativeId) {
                    if (options?.desired_outcomes && options?.timeline && journey.primary_workflow_template_name) {
                        try {
                            await fetchWithAuth(`/initiatives/${initiativeId}/start-journey-workflow`, {
                                method: 'POST',
                            });
                        } catch (startErr) {
                            console.warn('Workflow auto-start failed after journey initiative creation:', startErr);
                        }
                    }
                    router.push(`/dashboard/initiatives/${initiativeId}`);
                    return;
                }
            } catch (apiErr) {
                // Fall through to direct Supabase insert
                console.warn('API create from journey failed, trying direct insert:', apiErr);
            }

            const payload = {
                title: journey.title,
                description: journey.description || `Initiative based on the "${journey.title}" user journey`,
                priority: 'medium',
                status: 'not_started',
                progress: 0,
                phase: 'ideation',
                phase_progress: { ideation: 0, validation: 0, prototype: 0, build: 0, scale: 0 },
                user_id: user.id,
                metadata: {
                    source: 'user_journey',
                    journey_id: journey.id,
                    journey_title: journey.title,
                    journey_stages: Array.isArray(journey.stages) ? journey.stages : [],
                    kpis: Array.isArray(journey.kpis) ? journey.kpis : [],
                    desired_outcomes: options?.desired_outcomes || null,
                    timeline: options?.timeline || null,
                },
            };

            const { data, error } = await supabase
                .from('initiatives')
                .insert(payload)
                .select()
                .single();

            if (error) {
                console.error('Supabase error creating initiative from journey:', error.message, error.details, error.code);
                alert(`Failed to create initiative: ${error.message || 'Please try again.'}`);
                return;
            }
            if (!data?.id) {
                alert('Failed to create initiative: no data returned.');
                return;
            }
            router.push(`/dashboard/initiatives/${data.id}`);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            console.error('Error creating initiative from journey:', message, err);
            alert(`Failed to create initiative: ${message || 'Please try again.'}`);
        } finally {
            setCreating(null);
        }
    }, [router]);

    const handleStartAsInitiative = useCallback(async (journey: Journey) => {
        if (journey.outcomes_prompt) {
            setOutcomesModalJourney(journey);
            setDesiredOutcomesInput('');
            setTimelineInput('');
            return;
        }
        await createInitiativeFromJourney(journey);
    }, [createInitiativeFromJourney]);

    const allCategories = Array.from(new Set(
        journeys
            .map((j) => (typeof j.category === 'string' ? j.category.trim() : ''))
            .filter(Boolean)
    )).sort((a, b) => a.localeCompare(b));

    const filteredJourneys = journeys.filter((j) => {
        if (searchQuery && !j.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        if (selectedCategory !== 'all' && (j.category || '').toLowerCase() !== selectedCategory.toLowerCase()) return false;
        return true;
    });

    // Group journeys by persona for "all" view
    const groupedByPersona = filteredJourneys.reduce<Record<string, Journey[]>>((acc, j) => {
        if (!acc[j.persona]) acc[j.persona] = [];
        acc[j.persona].push(j);
        return acc;
    }, {});

    return (
        <PremiumShell>
            <div className="mb-6">
                <Breadcrumb items={breadcrumbItems} />
            </div>

            <div className="space-y-6 max-w-6xl mx-auto">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-outfit font-bold text-slate-900">User Journeys</h1>
                    <p className="text-slate-500 mt-1">
                        Browse curated journeys for your business stage. Start any journey as an initiative.
                    </p>
                </div>

                {/* Persona Tabs + Search */}
                <div className="flex flex-col sm:flex-row gap-4">
                    <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1 overflow-x-auto">
                        <button
                            onClick={() => setSelectedPersona('all')}
                            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                                selectedPersona === 'all' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            All ({journeys.length || '...'})
                        </button>
                        {Object.entries(PERSONA_CONFIG).map(([key, cfg]) => (
                            <button
                                key={key}
                                onClick={() => setSelectedPersona(key)}
                                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                                    selectedPersona === key ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                                }`}
                            >
                                {cfg.icon}
                                {cfg.label}
                            </button>
                        ))}
                    </div>
                    <div className="relative flex-1">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search journeys..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                        />
                    </div>
                </div>

                <div className="flex items-center gap-2 overflow-x-auto">
                    <button
                        onClick={() => setSelectedCategory('all')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap border ${selectedCategory === 'all'
                            ? 'bg-teal-50 text-teal-700 border-teal-200'
                            : 'bg-white text-slate-500 border-slate-200 hover:text-slate-700'
                            }`}
                    >
                        All Categories
                    </button>
                    {allCategories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setSelectedCategory(cat)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap border capitalize ${selectedCategory === cat
                                ? 'bg-teal-50 text-teal-700 border-teal-200'
                                : 'bg-white text-slate-500 border-slate-200 hover:text-slate-700'
                                }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>

                {/* Journey Count */}
                <p className="text-sm text-slate-400">
                    {filteredJourneys.length} journey{filteredJourneys.length !== 1 ? 's' : ''} found
                    {selectedPersona !== 'all' && ` for ${PERSONA_CONFIG[selectedPersona]?.label || selectedPersona}`}
                </p>

                {/* Loading */}
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-8 w-8 border-2 border-teal-500 border-t-transparent" />
                    </div>
                ) : filteredJourneys.length === 0 ? (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white p-12 rounded-3xl border border-slate-100 shadow-sm flex flex-col items-center justify-center text-center"
                    >
                        <Map size={48} className="text-slate-300 mb-4" />
                        <h3 className="text-lg font-semibold text-slate-700 mb-2">No journeys found</h3>
                        <p className="text-slate-400">
                            {searchQuery ? 'Try adjusting your search query.' : 'No journeys available for this persona.'}
                        </p>
                    </motion.div>
                ) : selectedPersona === 'all' ? (
                    // Grouped view
                    <div className="space-y-8">
                        {Object.entries(groupedByPersona).map(([personaKey, personaJourneys]) => {
                            const cfg = PERSONA_CONFIG[personaKey];
                            return (
                                <div key={personaKey}>
                                    <div className="flex items-center gap-2 mb-4">
                                        <div className={`${cfg?.color || 'text-slate-600'}`}>{cfg?.icon}</div>
                                        <h2 className="text-lg font-semibold text-slate-800">{cfg?.label || personaKey}</h2>
                                        <span className="text-sm text-slate-400">({personaJourneys.length})</span>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {personaJourneys.map((journey, idx) => (
                                            <JourneyCard
                                                key={journey.id}
                                                journey={journey}
                                                index={idx}
                                                creating={creating === journey.id}
                                                onStartAsInitiative={() => handleStartAsInitiative(journey)}
                                            />
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    // Flat grid view
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <AnimatePresence>
                            {filteredJourneys.map((journey, idx) => (
                                <JourneyCard
                                    key={journey.id}
                                    journey={journey}
                                    index={idx}
                                    creating={creating === journey.id}
                                    onStartAsInitiative={() => handleStartAsInitiative(journey)}
                                />
                            ))}
                        </AnimatePresence>
                    </div>
                )}
            </div>

            <AnimatePresence>
                {outcomesModalJourney && (
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
                            className="w-full max-w-xl bg-white rounded-2xl border border-slate-200 shadow-xl p-6"
                        >
                            <h3 className="text-lg font-semibold text-slate-900">Define Outcomes Before Starting</h3>
                            <p className="text-sm text-slate-500 mt-1">{outcomesModalJourney.outcomes_prompt}</p>

                            <label className="block text-sm font-medium text-slate-700 mt-4 mb-1">Desired outcomes</label>
                            <textarea
                                value={desiredOutcomesInput}
                                onChange={(e) => setDesiredOutcomesInput(e.target.value)}
                                placeholder="What should this journey achieve?"
                                rows={4}
                                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                            />

                            <label className="block text-sm font-medium text-slate-700 mt-4 mb-1">Timeline</label>
                            <input
                                type="text"
                                value={timelineInput}
                                onChange={(e) => setTimelineInput(e.target.value)}
                                placeholder="e.g. 90 days, Q2 2026, by end of month"
                                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                            />

                            <div className="flex items-center justify-end gap-2 mt-6">
                                <button
                                    onClick={() => setOutcomesModalJourney(null)}
                                    className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 text-sm hover:bg-slate-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={async () => {
                                        if (!outcomesModalJourney) return;
                                        if (!desiredOutcomesInput.trim() || !timelineInput.trim()) {
                                            alert('Please provide both desired outcomes and a timeline.');
                                            return;
                                        }
                                        const selectedJourney = outcomesModalJourney;
                                        setOutcomesModalJourney(null);
                                        await createInitiativeFromJourney(selectedJourney, {
                                            desired_outcomes: desiredOutcomesInput.trim(),
                                            timeline: timelineInput.trim(),
                                        });
                                    }}
                                    className="px-4 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium hover:bg-teal-700"
                                >
                                    Start Journey
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </PremiumShell>
    );
}

// Journey Card component
function JourneyCard({
    journey,
    index,
    creating,
    onStartAsInitiative,
}: {
    journey: Journey;
    index: number;
    creating: boolean;
    onStartAsInitiative: () => void;
}) {
    const stages = journey.stages || [];

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.03 }}
            className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm hover:shadow-md hover:border-slate-200 transition-all"
        >
            <div className="flex items-start gap-3 mb-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-50 to-emerald-50 border border-teal-100 flex items-center justify-center shrink-0">
                    <Lightbulb size={16} className="text-teal-600" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-semibold text-slate-800 line-clamp-1">{journey.title}</h3>
                        {journey.category && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 capitalize">{journey.category}</span>
                        )}
                        {journey.primary_workflow_template_name && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                                Linked Workflow
                            </span>
                        )}
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-0.5">{journey.description || 'No description'}</p>
                    {Array.isArray(journey.kpis) && journey.kpis.length > 0 && (
                        <div className="mt-1.5 flex items-center gap-1 flex-wrap">
                            {journey.kpis.slice(0, 3).map((kpi) => (
                                <span key={kpi} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100">
                                    KPI: {kpi}
                                </span>
                            ))}
                        </div>
                    )}
                    {journey.outcomes_prompt && (
                        <p className="text-[11px] text-teal-600/90 mt-1.5 line-clamp-2 bg-teal-50/80 rounded-lg px-2 py-1 border border-teal-100/80">
                            <span className="font-medium text-teal-700">The agent will ask:</span> {journey.outcomes_prompt}
                        </p>
                    )}
                </div>
            </div>

            {/* Stages indicator */}
            {stages.length > 0 && (
                <div className="flex items-center gap-1 mb-3">
                    {stages.map((stage, i) => (
                        <React.Fragment key={i}>
                            <span className="text-[10px] text-slate-400 font-medium truncate max-w-[60px]">{stage.name}</span>
                            {i < stages.length - 1 && <ChevronRight size={10} className="text-slate-300 shrink-0" />}
                        </React.Fragment>
                    ))}
                </div>
            )}

            {/* Action */}
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    onStartAsInitiative();
                }}
                disabled={creating}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-teal-50 text-teal-700 rounded-xl text-xs font-semibold hover:bg-teal-100 transition-colors disabled:opacity-50 border border-teal-100"
            >
                {creating ? (
                    <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-teal-500 border-t-transparent" />
                ) : (
                    <>
                        <Rocket size={13} />
                        Start as Initiative
                    </>
                )}
            </button>
        </motion.div>
    );
}
