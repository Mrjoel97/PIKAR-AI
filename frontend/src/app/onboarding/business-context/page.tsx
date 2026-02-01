'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { submitBusinessContext, BusinessContextInput } from '../../../services/onboarding';

const GOALS = ["Growth", "Efficiency", "Automation", "Cost Reduction", "Innovation", "Risk Management"];
const TEAM_SIZES = ["Just Me (Solopreneur)", "1-10 (Startup)", "11-50 (SME)", "51-200 (SME)", "200+ (Enterprise)"];

export default function BusinessContextPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<BusinessContextInput>({
        company_name: '',
        industry: '',
        description: '',
        website: '',
        goals: [],
        team_size: '',
        role: ''
    });

    const handleGoalToggle = (goal: string) => {
        setFormData(prev => ({
            ...prev,
            goals: prev.goals.includes(goal)
                ? prev.goals.filter(g => g !== goal)
                : [...prev.goals, goal]
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await submitBusinessContext(formData);
            router.push('/onboarding/preferences');
        } catch (error) {
            console.error('Failed to submit business context', error);
            // Ideally show toast error
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-2xl">
            <h1 className="text-3xl font-outfit font-bold text-slate-800 mb-2">Business Context</h1>
            <p className="text-slate-500 mb-8">Tell us about your organization so we can tailor the agents.</p>

            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="clay-card p-6 md:p-8 space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2">Company Name</label>
                            <input
                                type="text"
                                required
                                className="input-liquid w-full rounded-xl px-4 py-3 bg-white/50 border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                                placeholder="Acme Inc."
                                value={formData.company_name}
                                onChange={e => setFormData({ ...formData, company_name: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2">Website</label>
                            <input
                                type="url"
                                className="input-liquid w-full rounded-xl px-4 py-3 bg-white/50 border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                                placeholder="https://acme.com"
                                value={formData.website}
                                onChange={e => setFormData({ ...formData, website: e.target.value })}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">Industry</label>
                        <input
                            type="text"
                            required
                            className="input-liquid w-full rounded-xl px-4 py-3 bg-white/50 border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                            placeholder="e.g. Fintech, E-commerce, Healthcare"
                            value={formData.industry}
                            onChange={e => setFormData({ ...formData, industry: e.target.value })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">Role</label>
                        <input
                            type="text"
                            required
                            className="input-liquid w-full rounded-xl px-4 py-3 bg-white/50 border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                            placeholder="e.g. CEO, CTO, Marketing Manager"
                            value={formData.role || ''}
                            onChange={e => setFormData({ ...formData, role: e.target.value })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">Team Size</label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {TEAM_SIZES.map(size => (
                                <button
                                    key={size}
                                    type="button"
                                    className={`px-4 py-3 rounded-xl text-sm font-medium transition-all text-left border
                                        ${formData.team_size === size
                                            ? 'bg-teal-50 border-teal-500 text-teal-700 shadow-sm'
                                            : 'bg-white border-slate-200 text-slate-600 hover:border-teal-300'
                                        }
                                    `}
                                    onClick={() => setFormData({ ...formData, team_size: size })}
                                >
                                    {size}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">Business Description</label>
                        <textarea
                            required
                            className="input-liquid w-full rounded-xl px-4 py-3 bg-white/50 border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/50 min-h-[100px]"
                            placeholder=" Briefly describe what your company does..."
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-3">Primary Goals <span className="text-slate-400 font-normal">(Select all that apply)</span></label>
                        <div className="flex flex-wrap gap-3">
                            {GOALS.map(goal => (
                                <button
                                    key={goal}
                                    type="button"
                                    onClick={() => handleGoalToggle(goal)}
                                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all transform hover:scale-105
                                        ${formData.goals.includes(goal)
                                            ? 'bg-teal-600 text-white shadow-md'
                                            : 'bg-white text-slate-600 border border-slate-200 hover:border-teal-300'
                                        }
                                    `}
                                >
                                    {goal}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex justify-end pt-4">
                    <button
                        type="submit"
                        disabled={loading || !formData.company_name || !formData.industry || !formData.team_size}
                        className="clay-button-primary px-8 py-3 rounded-full text-white bg-teal-600 font-bold hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {loading ? 'Saving...' : 'Next Step'}
                        {!loading && <span className="material-symbols-outlined">arrow_forward</span>}
                    </button>
                </div>
            </form>
        </div>
    );
}
