'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { submitPreferences, UserPreferencesInput } from '../../../services/onboarding';

export default function PreferencesPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<UserPreferencesInput>({
        tone: 'professional',
        verbosity: 'concise',
        communication_style: 'direct',
        notification_frequency: 'daily'
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await submitPreferences(formData);
            router.push('/onboarding/processing');
        } catch (error) {
            console.error('Failed to submit preferences', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-2xl">
            <h1 className="text-3xl font-outfit font-bold text-slate-800 mb-2">Communication Preferences</h1>
            <p className="text-slate-500 mb-8">How should your agents communicate with you?</p>

            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="clay-card p-6 md:p-8 space-y-8">

                    {/* Tone Selection */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-4">Tone of Voice</label>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            {[
                                { id: 'professional', label: 'Professional', desc: 'Formal and precise' },
                                { id: 'casual', label: 'Casual', desc: 'Relaxed and friendly' },
                                { id: 'enthusiastic', label: 'Enthusiastic', desc: 'Energetic and inspiring' }
                            ].map(option => (
                                <button
                                    key={option.id}
                                    type="button"
                                    onClick={() => setFormData({ ...formData, tone: option.id })}
                                    className={`p-4 rounded-2xl text-left border transition-all h-full
                                        ${formData.tone === option.id
                                            ? 'bg-teal-50 border-teal-500 ring-1 ring-teal-500/20'
                                            : 'bg-white border-slate-200 hover:border-teal-300'
                                        }
                                    `}
                                >
                                    <div className={`font-bold mb-1 ${formData.tone === option.id ? 'text-teal-700' : 'text-slate-700'}`}>
                                        {option.label}
                                    </div>
                                    <div className="text-xs text-slate-500">{option.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Verbosity Selection */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-4">Verbosity</label>
                        <div className="flex flex-col gap-3">
                            {[
                                { id: 'concise', label: 'Concise', desc: 'Get straight to the point. Bullet points preferred.' },
                                { id: 'detailed', label: 'Detailed', desc: 'Explain context and reasoning thoroughly.' }
                            ].map(option => (
                                <button
                                    key={option.id}
                                    type="button"
                                    onClick={() => setFormData({ ...formData, verbosity: option.id })}
                                    className={`p-4 rounded-xl flex items-center gap-4 border transition-all
                                         ${formData.verbosity === option.id
                                            ? 'bg-teal-50 border-teal-500'
                                            : 'bg-white border-slate-200 hover:border-teal-300'
                                        }
                                    `}
                                >
                                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center
                                         ${formData.verbosity === option.id ? 'border-teal-500' : 'border-slate-300'}
                                    `}>
                                        {formData.verbosity === option.id && <div className="w-2.5 h-2.5 rounded-full bg-teal-500"></div>}
                                    </div>
                                    <div className="text-left">
                                        <div className={`font-semibold ${formData.verbosity === option.id ? 'text-teal-900' : 'text-slate-700'}`}>
                                            {option.label}
                                        </div>
                                        <div className="text-xs text-slate-500">{option.desc}</div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>

                </div>

                <div className="flex justify-end pt-4">
                    <button
                        type="submit"
                        disabled={loading}
                        className="clay-button-primary px-8 py-3 rounded-full text-white bg-teal-600 font-bold hover:bg-teal-700 flex items-center gap-2"
                    >
                        {loading ? 'Saving...' : 'Review & Finish'}
                        {!loading && <span className="material-symbols-outlined">check_circle</span>}
                    </button>
                </div>
            </form>
        </div>
    );
}
