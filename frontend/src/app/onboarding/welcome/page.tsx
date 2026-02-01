'use client';

import Link from 'next/link';

export default function OnboardingWelcomePage() {
    return (
        <div className="w-full max-w-2xl text-center">
            <div className="mx-auto w-24 h-24 rounded-3xl bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center mb-10 shadow-xl transform rotate-6 hover:rotate-12 transition-transform duration-500">
                <span className="material-symbols-outlined text-white text-5xl">rocket_launch</span>
            </div>

            <h1 className="font-outfit text-4xl md:text-6xl font-bold text-slate-900 mb-6 leading-tight">
                Welcome to <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-teal-400">Pikar AI</span>
            </h1>

            <p className="text-lg md:text-xl text-slate-500 leading-relaxed mb-12 max-w-lg mx-auto">
                We're thrilled to have you! Let's get your workspace set up in just a few steps to tailor the AI agents to your specific needs.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                    href="/onboarding/business-context"
                    className="clay-button-primary px-10 py-4 rounded-full text-white bg-teal-600 font-bold text-lg hover:bg-teal-700 transition-all flex items-center gap-2 group w-full sm:w-auto justify-center"
                >
                    <span>Start Setup</span>
                    <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">arrow_forward</span>
                </Link>
            </div>

            <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6 text-left">
                <div className="glass-card p-6 rounded-2xl border border-slate-100">
                    <span className="material-symbols-outlined text-teal-500 text-3xl mb-3">psychology</span>
                    <h3 className="font-bold text-slate-800 mb-1">Tailored AI</h3>
                    <p className="text-sm text-slate-500">Agents adapt to your business context.</p>
                </div>
                <div className="glass-card p-6 rounded-2xl border border-slate-100">
                    <span className="material-symbols-outlined text-purple-500 text-3xl mb-3">speed</span>
                    <h3 className="font-bold text-slate-800 mb-1">Fast Setup</h3>
                    <p className="text-sm text-slate-500">Get up and running in less than 2 minutes.</p>
                </div>
                <div className="glass-card p-6 rounded-2xl border border-slate-100">
                    <span className="material-symbols-outlined text-amber-500 text-3xl mb-3">security</span>
                    <h3 className="font-bold text-slate-800 mb-1">Secure</h3>
                    <p className="text-sm text-slate-500">Your data is encrypted and private.</p>
                </div>
            </div>
        </div>
    );
}
