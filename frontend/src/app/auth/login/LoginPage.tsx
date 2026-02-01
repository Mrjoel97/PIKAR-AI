'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signIn, signInWithGoogle } from '../../../services/auth';
import { getOnboardingStatus } from '../../../services/onboarding';

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const data = await signIn(email, password);
            // Supabase signIn might return a session or error.
            // If error is returned from the servicewrapper (which calls throw error), we catch it.
            // However, if the service wrapper structure is:
            // if (error) throw error; return data;
            // Then we are good.
            if (data) {
                try {
                    const status = await getOnboardingStatus();
                    if (!status.is_completed) {
                        router.push('/onboarding/welcome');
                    } else {
                        router.push('/dashboard');
                    }
                } catch (e) {
                    // Fallback to dashboard if status check fails (or onboarding not critical to block login)
                    // But explicitly requested to check.
                    console.error("Failed to check onboarding status", e);
                    router.push('/dashboard');
                }
            }
        } catch (err: any) {
            setError(err.message || 'Failed to login');
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSignIn = async () => {
        try {
            await signInWithGoogle();
        } catch (err: any) {
            setError(err.message || 'Failed to initiate Google login');
        }
    };

    return (
        <div className="font-display antialiased text-slate-800 bg-background-light dark:bg-background-dark h-screen w-full flex relative overflow-hidden selection:bg-teal-500 selection:text-white">
            <div className="fixed inset-0 z-0 opacity-30 bg-dot-grid pointer-events-none"></div>
            <main className="relative z-10 w-full h-full flex flex-col lg:flex-row overflow-hidden">
                <section className="w-full lg:w-1/2 p-4 lg:p-6 flex flex-col justify-between h-full relative z-10">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="size-6 rounded-lg bg-auth-primary text-white flex items-center justify-center shadow-md transform rotate-3">
                            <span className="material-symbols-outlined text-base">auto_awesome</span>
                        </div>
                        <span className="text-base font-bold tracking-tight text-auth-primary font-outfit">Pikar AI</span>
                    </div>
                    <div className="flex flex-col justify-center flex-grow space-y-4 max-w-md mx-auto lg:mx-0">
                        <div className="space-y-2">
                            <h1 className="font-outfit text-xl lg:text-2xl font-bold text-slate-900 leading-[1.15] tracking-tight">
                                Empower Your Team with <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-auth-primary">Autonomous Intelligence</span>
                            </h1>
                            <p className="text-sm text-slate-500 font-medium leading-relaxed max-w-sm">
                                Scale your business operations effortlessly with AI agents.
                            </p>
                        </div>
                        <div className="flex flex-col gap-2 mt-3">
                            <div className="glass-feature-card rounded-lg p-2 flex items-center gap-3">
                                <div className="size-8 rounded-lg bg-gradient-to-br from-teal-50 to-teal-100 border border-teal-200 flex items-center justify-center shadow-sm shrink-0">
                                    <span className="material-symbols-outlined text-teal-700 text-lg">smart_toy</span>
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">24/7 Automation</h3>
                                    <p className="text-xs text-slate-500">Continuous operations</p>
                                </div>
                            </div>
                            <div className="glass-feature-card rounded-lg p-2 flex items-center gap-3">
                                <div className="size-8 rounded-lg bg-gradient-to-br from-teal-50 to-teal-100 border border-teal-200 flex items-center justify-center shadow-sm shrink-0">
                                    <span className="material-symbols-outlined text-teal-700 text-lg">hub</span>
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">Deep Integration</h3>
                                    <p className="text-xs text-slate-500">Seamless connections</p>
                                </div>
                            </div>
                            <div className="glass-feature-card rounded-lg p-2 flex items-center gap-3">
                                <div className="size-8 rounded-lg bg-gradient-to-br from-teal-50 to-teal-100 border border-teal-200 flex items-center justify-center shadow-sm shrink-0">
                                    <span className="material-symbols-outlined text-teal-700 text-lg">shield_lock</span>
                                </div>
                                <div>
                                    <h3 className="font-outfit font-bold text-slate-800 text-sm">Enterprise Security</h3>
                                    <p className="text-xs text-slate-500">Bank-grade encryption</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="mt-4 text-xs text-slate-400 hidden lg:block">
                        © 2024 Pikar AI Inc.
                    </div>
                </section>
                <section className="w-full lg:w-1/2 flex items-center justify-center p-3 lg:p-4 relative h-full">
                    <div className="relative w-full max-w-[360px]">
                        <div className="relative overflow-hidden bg-auth-primary rounded-[20px] shadow-xl p-4 md:p-5 border border-slate-800/50">
                            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent pointer-events-none"></div>
                            <div className="relative z-10 flex flex-col gap-4">
                                <div className="text-center space-y-1">
                                    <div className="mx-auto w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center mb-2 backdrop-blur-sm">
                                        <span className="material-symbols-outlined text-white text-lg">lock_open</span>
                                    </div>
                                    <h1 className="text-lg md:text-xl font-bold font-outfit text-white tracking-tight">Welcome Back</h1>
                                    <p className="text-teal-200/70 text-xs font-normal font-display">Enter your credentials</p>
                                </div>

                                {error && (
                                    <div className="bg-red-500/10 border border-red-500/50 text-red-200 px-4 py-2 rounded-lg text-sm text-center">
                                        {error}
                                    </div>
                                )}

                                <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
                                    <div className="group">
                                        <label className="block text-teal-100/80 text-xs font-medium mb-1 pl-3" htmlFor="email">Email</label>
                                        <div className="relative">
                                            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-teal-400/60 z-10 text-base">mail</span>
                                            <input
                                                autoComplete="email"
                                                className="glass-input w-full rounded-xl py-2 pl-9 pr-4 text-white placeholder-teal-500/50 focus:outline-none focus:ring-2 focus:ring-teal-400/50 transition-all duration-200 font-medium font-display text-sm"
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
                                        <div className="flex justify-between items-center mb-1 px-3">
                                            <label className="block text-teal-100/80 text-xs font-medium" htmlFor="password">Password</label>
                                            <a className="text-xs text-teal-300 hover:text-white transition-colors" href="/auth/forgot-password">Forgot?</a>
                                        </div>
                                        <div className="relative">
                                            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-teal-400/60 z-10 text-base">key</span>
                                            <input
                                                className="glass-input w-full rounded-xl py-2 pl-9 pr-8 text-white placeholder-teal-500/50 focus:outline-none focus:ring-2 focus:ring-teal-400/50 transition-all duration-200 font-medium font-display text-sm"
                                                id="password"
                                                placeholder="Enter password"
                                                type="password"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                required
                                            />
                                            <button className="absolute right-3 top-1/2 -translate-y-1/2 text-teal-400/60 hover:text-white transition-colors cursor-pointer" type="button">
                                                <span className="material-symbols-outlined text-base">visibility</span>
                                            </button>
                                        </div>
                                    </div>
                                    <button
                                        className="clay-button-primary w-full bg-white text-auth-primary text-sm font-bold py-2 rounded-xl hover:bg-slate-100 focus:ring-2 focus:ring-white/30 outline-none flex items-center justify-center gap-1 cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed"
                                        type="submit"
                                        disabled={loading}
                                    >
                                        <span>{loading ? 'Logging in...' : 'Login'}</span>
                                        {!loading && <span className="material-symbols-outlined text-base font-bold">arrow_forward</span>}
                                    </button>
                                    <div className="relative py-1 flex items-center gap-3">
                                        <div className="h-px bg-white/10 flex-1"></div>
                                        <span className="text-teal-200/40 text-xs uppercase tracking-wider font-medium">Or</span>
                                        <div className="h-px bg-white/10 flex-1"></div>
                                    </div>
                                    <button
                                        className="glass-button-secondary w-full py-2 rounded-xl flex items-center justify-center gap-2 text-white font-medium hover:bg-white/10 focus:ring-2 focus:ring-white/20 outline-none group cursor-pointer text-xs"
                                        type="button"
                                        onClick={handleGoogleSignIn}
                                    >
                                        <svg className="w-4 h-4 group-hover:scale-110 transition-transform duration-200" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"></path>
                                            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"></path>
                                            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"></path>
                                            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"></path>
                                        </svg>
                                        Continue with Google
                                    </button>
                                </form>
                                <div className="text-center mt-1">
                                    <p className="text-teal-200/60 text-xs">
                                        Don't have an account?
                                        <a className="text-white font-bold hover:underline decoration-2 underline-offset-4 ml-1" href="/auth/signup">Sign up</a>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="lg:hidden mt-4 text-center text-slate-400 text-xs pb-4">
                        <p>© 2024 Pikar AI Inc.</p>
                    </div>
                </section>
            </main>
        </div>
    );
}
