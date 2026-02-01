'use client';

import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

const STEPS = [
    { path: '/onboarding/business-context', label: 'Business', icon: '🏢' },
    { path: '/onboarding/preferences', label: 'Preferences', icon: '⚙️' },
    { path: '/onboarding/agent-setup', label: 'Your Agent', icon: '🤖' },
];

export default function OnboardingLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const router = useRouter();

    // Handle processing page separately (no stepper)
    const isProcessingPage = pathname?.includes('/processing');

    const currentStepIndex = STEPS.findIndex((step) => pathname?.includes(step.path));
    const progress = currentStepIndex >= 0 ? ((currentStepIndex + 1) / STEPS.length) * 100 : 0;

    const handleStepClick = (stepIndex: number) => {
        // Only allow clicking on completed steps
        if (stepIndex < currentStepIndex) {
            router.push(STEPS[stepIndex].path);
        }
    };

    if (isProcessingPage) {
        return (
            <div className="font-display antialiased text-slate-800 bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900 min-h-screen flex flex-col relative overflow-hidden selection:bg-teal-500 selection:text-white">
                {/* Animated Background */}
                <div className="fixed inset-0 z-0">
                    <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse"></div>
                    <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
                </div>

                <main className="relative z-10 w-full flex-grow flex items-center justify-center p-6">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={pathname}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 1.05 }}
                            transition={{ duration: 0.4, ease: 'easeOut' }}
                            className="w-full max-w-lg"
                        >
                            {children}
                        </motion.div>
                    </AnimatePresence>
                </main>
            </div>
        );
    }

    return (
        <div className="font-display antialiased text-slate-800 bg-white min-h-screen flex flex-col relative overflow-hidden selection:bg-teal-500 selection:text-white">
            {/* Header with Logo */}
            <header className="relative z-20 w-full px-6 lg:px-12 pt-6 pb-4">
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-600 to-teal-700 text-white flex items-center justify-center shadow-lg shadow-teal-500/25 transform -rotate-3">
                            <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6">
                                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor" />
                            </svg>
                        </div>
                        <span className="text-xl font-bold tracking-tight text-slate-800 font-outfit">Pikar AI</span>
                    </div>

                    <div className="text-sm text-slate-500">
                        Setup Progress
                    </div>
                </div>
            </header>

            <main className="relative z-10 w-full max-w-4xl mx-auto flex-grow flex flex-col px-6 lg:px-12 py-6">
                {/* Progress Section */}
                <div className="mb-10">
                    {/* Progress Bar */}
                    <div className="relative h-2 bg-slate-200 rounded-full overflow-hidden mb-8">
                        <motion.div
                            className="absolute inset-y-0 left-0 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 0.5, ease: 'easeOut' }}
                        />
                    </div>

                    {/* Step Indicators */}
                    <div className="flex items-center justify-between">
                        {STEPS.map((step, index) => {
                            const isCompleted = index < currentStepIndex;
                            const isCurrent = index === currentStepIndex;
                            const isClickable = index < currentStepIndex;

                            return (
                                <div 
                                    key={step.path} 
                                    className={`flex flex-col items-center gap-2 ${isClickable ? 'cursor-pointer' : ''}`}
                                    onClick={() => handleStepClick(index)}
                                >
                                    <motion.div
                                        className={`
                                            relative w-14 h-14 rounded-2xl flex items-center justify-center 
                                            transition-all duration-300 text-2xl
                                            ${isCompleted 
                                                ? 'bg-gradient-to-br from-teal-500 to-cyan-500 text-white shadow-lg shadow-teal-500/30' 
                                                : isCurrent 
                                                    ? 'bg-white border-2 border-teal-500 shadow-lg shadow-teal-500/20'
                                                    : 'bg-slate-100 border border-slate-200 text-slate-400'
                                            }
                                        `}
                                        whileHover={isClickable ? { scale: 1.05 } : {}}
                                        whileTap={isClickable ? { scale: 0.95 } : {}}
                                    >
                                        {isCompleted ? (
                                            <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                                <polyline points="20 6 9 17 4 12"></polyline>
                                            </svg>
                                        ) : (
                                            <span>{step.icon}</span>
                                        )}
                                        
                                        {isCurrent && (
                                            <motion.div
                                                className="absolute inset-0 rounded-2xl border-2 border-teal-400"
                                                initial={{ scale: 1, opacity: 1 }}
                                                animate={{ scale: 1.2, opacity: 0 }}
                                                transition={{ duration: 1.5, repeat: Infinity }}
                                            />
                                        )}
                                    </motion.div>
                                    
                                    <div className="text-center">
                                        <span className={`
                                            text-xs font-semibold uppercase tracking-wider transition-colors duration-300
                                            ${isCurrent ? 'text-teal-600' : isCompleted ? 'text-slate-600' : 'text-slate-400'}
                                        `}>
                                            Step {index + 1}
                                        </span>
                                        <p className={`
                                            text-sm font-medium mt-0.5 transition-colors duration-300
                                            ${isCurrent ? 'text-slate-800' : isCompleted ? 'text-slate-600' : 'text-slate-400'}
                                        `}>
                                            {step.label}
                                        </p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Content */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={pathname}
                        initial={{ opacity: 0, y: 20, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -20, scale: 0.98 }}
                        transition={{ duration: 0.3, ease: 'easeOut' }}
                        className="flex-grow"
                    >
                        {children}
                    </motion.div>
                </AnimatePresence>
            </main>

            {/* Footer */}
            <footer className="relative z-10 w-full px-6 py-4 text-center text-xs text-slate-400">
                © 2024 Pikar AI Inc. · Your data is encrypted and secure
            </footer>
        </div>
    );
}
