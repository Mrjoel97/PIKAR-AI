'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { signUp, signInWithGoogle } from '../../../services/auth';
import Link from 'next/link';

// SVG Icon Components for Feature Cards
const SpeedIcon = () => (
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <circle cx="24" cy="24" r="20" fill="url(#speed-gradient)" />
        <path d="M24 12L14 28H22L22 36L32 20H24L24 12Z" fill="#0d9488" stroke="#0d9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <defs>
            <linearGradient id="speed-gradient" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#f0fdfa" />
                <stop offset="1" stopColor="#ccfbf1" />
            </linearGradient>
        </defs>
    </svg>
);

const IntelligenceIcon = () => (
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <circle cx="24" cy="24" r="20" fill="url(#intel-gradient)" />
        <circle cx="24" cy="20" r="8" stroke="#0d9488" strokeWidth="2.5" fill="#ccfbf1" />
        <path d="M16 32C16 28 19.5 26 24 26C28.5 26 32 28 32 32" stroke="#0d9488" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="21" cy="18" r="1.5" fill="#0d9488" />
        <circle cx="27" cy="18" r="1.5" fill="#0d9488" />
        <path d="M21 22C21 22 22.5 24 24 24C25.5 24 27 22 27 22" stroke="#0d9488" strokeWidth="1.5" strokeLinecap="round" />
        <defs>
            <linearGradient id="intel-gradient" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#f0fdfa" />
                <stop offset="1" stopColor="#ccfbf1" />
            </linearGradient>
        </defs>
    </svg>
);

const ShieldIcon = () => (
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <circle cx="24" cy="24" r="20" fill="url(#shield-gradient)" />
        <path d="M24 10L34 14V22C34 28.627 29.627 34 24 36C18.373 34 14 28.627 14 22V14L24 10Z" stroke="#0d9488" strokeWidth="2.5" fill="#ccfbf1" strokeLinejoin="round" />
        <path d="M20 24L23 27L28 21" stroke="#0d9488" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <defs>
            <linearGradient id="shield-gradient" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#f0fdfa" />
                <stop offset="1" stopColor="#ccfbf1" />
            </linearGradient>
        </defs>
    </svg>
);

