'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { signIn, signInWithGoogle } from '../../../services/auth';

// SVG Icon Components for Feature Cards
const AutomationIcon = () => (
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <circle cx="24" cy="24" r="20" fill="url(#automation-gradient)" />
        <path d="M24 12C17.373 12 12 17.373 12 24C12 30.627 17.373 36 24 36C30.627 36 36 30.627 36 24" stroke="#0d9488" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M24 16V24L28 28" stroke="#0d9488" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="24" cy="24" r="3" fill="#0d9488" />
        <path d="M36 18L36 24L30 24" stroke="#0d9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <defs>
            <linearGradient id="automation-gradient" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#f0fdfa" />
                <stop offset="1" stopColor="#ccfbf1" />
            </linearGradient>
        </defs>
    </svg>
);

const IntegrationIcon = () => (
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <circle cx="24" cy="24" r="20" fill="url(#integration-gradient)" />
        <circle cx="24" cy="16" r="4" stroke="#0d9488" strokeWidth="2.5" fill="#ccfbf1" />
        <circle cx="16" cy="30" r="4" stroke="#0d9488" strokeWidth="2.5" fill="#ccfbf1" />
        <circle cx="32" cy="30" r="4" stroke="#0d9488" strokeWidth="2.5" fill="#ccfbf1" />
        <path d="M24 20V24M20 28L24 24M28 28L24 24" stroke="#0d9488" strokeWidth="2" strokeLinecap="round" />
        <defs>
            <linearGradient id="integration-gradient" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#f0fdfa" />
                <stop offset="1" stopColor="#ccfbf1" />
            </linearGradient>
        </defs>
    </svg>
);

const SecurityIcon = () => (
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <circle cx="24" cy="24" r="20" fill="url(#security-gradient)" />
        <path d="M24 10L34 14V22C34 28.627 29.627 34 24 36C18.373 34 14 28.627 14 22V14L24 10Z" stroke="#0d9488" strokeWidth="2.5" fill="#ccfbf1" strokeLinejoin="round" />
        <path d="M20 24L23 27L28 21" stroke="#0d9488" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <defs>
            <linearGradient id="security-gradient" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#f0fdfa" />
                <stop offset="1" stopColor="#ccfbf1" />
            </linearGradient>
        </defs>
    </svg>
);

