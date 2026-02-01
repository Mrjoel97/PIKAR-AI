'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
    submitPreferences, 
    UserPreferencesInput,
    TONE_OPTIONS,
    VERBOSITY_OPTIONS,
    COMMUNICATION_STYLE_OPTIONS,
    NOTIFICATION_FREQUENCY_OPTIONS
} from '@/services/onboarding';

export default function PreferencesPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    const [formData, setFormData] = useState<UserPreferencesInput>({
        tone: 'professional',
        verbosity: 'concise',
        communication_style: 'direct',
        notification_frequency: 'daily'
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);
        
        try {
            await submitPreferences(formData);
            router.push('/onboarding/agent-setup');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to save. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        router.push('/onboarding/business-context');
    };

    return (
        <div className="w-full">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl lg:text-4xl font-outfit font-bold text-slate-800 mb-3">
                    Communication Preferences
                </h1>
                <p className="text-lg text-slate-500">
                    Customize how your AI assistant communicates with you.
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
                {/* Tone Selection */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2">
                        <span className="text-xl">🎭</span> Tone of Voice
                    </h2>
                    <p className="text-sm text-slate-500 mb-6">How should your AI assistant speak to you?</p>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {TONE_OPTIONS.map(option => (
                            <motion.button
                                key={option.id}
                                type="button"
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => setFormData({ ...formData, tone: option.id })}
                                className={`
                                    p-5 rounded-xl text-center border-2 transition-all
                                    ${formData.tone === option.id
                                        ? 'bg-teal-50 border-teal-500 shadow-md shadow-teal-500/20'
                                        : 'bg-white border-slate-200 hover:border-teal-300'
                                    }
                                `}
                            >
                                <div className="text-3xl mb-3">{option.icon}</div>
                                <div className={`font-bold mb-1 ${formData.tone === option.id ? 'text-teal-700' : 'text-slate-700'}`}>
                                    {option.label}
                                </div>
                                <div className="text-xs text-slate-500">{option.description}</div>
                            </motion.button>
                        ))}
                    </div>
                </div>

                {/* Verbosity Selection */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2">
                        <span className="text-xl">📝</span> Response Length
                    </h2>
                    <p className="text-sm text-slate-500 mb-6">How detailed should responses be?</p>
                    
                    <div className="space-y-3">
                        {VERBOSITY_OPTIONS.map(option => (
                            <motion.button
                                key={option.id}
                                type="button"
                                whileHover={{ scale: 1.01 }}
                                whileTap={{ scale: 0.99 }}
                                onClick={() => setFormData({ ...formData, verbosity: option.id })}
                                className={`
                                    w-full p-4 rounded-xl flex items-center gap-4 border-2 transition-all text-left
                                    ${formData.verbosity === option.id
                                        ? 'bg-teal-50 border-teal-500 shadow-md shadow-teal-500/20'
                                        : 'bg-white border-slate-200 hover:border-teal-300'
                                    }
                                `}
                            >
                                <div className="text-2xl">{option.icon}</div>
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0
                                    ${formData.verbosity === option.id ? 'border-teal-500 bg-teal-500' : 'border-slate-300'}
                                `}>
                                    {formData.verbosity === option.id && (
                                        <svg className="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4">
                                            <polyline points="20 6 9 17 4 12"></polyline>
                                        </svg>
                                    )}
                                </div>
                                <div className="flex-grow">
                                    <div className={`font-bold ${formData.verbosity === option.id ? 'text-teal-700' : 'text-slate-700'}`}>
                                        {option.label}
                                    </div>
                                    <div className="text-xs text-slate-500">{option.description}</div>
                                </div>
                            </motion.button>
                        ))}
                    </div>
                </div>

                {/* Communication Style Selection */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2">
                        <span className="text-xl">💬</span> Communication Style
                    </h2>
                    <p className="text-sm text-slate-500 mb-6">What approach works best for you?</p>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {COMMUNICATION_STYLE_OPTIONS.map(option => (
                            <motion.button
                                key={option.id}
                                type="button"
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => setFormData({ ...formData, communication_style: option.id })}
                                className={`
                                    p-5 rounded-xl text-left border-2 transition-all
                                    ${formData.communication_style === option.id
                                        ? 'bg-teal-50 border-teal-500 shadow-md shadow-teal-500/20'
                                        : 'bg-white border-slate-200 hover:border-teal-300'
                                    }
                                `}
                            >
                                <div className={`font-bold mb-1 ${formData.communication_style === option.id ? 'text-teal-700' : 'text-slate-700'}`}>
                                    {option.label}
                                </div>
                                <div className="text-xs text-slate-500">{option.description}</div>
                            </motion.button>
                        ))}
                    </div>
                </div>

                {/* Notification Frequency */}
                <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6 lg:p-8">
                    <h2 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2">
                        <span className="text-xl">🔔</span> Notification Frequency
                    </h2>
                    <p className="text-sm text-slate-500 mb-6">How often should your AI reach out with updates?</p>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {NOTIFICATION_FREQUENCY_OPTIONS.map(option => (
                            <motion.button
                                key={option.id}
                                type="button"
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => setFormData({ ...formData, notification_frequency: option.id })}
                                className={`
                                    p-5 rounded-xl text-left border-2 transition-all
                                    ${formData.notification_frequency === option.id
                                        ? 'bg-teal-50 border-teal-500 shadow-md shadow-teal-500/20'
                                        : 'bg-white border-slate-200 hover:border-teal-300'
                                    }
                                `}
                            >
                                <div className={`font-bold mb-1 ${formData.notification_frequency === option.id ? 'text-teal-700' : 'text-slate-700'}`}>
                                    {option.label}
                                </div>
                                <div className="text-xs text-slate-500">{option.description}</div>
                            </motion.button>
                        ))}
                    </div>
                </div>

                {/* Preview Card */}
                <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl shadow-xl p-6 text-white">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
                            <span className="text-xl">🤖</span>
                        </div>
                        <div>
                            <div className="text-sm text-slate-400">Preview</div>
                            <div className="font-bold">How your AI will respond</div>
                        </div>
                    </div>
                    <div className="bg-white/5 rounded-xl p-4 text-sm text-slate-300 leading-relaxed">
                        {formData.tone === 'professional' && formData.verbosity === 'concise' && (
                            "Your quarterly revenue shows a 12% increase. Key drivers: new customer acquisition (+8%) and upsells (+4%). Recommend focusing on retention strategies."
                        )}
                        {formData.tone === 'professional' && formData.verbosity === 'detailed' && (
                            "I've analyzed your quarterly performance metrics. Revenue has increased by 12% compared to the previous quarter. This growth is primarily attributed to two factors: new customer acquisition contributed 8% growth, while successful upselling to existing customers added an additional 4%. Based on this analysis, I recommend implementing retention-focused strategies to maximize customer lifetime value."
                        )}
                        {formData.tone === 'casual' && formData.verbosity === 'concise' && (
                            "Hey! Great news - revenue's up 12% this quarter! 🎉 New customers (+8%) and upsells (+4%) are driving growth. Let's work on keeping them around!"
                        )}
                        {formData.tone === 'casual' && (formData.verbosity === 'detailed' || formData.verbosity === 'balanced') && (
                            "Hey there! I've been crunching the numbers and have some exciting news - your revenue jumped 12% this quarter! That's awesome! Here's the breakdown: you brought in a bunch of new customers which added 8%, and your team did a great job upselling to existing folks for another 4%. My suggestion? Let's focus on keeping these happy customers coming back!"
                        )}
                        {formData.tone === 'enthusiastic' && formData.verbosity === 'concise' && (
                            "Amazing news! 🚀 Revenue SOARED 12% this quarter! New customers (+8%) and killer upsells (+4%) are fueling this growth! Let's keep this momentum going!"
                        )}
                        {formData.tone === 'enthusiastic' && (formData.verbosity === 'detailed' || formData.verbosity === 'balanced') && (
                            "WOW! 🎯 I'm thrilled to share these incredible results with you! Your revenue absolutely CRUSHED it this quarter with a phenomenal 12% increase! Here's what's driving this success: your customer acquisition efforts brought in 8% growth - that's fantastic! Plus, your team's upselling game is ON FIRE with another 4%! Let's channel this energy into retention strategies and keep the wins coming!"
                        )}
                        {formData.tone === 'professional' && formData.verbosity === 'balanced' && (
                            "Your quarterly revenue increased by 12%. This growth stems from new customer acquisition (+8%) and upselling (+4%). I recommend prioritizing retention strategies to sustain this momentum."
                        )}
                    </div>
                </div>

                {/* Navigation Buttons */}
                <div className="flex justify-between pt-4">
                    <motion.button
                        type="button"
                        onClick={handleBack}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="px-6 py-4 rounded-xl text-slate-600 bg-white border border-slate-200 font-semibold hover:bg-slate-50 flex items-center gap-2 transition-all"
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
                        className="px-8 py-4 rounded-xl text-white bg-gradient-to-r from-teal-600 to-cyan-600 font-bold text-lg shadow-lg shadow-teal-500/30 hover:shadow-xl hover:shadow-teal-500/40 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 transition-all"
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
                                Continue to Agent Setup
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
