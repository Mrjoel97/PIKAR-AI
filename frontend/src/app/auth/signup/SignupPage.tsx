'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signUp, signInWithGoogle } from '../../../services/auth';
import Link from 'next/link';

export default function SignupPage() {
    const router = useRouter();
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

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
            // SignUp might require email confirmation depending on Supabase settings.
            // But typically we can redirect or show a 'check email' message.
            if (data) {
                // You might want to update user profile with fullName here using another service call if Supabase auth metadata supports it or a separate profile table
                router.push('/onboarding/welcome');
            }
        } catch (err: any) {
            setError(err.message || 'Failed to sign up');
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
        <div className="bg-clay-white h-screen font-display flex overflow-hidden selection:bg-teal-500 selection:text-white">
            <div className="flex flex-col lg:flex-row w-full h-full overflow-hidden">
                <div className="hidden lg:flex w-1/2 relative bg-white items-center justify-center p-4 overflow-hidden">
                    <div className="absolute inset-0 z-0 bg-bold-grid bg-[length:30px_30px] opacity-[0.3]"></div>
                    <div className="relative z-10 max-w-md flex flex-col gap-4">
                        <div className="space-y-1">
                            <h1 className="font-heading font-extrabold text-2xl text-slate-900 leading-tight">
                                Join the <br />
                                <span className="text-teal-900">AI Revolution</span>
                            </h1>
                            <p className="text-slate-600 text-sm font-medium leading-relaxed">
                                Next-gen AI interfaces. Fast, secure, beautiful.
                            </p>
                        </div>
                        <div className="grid grid-cols-1 gap-2 mt-1">
                            <div className="flex items-center gap-3 group">
                                <div className="clay-icon-wrapper w-9 h-9">
                                    <span className="material-symbols-outlined text-teal-700 text-lg">rocket_launch</span>
                                </div>
                                <div>
                                    <h3 className="font-heading font-bold text-sm text-slate-800">Lightning Speed</h3>
                                    <p className="text-slate-500 text-xs">Processing power that keeps up.</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 group">
                                <div className="clay-icon-wrapper w-9 h-9">
                                    <span className="material-symbols-outlined text-teal-700 text-lg">psychology</span>
                                </div>
                                <div>
                                    <h3 className="font-heading font-bold text-sm text-slate-800">Deep Intelligence</h3>
                                    <p className="text-slate-500 text-xs">Adaptive learning algorithms.</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 group">
                                <div className="clay-icon-wrapper w-9 h-9">
                                    <span className="material-symbols-outlined text-teal-700 text-lg">shield_lock</span>
                                </div>
                                <div>
                                    <h3 className="font-heading font-bold text-sm text-slate-800">Bank-Grade Security</h3>
                                    <p className="text-slate-500 text-xs">Encrypted and protected.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="w-full lg:w-1/2 bg-clay-white relative flex items-center justify-center p-3 md:p-4">
                    <div className="absolute inset-0 z-0 opacity-[0.3] bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] bg-[length:20px_20px] pointer-events-none"></div>
                    <div className="relative z-10 card-deep-teal w-full max-w-[360px] rounded-[20px] p-4 md:p-5 flex flex-col gap-3">
                        <div className="flex flex-col items-center gap-1 text-center">
                            <div className="size-8 rounded-lg bg-white/10 backdrop-blur-md flex items-center justify-center shadow-inner border border-white/10 mb-1">
                                <span className="material-symbols-outlined text-white text-lg">auto_awesome</span>
                            </div>
                            <h1 className="font-heading font-bold text-lg md:text-xl text-white tracking-wide">
                                Create Account
                            </h1>
                            <p className="text-white/60 text-xs font-medium">
                                Join Pikar AI
                            </p>
                        </div>

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/50 text-red-200 px-3 py-1.5 rounded-lg text-xs text-center">
                                {error}
                            </div>
                        )}

                        <form className="flex flex-col gap-2 w-full" onSubmit={handleSubmit}>
                            <div className="input-liquid rounded-lg overflow-hidden group">
                                <label className="flex items-center px-3 h-9 w-full cursor-text">
                                    <span className="material-symbols-outlined text-white/40 group-focus-within:text-white/80 transition-colors mr-2 text-sm">person</span>
                                    <input
                                        className="bg-transparent border-none w-full text-white placeholder-white/30 focus:ring-0 p-0 text-xs font-medium h-full focus:outline-none"
                                        placeholder="Full Name"
                                        type="text"
                                        value={fullName}
                                        onChange={(e) => setFullName(e.target.value)}
                                        required
                                    />
                                </label>
                            </div>
                            <div className="input-liquid rounded-lg overflow-hidden group">
                                <label className="flex items-center px-3 h-9 w-full cursor-text">
                                    <span className="material-symbols-outlined text-white/40 group-focus-within:text-white/80 transition-colors mr-2 text-sm">mail</span>
                                    <input
                                        className="bg-transparent border-none w-full text-white placeholder-white/30 focus:ring-0 p-0 text-xs font-medium h-full focus:outline-none"
                                        placeholder="Email"
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                    />
                                </label>
                            </div>
                            <div className="input-liquid rounded-lg overflow-hidden group">
                                <label className="flex items-center px-3 h-9 w-full cursor-text">
                                    <span className="material-symbols-outlined text-white/40 group-focus-within:text-white/80 transition-colors mr-2 text-sm">lock</span>
                                    <input
                                        className="bg-transparent border-none w-full text-white placeholder-white/30 focus:ring-0 p-0 text-xs font-medium h-full focus:outline-none"
                                        placeholder="Password"
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                    />
                                    <button className="text-white/40 hover:text-white transition-colors focus:outline-none flex items-center justify-center p-1 cursor-pointer" type="button">
                                        <span className="material-symbols-outlined text-base">visibility</span>
                                    </button>
                                </label>
                            </div>
                            <div className="input-liquid rounded-lg overflow-hidden group">
                                <label className="flex items-center px-3 h-9 w-full cursor-text">
                                    <span className="material-symbols-outlined text-white/40 group-focus-within:text-white/80 transition-colors mr-2 text-sm">verified_user</span>
                                    <input
                                        className="bg-transparent border-none w-full text-white placeholder-white/30 focus:ring-0 p-0 text-xs font-medium h-full focus:outline-none"
                                        placeholder="Confirm Password"
                                        type="password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        required
                                    />
                                </label>
                            </div>
                            <button
                                className="mt-1 w-full h-9 bg-white text-primary font-bold text-sm rounded-lg shadow-puffy-btn hover:shadow-puffy-btn-hover hover:scale-[0.99] active:scale-[0.97] transition-all duration-200 flex items-center justify-center gap-1 cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed"
                                type="submit"
                                disabled={loading}
                            >
                                {loading ? 'Creating...' : 'Create Account'}
                                {!loading && <span className="material-symbols-outlined text-base font-bold">arrow_forward</span>}
                            </button>
                            <div className="flex items-center gap-3 py-1">
                                <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                                <span className="text-white/40 text-xs uppercase tracking-widest font-bold">Or</span>
                                <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                            </div>
                            <button
                                className="w-full h-9 bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-sm rounded-lg text-white font-medium text-xs transition-all duration-200 flex items-center justify-center gap-2 group cursor-pointer"
                                type="button"
                                onClick={handleGoogleSignIn}
                            >
                                <svg className="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"></path>
                                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"></path>
                                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"></path>
                                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"></path>
                                </svg>
                                Continue with Google
                            </button>
                        </form>
                        <div className="text-center pt-1">
                            <p className="text-white/50 text-xs">
                                Already have an account?
                                <Link className="text-[#4fd1c5] hover:text-[#81e6d9] font-semibold transition-colors ml-1 decoration-skip-ink hover:underline" href="/auth/login">
                                    Login
                                </Link>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