export default function LoginPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const sessionExpired = searchParams.get('reason') === 'session_expired';

    // Prefetch the command center route so navigation is instant after login
    useEffect(() => {
        router.prefetch('/dashboard/command-center');
    }, [router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const data = await signIn(email, password);
            if (data) {
                // Navigate immediately — middleware handles onboarding/persona routing.
                // This avoids a redundant getOnboardingStatus() API call (~200-500ms saved).
                router.replace('/dashboard/command-center');
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to login';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSignIn = async () => {
        try {
            await signInWithGoogle();
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to initiate Google login';
            setError(message);
        }
    };

    return (
        <div className="font-display antialiased text-slate-800 bg-gradient-to-br from-slate-50 via-white to-teal-50/30 h-[100dvh] w-full flex relative overflow-hidden selection:bg-teal-500 selection:text-white">
            {/* Subtle background pattern */}
            <div className="fixed inset-0 z-0 opacity-40 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, #cbd5e1 1px, transparent 0)', backgroundSize: '32px 32px' }}></div>

            <main className="relative z-10 w-full h-[100dvh] flex flex-col md:flex-row overflow-y-auto">
                {/* Left Side - Content/Features */}
                <section className="hidden md:flex md:w-1/2 p-4 md:p-8 xl:p-10 flex-col justify-between h-full relative z-10 bg-white/50 backdrop-blur-sm">
                    {/* Logo */}
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-600 to-teal-700 text-white flex items-center justify-center shadow-lg shadow-teal-500/25 transform -rotate-3">
                            <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
                                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor" />
                            </svg>
                        </div>
                        <span className="text-lg font-bold tracking-tight text-slate-800 font-outfit">Pikar AI</span>
                    </div>

                    {/* Main Content */}
                    <div className="flex flex-col justify-center flex-grow space-y-4 max-w-lg py-4">
                        <div className="space-y-2">
                            <h1 className="font-outfit text-2xl lg:text-3xl font-bold text-slate-900 leading-tight tracking-tight">
                                Empower Your Team with{' '}
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-cyan-600">
                                    Autonomous Intelligence
                                </span>
                            </h1>
                            <p className="text-sm text-slate-600 font-medium leading-relaxed">
                                Scale your business operations effortlessly with AI agents.
                            </p>
                        </div>

                        {/* Feature Cards */}
                        <div className="flex flex-col gap-3">
                            <div className="bg-white rounded-xl p-3 flex items-center gap-4 shadow-md shadow-slate-200/50 border border-slate-100 hover:shadow-lg hover:border-teal-100 transition-all duration-300">
                                <div className="w-12 h-12 rounded-lg shrink-0">
                                    <AutomationIcon />
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">24/7 Automation</h3>
                                    <p className="text-xs text-slate-500">Continuous operations that never sleep</p>
                                </div>
                            </div>

                            <div className="bg-white rounded-xl p-3 flex items-center gap-4 shadow-md shadow-slate-200/50 border border-slate-100 hover:shadow-lg hover:border-teal-100 transition-all duration-300">
                                <div className="w-12 h-12 rounded-lg shrink-0">
                                    <IntegrationIcon />
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">Deep Integration</h3>
                                    <p className="text-xs text-slate-500">Seamless connections with your tools</p>
                                </div>
                            </div>

                            <div className="bg-white rounded-xl p-3 flex items-center gap-4 shadow-md shadow-slate-200/50 border border-slate-100 hover:shadow-lg hover:border-teal-100 transition-all duration-300">
                                <div className="w-12 h-12 rounded-lg shrink-0">
                                    <SecurityIcon />
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">Enterprise Security</h3>
                                    <p className="text-xs text-slate-500">Bank-grade encryption & compliance</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="text-xs text-slate-400 hidden md:block">
                        © 2024 Pikar AI Inc. All rights reserved.
                    </div>
                </section>

                {/* Right Side - Form */}
                <section className="w-full md:w-1/2 flex items-center justify-center p-4 md:p-8 relative h-full min-h-[100dvh] md:min-h-0 bg-gradient-to-br from-teal-700 via-teal-800 to-slate-900">
                    {/* Decorative elements */}
                    <div className="absolute inset-0 overflow-hidden">
                        <div className="absolute -top-24 -right-24 w-72 h-72 bg-teal-500/20 rounded-full blur-3xl"></div>
                        <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-cyan-500/20 rounded-full blur-3xl"></div>
                    </div>

                    <div className="relative w-full max-w-sm">
                        <div className="relative overflow-hidden bg-white/10 backdrop-blur-xl rounded-2xl shadow-2xl p-6 border border-white/20">
                            <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent pointer-events-none"></div>

                            <div className="relative z-10 flex flex-col gap-4">
                                {/* Header */}
                                <div className="text-center space-y-1">
                                    <div className="mx-auto w-11 h-11 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center mb-2 backdrop-blur-sm">
                                        <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6 text-white">
                                            <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="2" />
                                            <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                        </svg>
                                    </div>
                                    <h1 className="text-xl font-bold font-outfit text-white tracking-tight">Welcome Back</h1>
                                    <p className="text-teal-200/70 text-xs font-medium">Enter your credentials to continue</p>
                                </div>

                                {sessionExpired && (
                                    <div className="bg-amber-500/20 border border-amber-400/50 text-amber-100 px-3 py-2 rounded-lg text-xs text-center">
                                        Your session has expired. Please sign in again.
                                    </div>
                                )}

                                {error && (
                                    <div className="bg-red-500/20 border border-red-400/50 text-red-100 px-3 py-2 rounded-lg text-xs text-center">
                                        {error}
                                    </div>
                                )}

                                <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
                                    <div className="group">
                                        <label className="block text-teal-100/90 text-xs font-medium mb-1 pl-1" htmlFor="email">Email Address</label>
                                        <div className="relative">
                                            <svg viewBox="0 0 24 24" fill="none" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-teal-300/60">
                                                <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" strokeWidth="2" />
                                                <path d="M2 7l10 7 10-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                            </svg>
                                            <input
                                                autoComplete="email"
                                                className="w-full bg-white/10 border border-white/20 rounded-lg py-2.5 pl-10 pr-3 text-white placeholder-teal-300/40 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-200 font-medium text-sm min-h-[44px]"
                                                id="email"
                                                placeholder="name@company.com"
                                                type="email"
                                                value={email}
                                                onChange={(e) => setEmail(e.target.value)}
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div className="group">
                                        <div className="flex justify-between items-center mb-1 px-1">
                                            <label className="block text-teal-100/90 text-xs font-medium" htmlFor="password">Password</label>
                                            <a className="text-xs text-teal-300 hover:text-white transition-colors font-medium" href="/auth/forgot-password">Forgot?</a>
                                        </div>
                                        <div className="relative">
                                            <svg viewBox="0 0 24 24" fill="none" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-teal-300/60">
                                                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                            <input
                                                className="w-full bg-white/10 border border-white/20 rounded-lg py-2.5 pl-10 pr-10 text-white placeholder-teal-300/40 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-200 font-medium text-sm min-h-[44px]"
                                                id="password"
                                                placeholder="Enter your password"
                                                type={showPassword ? 'text' : 'password'}
                                                autoComplete="current-password"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                required
                                            />
                                            <button className="absolute right-3 top-1/2 -translate-y-1/2 text-teal-300/60 hover:text-white transition-colors cursor-pointer" type="button" onClick={() => setShowPassword(p => !p)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                                                <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4">
                                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="2" />
                                                    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
                                                </svg>
                                            </button>
                                        </div>
                                    </div>

                                    <button
                                        className="mt-1 w-full bg-white text-teal-700 text-sm font-bold py-2.5 rounded-lg hover:bg-teal-50 focus:ring-2 focus:ring-white/50 outline-none flex items-center justify-center gap-2 cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed shadow-lg shadow-black/20 transition-all duration-200 min-h-[44px]"
                                        type="submit"
                                        disabled={loading}
                                    >
                                        <span>{loading ? 'Signing in...' : 'Sign In'}</span>
                                        {!loading && (
                                            <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4">
                                                <path d="M5 12h14m-7-7l7 7-7 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        )}
                                    </button>

                                    <div className="relative py-1 flex items-center gap-3">
                                        <div className="h-px bg-white/20 flex-1"></div>
                                        <span className="text-teal-200/50 text-[10px] uppercase tracking-widest font-semibold">Or</span>
                                        <div className="h-px bg-white/20 flex-1"></div>
                                    </div>

                                    <button
                                        className="w-full py-2.5 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg flex items-center justify-center gap-2 text-white font-medium focus:ring-2 focus:ring-white/30 outline-none group cursor-pointer text-sm transition-all duration-200"
                                        type="button"
                                        onClick={handleGoogleSignIn}
                                    >
                                        <svg className="w-4 h-4 group-hover:scale-110 transition-transform duration-200" viewBox="0 0 24 24">
                                            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                        </svg>
                                        Continue with Google
                                    </button>
                                </form>

                                <div className="text-center">
                                    <p className="text-teal-200/70 text-xs">
                                        Don&apos;t have an account?{' '}
                                        <a className="text-white font-bold hover:underline decoration-2 underline-offset-4" href="/auth/signup">
                                            Create one
                                        </a>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Mobile footer */}
                    <div className="md:hidden absolute bottom-4 left-0 right-0 text-center text-teal-200/50 text-xs">
                        <p>© 2024 Pikar AI Inc.</p>
                    </div>
                </section>
            </main>
        </div>
    );
}