export default function SignupPage() {
    const router = useRouter();
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Prefetch the onboarding route so navigation is instant after signup
    useEffect(() => {
        router.prefetch('/onboarding');
    }, [router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (password !== confirmPassword) {
            setError("Passwords don't match");
            return;
        }

        setLoading(true);
        try {
            const data = await signUp(email, password);
            if (data) {
                router.replace('/onboarding');
            }
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to sign up';
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSignIn = async () => {
        try {
            await signInWithGoogle();
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to initiate Google login';
            setError(errorMessage);
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
                                Join the{' '}
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-cyan-600">
                                    AI Revolution
                                </span>
                            </h1>
                            <p className="text-sm text-slate-600 font-medium leading-relaxed">
                                Next-gen AI interfaces. Fast, secure, beautiful.
                            </p>
                        </div>

                        {/* Feature Cards */}
                        <div className="flex flex-col gap-3">
                            <div className="bg-white rounded-xl p-3 flex items-center gap-4 shadow-md shadow-slate-200/50 border border-slate-100 hover:shadow-lg hover:border-teal-100 transition-all duration-300">
                                <div className="w-12 h-12 rounded-lg shrink-0">
                                    <SpeedIcon />
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">Lightning Speed</h3>
                                    <p className="text-xs text-slate-500">Processing power that keeps up</p>
                                </div>
                            </div>

                            <div className="bg-white rounded-xl p-3 flex items-center gap-4 shadow-md shadow-slate-200/50 border border-slate-100 hover:shadow-lg hover:border-teal-100 transition-all duration-300">
                                <div className="w-12 h-12 rounded-lg shrink-0">
                                    <IntelligenceIcon />
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">Deep Intelligence</h3>
                                    <p className="text-xs text-slate-500">Adaptive learning that evolves</p>
                                </div>
                            </div>

                            <div className="bg-white rounded-xl p-3 flex items-center gap-4 shadow-md shadow-slate-200/50 border border-slate-100 hover:shadow-lg hover:border-teal-100 transition-all duration-300">
                                <div className="w-12 h-12 rounded-lg shrink-0">
                                    <ShieldIcon />
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">Bank-Grade Security</h3>
                                    <p className="text-xs text-slate-500">Enterprise encryption & compliance</p>
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
                <section className="w-full md:w-1/2 flex items-center justify-center p-4 md:p-6 relative h-full min-h-[100dvh] md:min-h-0 bg-gradient-to-br from-teal-700 via-teal-800 to-slate-900">
                    {/* Decorative elements */}
                    <div className="absolute inset-0 overflow-hidden">
                        <div className="absolute -top-24 -right-24 w-72 h-72 bg-teal-500/20 rounded-full blur-3xl"></div>
                        <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-cyan-500/20 rounded-full blur-3xl"></div>
                    </div>

                    <div className="relative w-full max-w-sm">
                        <div className="relative overflow-hidden bg-white/10 backdrop-blur-xl rounded-2xl shadow-2xl p-5 border border-white/20">
                            <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent pointer-events-none"></div>

                            <div className="relative z-10 flex flex-col gap-3">
                                {/* Header */}
                                <div className="text-center space-y-1">
                                    <div className="mx-auto w-10 h-10 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center mb-1 backdrop-blur-sm">
                                        <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5 text-white">
                                            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor" />
                                        </svg>
                                    </div>
                                    <h1 className="text-lg font-bold font-outfit text-white tracking-tight">Create Account</h1>
                                    <p className="text-teal-200/70 text-xs font-medium">Start your AI journey today</p>
                                </div>

                                {error && (
                                    <div className="bg-red-500/20 border border-red-400/50 text-red-100 px-3 py-2 rounded-lg text-xs text-center">
                                        {error}
                                    </div>
                                )}

                                <form className="flex flex-col gap-2.5" onSubmit={handleSubmit}>
                                    <div className="group">
                                        <label className="block text-teal-100/90 text-xs font-medium mb-1 pl-1" htmlFor="fullName">Full Name</label>
                                        <div className="relative">
                                            <svg viewBox="0 0 24 24" fill="none" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-teal-300/60">
                                                <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
                                                <path d="M4 20c0-4 4-6 8-6s8 2 8 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                            </svg>
                                            <input
                                                className="w-full bg-white/10 border border-white/20 rounded-lg py-2 pl-9 pr-3 text-white placeholder-teal-300/40 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-200 font-medium text-sm min-h-[44px]"
                                                id="fullName"
                                                placeholder="John Doe"
                                                type="text"
                                                value={fullName}
                                                onChange={(e) => setFullName(e.target.value)}
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div className="group">
                                        <label className="block text-teal-100/90 text-xs font-medium mb-1 pl-1" htmlFor="email">Email Address</label>
                                        <div className="relative">
                                            <svg viewBox="0 0 24 24" fill="none" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-teal-300/60">
                                                <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" strokeWidth="2" />
                                                <path d="M2 7l10 7 10-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                            </svg>
                                            <input
                                                autoComplete="email"
                                                className="w-full bg-white/10 border border-white/20 rounded-lg py-2 pl-9 pr-3 text-white placeholder-teal-300/40 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-200 font-medium text-sm min-h-[44px]"
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
                                        <label className="block text-teal-100/90 text-xs font-medium mb-1 pl-1" htmlFor="password">Password</label>
                                        <div className="relative">
                                            <svg viewBox="0 0 24 24" fill="none" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-teal-300/60">
                                                <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="2" />
                                                <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                            </svg>
                                            <input
                                                className="w-full bg-white/10 border border-white/20 rounded-lg py-2 pl-9 pr-9 text-white placeholder-teal-300/40 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-200 font-medium text-sm min-h-[44px]"
                                                id="password"
                                                placeholder="Create a password"
                                                type="password"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                required
                                            />
                                            <button className="absolute right-3 top-1/2 -translate-y-1/2 text-teal-300/60 hover:text-white transition-colors cursor-pointer" type="button">
                                                <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4">
                                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="2" />
                                                    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
                                                </svg>
                                            </button>
                                        </div>
                                    </div>

                                    <div className="group">
                                        <label className="block text-teal-100/90 text-xs font-medium mb-1 pl-1" htmlFor="confirmPassword">Confirm Password</label>
                                        <div className="relative">
                                            <svg viewBox="0 0 24 24" fill="none" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-teal-300/60">
                                                <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                                <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="2" />
                                            </svg>
                                            <input
                                                className="w-full bg-white/10 border border-white/20 rounded-lg py-2 pl-9 pr-3 text-white placeholder-teal-300/40 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-200 font-medium text-sm min-h-[44px]"
                                                id="confirmPassword"
                                                placeholder="Confirm password"
                                                type="password"
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                                required
                                            />
                                        </div>
                                    </div>

                                    <button
                                        className="mt-1 w-full bg-white text-teal-700 text-sm font-bold py-2.5 rounded-lg hover:bg-teal-50 focus:ring-2 focus:ring-white/50 outline-none flex items-center justify-center gap-2 cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed shadow-lg shadow-black/20 transition-all duration-200 min-h-[44px]"
                                        type="submit"
                                        disabled={loading}
                                    >
                                        <span>{loading ? 'Creating...' : 'Create Account'}</span>
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
                                        Already have an account?{' '}
                                        <Link className="text-white font-bold hover:underline decoration-2 underline-offset-4" href="/auth/login">
                                            Sign in
                                        </Link>
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
