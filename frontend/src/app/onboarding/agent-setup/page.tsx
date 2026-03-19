'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
    submitAgentSetup, 
    AgentSetupInput,
    getOnboardingStatus,
    PERSONA_INFO,
    PersonaType,
    determinePersonaPreview
} from '@/services/onboarding';

const AGENT_NAME_SUGGESTIONS = [
    'Atlas',
    'Nova', 
    'Sage',
    'Aria',
    'Max',
    'Echo',
    'Iris',
    'Kai',
];

const FOCUS_AREAS = [
    { id: 'strategy', label: 'Strategic Planning', icon: '🎯', description: 'OKRs, roadmaps, initiatives' },
    { id: 'finance', label: 'Financial Analysis', icon: '📊', description: 'Revenue, costs, forecasting' },
    { id: 'marketing', label: 'Marketing & Sales', icon: '📈', description: 'Campaigns, leads, growth' },
    { id: 'operations', label: 'Operations', icon: '⚙️', description: 'Processes, efficiency, logistics' },
    { id: 'content', label: 'Content Creation', icon: '✍️', description: 'Blogs, emails, social media' },
    { id: 'hr', label: 'HR & Recruitment', icon: '👥', description: 'Hiring, team, culture' },
];

export default function AgentSetupPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [persona, setPersona] = useState<PersonaType>('startup');
    
    const [formData, setFormData] = useState<AgentSetupInput>({
        agent_name: '',
        focus_areas: []
    });

    useEffect(() => {
        // Fetch status to get persona preview
        const fetchStatus = async () => {
            try {
                const status = await getOnboardingStatus();
                if (status.persona) {
                    setPersona(status.persona as PersonaType);
                }
            } catch (err) {
                console.error('Failed to fetch status', err);
            }
        };
        fetchStatus();
    }, []);

    const handleFocusToggle = (areaId: string) => {
        setFormData(prev => ({
            ...prev,
            focus_areas: prev.focus_areas?.includes(areaId)
                ? prev.focus_areas.filter(a => a !== areaId)
                : [...(prev.focus_areas || []), areaId]
        }));
    };

    const handleNameSuggestion = (name: string) => {
        setFormData({ ...formData, agent_name: name });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);
        
        try {
            await submitAgentSetup({
                agent_name: formData.agent_name || 'Executive Agent',
                focus_areas: formData.focus_areas
            });
            router.push('/onboarding/processing');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to save. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        router.push('/onboarding/preferences');
    };

    const currentPersona = PERSONA_INFO[persona];

    return (
        <div className="w-full">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl lg:text-4xl font-outfit font-bold text-slate-800 mb-3">
                    Meet Your Executive Agent
                </h1>
                <p className="text-lg text-slate-500">
                    Customize your AI-powered chief of staff.
                </p>
            </div>

            {error && (
                <motion.div 
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm"
                >
                    {error}
                </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-8">
                {/* Agent Persona Card */}
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`bg-gradient-to-br ${currentPersona.color} rounded-2xl shadow-xl p-8 text-white relative overflow-hidden`}
                >
                    {/* Decorative circles */}
                    <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2"></div>
                    <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/10 rounded-full translate-y-1/2 -translate-x-1/2"></div>
                    
                    <div className="relative z-10">
                        <div className="flex items-center gap-4 mb-4">
                            <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center text-4xl shadow-lg">
                                {currentPersona.icon}
                            </div>
                            <div>
                                <div className="text-sm font-medium text-white/80">Your AI Persona</div>
                                <div className="text-2xl font-bold">{currentPersona.title}</div>
                            </div>
                        </div>
                        <p className="text-white/90 text-sm leading-relaxed">
                            {currentPersona.description}
                        </p>
                    </div>
                </motion.div>

                {/* Agent Name Card */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2">
                        <span className="text-xl">🤖</span> Name Your Agent
                    </h2>
                    <p className="text-sm text-slate-500 mb-6">Give your executive assistant a personal touch</p>
                    
                    <div className="space-y-4">
                        <input
                            type="text"
                            className="w-full rounded-xl px-5 py-4 bg-slate-50 border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-all text-lg font-medium"
                            placeholder="e.g. Atlas, Nova, or your own name"
                            value={formData.agent_name}
                            onChange={e => setFormData({ ...formData, agent_name: e.target.value })}
                        />
                        
                        <div>
                            <div className="text-xs text-slate-500 mb-2">Quick suggestions:</div>
                            <div className="flex flex-wrap gap-2">
                                {AGENT_NAME_SUGGESTIONS.map(name => (
                                    <motion.button
                                        key={name}
                                        type="button"
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        onClick={() => handleNameSuggestion(name)}
                                        className={`
                                            px-4 py-2 rounded-full text-sm font-medium transition-all
                                            ${formData.agent_name === name
                                                ? 'bg-teal-600 text-white shadow-md shadow-teal-500/30'
                                                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                            }
                                        `}
                                    >
                                        {name}
                                    </motion.button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Focus Areas Card */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2">
                        <span className="text-xl">🎯</span> Primary Focus Areas
                    </h2>
                    <p className="text-sm text-slate-500 mb-6">Select the areas where you need the most help (optional)</p>
                    
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                        {FOCUS_AREAS.map(area => (
                            <motion.button
                                key={area.id}
                                type="button"
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => handleFocusToggle(area.id)}
                                className={`
                                    p-4 rounded-xl text-left border-2 transition-all
                                    ${formData.focus_areas?.includes(area.id)
                                        ? 'bg-teal-50 border-teal-500 shadow-md shadow-teal-500/20'
                                        : 'bg-white border-slate-200 hover:border-teal-300'
                                    }
                                `}
                            >
                                <div className="text-2xl mb-2">{area.icon}</div>
                                <div className={`font-bold text-sm mb-1 ${formData.focus_areas?.includes(area.id) ? 'text-teal-700' : 'text-slate-700'}`}>
                                    {area.label}
                                </div>
                                <div className="text-xs text-slate-500">{area.description}</div>
                            </motion.button>
                        ))}
                    </div>
                </div>

                {/* Capabilities Preview */}
                <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl shadow-xl p-6 lg:p-8 text-white">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center shadow-lg">
                            <span className="text-2xl">⚡</span>
                        </div>
                        <div>
                            <div className="font-bold text-lg">
                                {formData.agent_name || "Your Agent's Capabilities"}
                            </div>
                            <div className="text-sm text-slate-400">Powered by 10+ specialized AI agents</div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {[
                            { icon: '📊', label: 'Financial Analysis' },
                            { icon: '📈', label: 'Sales Intelligence' },
                            { icon: '✍️', label: 'Content Creation' },
                            { icon: '📧', label: 'Marketing Automation' },
                            { icon: '⚙️', label: 'Operations' },
                            { icon: '🛡️', label: 'Compliance & Risk' },
                        ].map(cap => (
                            <div key={cap.label} className="bg-white/5 rounded-lg p-3 flex items-center gap-2">
                                <span className="text-lg">{cap.icon}</span>
                                <span className="text-xs font-medium text-slate-300">{cap.label}</span>
                            </div>
                        ))}
                    </div>

                    <div className="mt-6 p-4 bg-white/5 rounded-xl border border-white/10">
                        <div className="text-sm text-slate-300 italic">
                            &quot;{formData.agent_name || 'Your Agent'} will coordinate all these specialists to help you achieve your business goals with {currentPersona.id === 'enterprise' ? 'strategic precision' : currentPersona.id === 'solopreneur' ? 'maximum efficiency' : currentPersona.id === 'sme' ? 'reliable optimization' : 'growth-focused insights'}.&quot;
                        </div>
                    </div>
                </div>

                {/* Navigation Buttons */}
                <div className="flex justify-between pt-4">
                    <motion.button
                        type="button"
                        onClick={handleBack}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="px-4 sm:px-6 py-3 sm:py-4 rounded-xl text-slate-600 bg-white border border-slate-200 font-semibold hover:bg-slate-50 flex items-center gap-2 transition-all"
                    >
                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="19" y1="12" x2="5" y2="12"></line>
                            <polyline points="12 19 5 12 12 5"></polyline>
                        </svg>
                        Back
                    </motion.button>

                    <motion.button
                        type="submit"
                        disabled={loading}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="px-5 sm:px-8 py-3 sm:py-4 rounded-xl text-white bg-gradient-to-r from-teal-600 to-cyan-600 font-bold text-base sm:text-lg shadow-lg shadow-teal-500/30 hover:shadow-xl hover:shadow-teal-500/40 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 sm:gap-3 transition-all"
                    >
                        {loading ? (
                            <>
                                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Activating...
                            </>
                        ) : (
                            <>
                                Activate {formData.agent_name || 'Agent'}
                                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                                </svg>
                            </>
                        )}
                    </motion.button>
                </div>
            </form>
        </div>
    );
}
