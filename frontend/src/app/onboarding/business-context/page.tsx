'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    submitBusinessContext,
    BusinessContextInput,
    GOALS_OPTIONS,
    TEAM_SIZES,
    INDUSTRIES,
    determinePersonaPreview,
    PERSONA_INFO,
    PersonaType
} from '@/services/onboarding';

export default function BusinessContextPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [personaPreview, setPersonaPreview] = useState<PersonaType>('startup');
    const [showIndustryDropdown, setShowIndustryDropdown] = useState(false);

    const [formData, setFormData] = useState<BusinessContextInput>({
        company_name: '',
        industry: '',
        description: '',
        website: '',
        goals: [],
        team_size: '',
        role: ''
    });

    // Update persona preview when relevant fields change
    useEffect(() => {
        const persona = determinePersonaPreview(formData);
        setPersonaPreview(persona);
    }, [formData.team_size, formData.role, formData.industry]);

    const handleGoalToggle = (goalId: string) => {
        setFormData(prev => ({
            ...prev,
            goals: prev.goals.includes(goalId)
                ? prev.goals.filter(g => g !== goalId)
                : [...prev.goals, goalId]
        }));
    };

    const handleIndustrySelect = (industry: string) => {
        setFormData({ ...formData, industry });
        setShowIndustryDropdown(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await submitBusinessContext(formData);
            router.push('/onboarding/preferences');
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to save';
            if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
                setError('Unable to connect to the server. Please check that the backend is running and try again.');
            } else if (message.includes('401') || message.includes('Not authenticated')) {
                setError('Your session has expired. Please log in again.');
                setTimeout(() => router.push('/auth/login'), 2000);
            } else {
                setError(message);
            }
        } finally {
            setLoading(false);
        }
    };

    const isFormValid = formData.company_name && formData.industry && formData.team_size && formData.goals.length > 0;
    const currentPersona = PERSONA_INFO[personaPreview];

    return (
        <div className="w-full">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl lg:text-4xl font-outfit font-bold text-slate-800 mb-3">
                    Tell us about your business
                </h1>
                <p className="text-lg text-slate-500">
                    This helps us customize your AI assistant to understand your context and goals.
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
                {/* Company Info Card */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                        <span className="text-xl">🏢</span> Company Information
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Company Name */}
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2">
                                Company Name <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                required
                                className="w-full rounded-xl px-4 py-3 bg-slate-50 border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-all"
                                placeholder="Acme Inc."
                                value={formData.company_name}
                                onChange={e => setFormData({ ...formData, company_name: e.target.value })}
                            />
                        </div>

                        {/* Website */}
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2">
                                Website <span className="text-slate-400 font-normal">(optional)</span>
                            </label>
                            <input
                                type="url"
                                className="w-full rounded-xl px-4 py-3 bg-slate-50 border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-all"
                                placeholder="https://acme.com"
                                value={formData.website}
                                onChange={e => setFormData({ ...formData, website: e.target.value })}
                            />
                        </div>

                        {/* Industry */}
                        <div className="relative">
                            <label className="block text-sm font-semibold text-slate-700 mb-2">
                                Industry <span className="text-red-500">*</span>
                            </label>
                            <div
                                className="w-full rounded-xl px-4 py-3 bg-slate-50 border border-slate-200 cursor-pointer flex items-center justify-between hover:border-teal-300 transition-all"
                                onClick={() => setShowIndustryDropdown(!showIndustryDropdown)}
                            >
                                <span className={formData.industry ? 'text-slate-800' : 'text-slate-400'}>
                                    {formData.industry || 'Select your industry'}
                                </span>
                                <svg className={`w-5 h-5 text-slate-400 transition-transform ${showIndustryDropdown ? 'rotate-180' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <polyline points="6 9 12 15 18 9"></polyline>
                                </svg>
                            </div>

                            {showIndustryDropdown && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="absolute z-50 w-full mt-2 bg-white rounded-xl shadow-xl border border-slate-200 max-h-60 overflow-y-auto"
                                >
                                    {INDUSTRIES.map(industry => (
                                        <div
                                            key={industry}
                                            className={`px-4 py-3 cursor-pointer hover:bg-teal-50 transition-colors ${formData.industry === industry ? 'bg-teal-50 text-teal-700' : 'text-slate-700'}`}
                                            onClick={() => handleIndustrySelect(industry)}
                                        >
                                            {industry}
                                        </div>
                                    ))}
                                </motion.div>
                            )}
                        </div>

                        {/* Role */}
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2">
                                Your Role <span className="text-slate-400 font-normal">(optional)</span>
                            </label>
                            <input
                                type="text"
                                className="w-full rounded-xl px-4 py-3 bg-slate-50 border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-all"
                                placeholder="e.g. CEO, Founder, Marketing Director"
                                value={formData.role || ''}
                                onChange={e => setFormData({ ...formData, role: e.target.value })}
                            />
                        </div>
                    </div>

                    {/* Description */}
                    <div className="mt-6">
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Business Description <span className="text-slate-400 font-normal">(optional)</span>
                        </label>
                        <textarea
                            className="w-full rounded-xl px-4 py-3 bg-slate-50 border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-all min-h-[100px] resize-none"
                            placeholder="Briefly describe what your company does, your products/services, and target market..."
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                        />
                    </div>
                </div>

                {/* Team Size Card */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                        <span className="text-xl">👥</span> Team Size <span className="text-red-500">*</span>
                    </h2>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {TEAM_SIZES.map(size => (
                            <motion.button
                                key={size.id}
                                type="button"
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                className={`
                                    p-4 rounded-xl text-left border-2 transition-all
                                    ${formData.team_size === size.id
                                        ? 'bg-teal-50 border-teal-500 shadow-md shadow-teal-500/20'
                                        : 'bg-white border-slate-200 hover:border-teal-300'
                                    }
                                `}
                                onClick={() => setFormData({ ...formData, team_size: size.id })}
                            >
                                <div className={`font-bold text-sm ${formData.team_size === size.id ? 'text-teal-700' : 'text-slate-700'}`}>
                                    {size.label}
                                </div>
                                <div className="text-xs text-slate-500 mt-1">{size.description}</div>
                            </motion.button>
                        ))}
                    </div>

                    {/* Persona Preview */}
                    {formData.team_size && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`mt-6 p-4 rounded-xl bg-gradient-to-r ${currentPersona.color} text-white`}
                        >
                            <div className="flex items-center gap-3">
                                <span className="text-3xl">{currentPersona.icon}</span>
                                <div>
                                    <div className="text-sm font-medium opacity-90">Your AI will be optimized for:</div>
                                    <div className="font-bold text-lg">{currentPersona.title}</div>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </div>

                {/* Goals Card */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2">
                        <span className="text-xl">🎯</span> Primary Goals <span className="text-red-500">*</span>
                    </h2>
                    <p className="text-sm text-slate-500 mb-6">Select all that apply to your business priorities</p>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {GOALS_OPTIONS.map(goal => (
                            <motion.button
                                key={goal.id}
                                type="button"
                                whileHover={{ scale: 1.03 }}
                                whileTap={{ scale: 0.97 }}
                                onClick={() => handleGoalToggle(goal.id)}
                                className={`
                                    p-4 rounded-xl text-center transition-all border-2
                                    ${formData.goals.includes(goal.id)
                                        ? 'bg-teal-600 border-teal-600 text-white shadow-lg shadow-teal-500/30'
                                        : 'bg-white border-slate-200 text-slate-700 hover:border-teal-300'
                                    }
                                `}
                            >
                                <div className="text-2xl mb-2">{goal.icon}</div>
                                <div className="text-xs font-semibold leading-tight">{goal.label}</div>
                            </motion.button>
                        ))}
                    </div>

                    {formData.goals.length > 0 && (
                        <div className="mt-4 text-sm text-teal-600 font-medium">
                            {formData.goals.length} goal{formData.goals.length > 1 ? 's' : ''} selected
                        </div>
                    )}
                </div>

                {/* Submit Button */}
                <div className="flex justify-end pt-4">
                    <motion.button
                        type="submit"
                        disabled={loading || !isFormValid}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="px-5 sm:px-8 py-3 sm:py-4 rounded-xl text-white bg-gradient-to-r from-teal-600 to-cyan-600 font-bold text-base sm:text-lg shadow-lg shadow-teal-500/30 hover:shadow-xl hover:shadow-teal-500/40 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none flex items-center gap-2 sm:gap-3 transition-all"
                    >
                        {loading ? (
                            <>
                                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Saving...
                            </>
                        ) : (
                            <>
                                Continue to Preferences
                                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="5" y1="12" x2="19" y2="12"></line>
                                    <polyline points="12 5 19 12 12 19"></polyline>
                                </svg>
                            </>
                        )}
                    </motion.button>
                </div>
            </form>
        </div>
    );
}
