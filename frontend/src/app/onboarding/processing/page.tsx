'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { completeOnboarding, PERSONA_INFO, PersonaType } from '@/services/onboarding';

const PROCESSING_STEPS = [
    { label: 'Analyzing business context', icon: '📊', duration: 1500 },
    { label: 'Configuring AI persona', icon: '🧠', duration: 1200 },
    { label: 'Training executive agent', icon: '🤖', duration: 1800 },
    { label: 'Setting up workspace', icon: '⚡', duration: 1000 },
    { label: 'Finalizing configuration', icon: '✨', duration: 800 },
];

export default function ProcessingPage() {
    const router = useRouter();
    const [currentStep, setCurrentStep] = useState(0);
    const [progress, setProgress] = useState(0);
    const [isComplete, setIsComplete] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [persona, setPersona] = useState<PersonaType | null>(null);
    const [agentName, setAgentName] = useState<string>('Your Agent');

    useEffect(() => {
        let isMounted = true;

        const runCompletion = async () => {
            try {
                // Animate through steps
                for (let i = 0; i < PROCESSING_STEPS.length; i++) {
                    if (!isMounted) return;
                    
                    setCurrentStep(i);
                    
                    // Calculate progress
                    const baseProgress = (i / PROCESSING_STEPS.length) * 100;
                    const stepProgress = PROCESSING_STEPS[i].duration / 50;
                    
                    // Animate progress within step
                    for (let j = 0; j <= stepProgress; j++) {
                        if (!isMounted) return;
                        const incrementalProgress = baseProgress + ((j / stepProgress) * (100 / PROCESSING_STEPS.length));
                        setProgress(Math.min(incrementalProgress, 95));
                        await new Promise(r => setTimeout(r, 50));
                    }
                }

                // Actually complete onboarding on backend
                const result = await completeOnboarding();
                
                if (!isMounted) return;

                // Final progress
                setProgress(100);
                setIsComplete(true);
                
                if (result.persona) {
                    setPersona(result.persona as PersonaType);
                }

                // Wait for celebration animation then redirect to persona dashboard
                await new Promise(r => setTimeout(r, 2500));

                if (isMounted) {
                    const personaRoute = result.persona ? `/${result.persona}` : '/dashboard/command-center';
                    router.push(personaRoute);
                }

            } catch (err) {
                if (isMounted) {
                    setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
                }
            }
        };

        runCompletion();

        return () => { isMounted = false; };
    }, [router]);

    if (error) {
        return (
            <div className="text-center">
                <motion.div 
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="w-24 h-24 mx-auto mb-6 rounded-full bg-red-500/20 flex items-center justify-center"
                >
                    <span className="text-5xl">😢</span>
                </motion.div>
                <h2 className="text-2xl font-bold text-white mb-3">Oops! Something went wrong</h2>
                <p className="text-slate-400 mb-6">{error}</p>
                <button 
                    onClick={() => router.push('/onboarding/agent-setup')}
                    className="px-6 py-3 bg-white/10 rounded-xl text-white font-medium hover:bg-white/20 transition-colors"
                >
                    Go Back & Try Again
                </button>
            </div>
        );
    }

    if (isComplete && persona) {
        const personaInfo = PERSONA_INFO[persona];
        
        return (
            <div className="text-center">
                {/* Celebration Animation */}
                <motion.div 
                    initial={{ scale: 0, rotate: -180 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: 'spring', damping: 10, stiffness: 100 }}
                    className="relative w-32 h-32 mx-auto mb-8"
                >
                    {/* Glow effect */}
                    <div className="absolute inset-0 bg-gradient-to-br from-teal-400 to-cyan-400 rounded-full blur-xl opacity-50 animate-pulse"></div>
                    
                    {/* Icon container */}
                    <div className={`relative w-full h-full rounded-full bg-gradient-to-br ${personaInfo.color} flex items-center justify-center shadow-2xl`}>
                        <span className="text-5xl">{personaInfo.icon}</span>
                    </div>
                    
                    {/* Success checkmark */}
                    <motion.div 
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.3, type: 'spring' }}
                        className="absolute -bottom-2 -right-2 w-12 h-12 bg-green-500 rounded-full flex items-center justify-center shadow-lg"
                    >
                        <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    </motion.div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                >
                    <h2 className="text-3xl font-bold text-white mb-3">
                        You&apos;re All Set! 🎉
                    </h2>
                    <p className="text-lg text-slate-300 mb-2">
                        Your {personaInfo.title} workspace is ready
                    </p>
                    <p className="text-slate-400 text-sm mb-8">
                        Redirecting to your dashboard...
                    </p>

                    {/* Persona Badge */}
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.6 }}
                        className={`inline-flex items-center gap-3 px-6 py-3 rounded-full bg-gradient-to-r ${personaInfo.color} text-white shadow-lg`}
                    >
                        <span className="text-2xl">{personaInfo.icon}</span>
                        <div className="text-left">
                            <div className="text-xs font-medium opacity-80">AI Mode</div>
                            <div className="font-bold">{personaInfo.title}</div>
                        </div>
                    </motion.div>
                </motion.div>
            </div>
        );
    }

    // Processing State
    return (
        <div className="text-center">
            {/* Animated AI Icon */}
            <div className="relative w-32 h-32 mx-auto mb-8">
                {/* Outer rotating ring */}
                <motion.div 
                    className="absolute inset-0 rounded-full border-4 border-teal-500/30"
                    style={{ borderTopColor: '#14b8a6', borderRightColor: '#06b6d4' }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                />
                
                {/* Middle pulsing ring */}
                <motion.div 
                    className="absolute inset-2 rounded-full border-2 border-cyan-400/50"
                    animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                />

                {/* Inner icon container */}
                <div className="absolute inset-4 rounded-full bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-teal-500/50">
                    <motion.span 
                        className="text-4xl"
                        animate={{ scale: [1, 1.1, 1] }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                    >
                        🤖
                    </motion.span>
                </div>

                {/* Progress ring */}
                <svg className="absolute inset-0 w-full h-full -rotate-90">
                    <circle
                        cx="64"
                        cy="64"
                        r="60"
                        fill="none"
                        stroke="rgba(255,255,255,0.1)"
                        strokeWidth="4"
                    />
                    <motion.circle
                        cx="64"
                        cy="64"
                        r="60"
                        fill="none"
                        stroke="url(#progressGradient)"
                        strokeWidth="4"
                        strokeLinecap="round"
                        strokeDasharray={377}
                        strokeDashoffset={377 - (377 * progress) / 100}
                        transition={{ duration: 0.2 }}
                    />
                    <defs>
                        <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#14b8a6" />
                            <stop offset="100%" stopColor="#06b6d4" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>

            {/* Progress Percentage */}
            <motion.div 
                className="text-4xl font-bold text-white mb-4"
                key={Math.floor(progress)}
            >
                {Math.floor(progress)}%
            </motion.div>

            {/* Current Step */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={currentStep}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="flex items-center justify-center gap-3 text-slate-300"
                >
                    <span className="text-2xl">{PROCESSING_STEPS[currentStep]?.icon}</span>
                    <span className="text-lg font-medium">{PROCESSING_STEPS[currentStep]?.label}</span>
                </motion.div>
            </AnimatePresence>

            {/* Step Indicators */}
            <div className="flex justify-center gap-2 mt-8">
                {PROCESSING_STEPS.map((step, index) => (
                    <motion.div
                        key={index}
                        className={`w-2 h-2 rounded-full transition-all duration-300 ${
                            index < currentStep ? 'bg-teal-400' :
                            index === currentStep ? 'bg-white w-6' :
                            'bg-white/20'
                        }`}
                        initial={false}
                        animate={{
                            scale: index === currentStep ? 1 : 0.8
                        }}
                    />
                ))}
            </div>

            {/* Subtle message */}
            <p className="text-slate-500 text-sm mt-8">
                Setting up your intelligent workspace...
            </p>
        </div>
    );
}
