'use client';

import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';

export default function OnboardingLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    const steps = [
        { path: '/onboarding/welcome', label: 'Welcome' },
        { path: '/onboarding/business-context', label: 'Business Context' },
        { path: '/onboarding/preferences', label: 'Preferences' },
        { path: '/onboarding/processing', label: 'Processing' },
    ];

    const currentStepIndex = steps.findIndex((step) => pathname?.includes(step.path));

    return (
        <div className="font-display antialiased text-slate-800 bg-background-light dark:bg-background-dark min-h-screen flex flex-col relative overflow-hidden selection:bg-teal-500 selection:text-white">
            {/* Background Effects */}
            <div className="fixed inset-0 z-0 opacity-40 bg-dot-grid pointer-events-none"></div>
            <div className="fixed top-0 left-0 w-full h-full z-0 pointer-events-none overflow-hidden">
                <div className="absolute top-[-10%] left-[-10%] w-[40rem] h-[40rem] bg-teal-200/30 rounded-full blur-3xl mix-blend-multiply filter opacity-50 animate-blob"></div>
                <div className="absolute top-[-10%] right-[-10%] w-[35rem] h-[35rem] bg-purple-200/30 rounded-full blur-3xl mix-blend-multiply filter opacity-50 animate-blob animation-delay-2000"></div>
            </div>

            <main className="relative z-10 w-full max-w-5xl mx-auto flex-grow flex flex-col p-6 lg:p-12">
                {/* Stepper only visible if not on welcome page? Or always visible? 
                    Let's hide it on Welcome page for a cleaner look, or show it. 
                    The plan says "Progress stepper at the top". I will show it.
                */}
                <div className="mb-12">
                    <div className="flex items-center justify-between relative">
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-slate-200 rounded-full -z-10"></div>
                        <div
                            className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-teal-500 rounded-full -z-10 transition-all duration-500 ease-out"
                            style={{ width: `${(currentStepIndex / (steps.length - 1)) * 100}%` }}
                        ></div>

                        {steps.map((step, index) => {
                            const isCompleted = index < currentStepIndex;
                            const isCurrent = index === currentStepIndex;

                            return (
                                <div key={step.path} className="flex flex-col items-center gap-2">
                                    <div
                                        className={`w-10 h-10 rounded-full flex items-center justify-center border-4 transition-all duration-300 font-bold text-sm bg-white
                                            ${isCompleted || isCurrent ? 'border-teal-500 text-teal-600' : 'border-slate-200 text-slate-400'}
                                            ${isCurrent ? 'scale-110 shadow-lg ring-4 ring-teal-500/20' : ''}
                                        `}
                                    >
                                        {isCompleted ? (
                                            <span className="material-symbols-outlined text-base">check</span>
                                        ) : (
                                            <span>{index + 1}</span>
                                        )}
                                    </div>
                                    <span className={`text-xs font-semibold uppercase tracking-wider hidden sm:block transition-colors duration-300 ${isCurrent ? 'text-teal-600' : 'text-slate-400'}`}>
                                        {step.label}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <motion.div
                    key={pathname}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                    className="flex-grow flex flex-col items-center justify-center"
                >
                    {children}
                </motion.div>
            </main>
        </div>
    );
}
