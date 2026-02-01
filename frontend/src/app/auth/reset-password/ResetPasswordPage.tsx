'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { updateUser } from '../../../services/auth';
import Link from 'next/link';

export default function ResetPasswordPage() {
    const router = useRouter();
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (newPassword !== confirmPassword) {
            setError("Passwords don't match");
            return;
        }

        if (newPassword.length < 6) {
            setError("Password must be at least 6 characters");
            return;
        }

        setLoading(true);
        try {
            await updateUser({ password: newPassword });
            setSuccess(true);
            setTimeout(() => router.push('/auth/login'), 2000);
        } catch (err: any) {
            setError(err.message || 'Failed to update password');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="font-display bg-[#f6f8f8] text-slate-800 antialiased selection:bg-teal-500 selection:text-white">
            <div className="relative min-h-screen w-full flex flex-col items-center justify-center p-6 overflow-hidden">
                {/* Background Texture */}
                <div className="absolute inset-0 z-0 opacity-40 bg-dot-grid pointer-events-none"></div>
                {/* Ambient decorative blurs */}
                <div className="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] bg-teal-200/20 rounded-full blur-[120px] pointer-events-none"></div>
                <div className="absolute bottom-[10%] right-[5%] w-[40%] h-[40%] bg-blue-200/20 rounded-full blur-[100px] pointer-events-none"></div>

                {/* Main Content Wrapper */}
                <main className="relative z-10 w-full max-w-[480px]">
                    {/* Logo */}
                    <div className="mb-8 flex justify-center">
                        <div className="flex items-center gap-3 text-[#0d2b2b]">
                            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-[#0d2b2b] text-white shadow-lg">
                                <span className="material-symbols-outlined text-2xl">auto_awesome</span>
                            </div>
                            <span className="text-2xl font-bold tracking-tight">Pikar AI</span>
                        </div>
                    </div>

                    {/* The Dark Clay Card */}
                    <div className="card-deep-teal rounded-3xl p-8 sm:p-10 w-full relative overflow-hidden">
                        {/* Card Header */}
                        <div className="text-center mb-8 relative z-10">
                            <h1 className="text-3xl font-bold text-white mb-2 tracking-wide">Reset Password</h1>
                            <p className="text-teal-200/70 text-sm font-medium leading-relaxed">
                                Enter your new password below to secure your account.
                            </p>
                        </div>

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/50 text-red-200 px-4 py-2 rounded-lg text-sm text-center mb-6 relative z-10">
                                {error}
                            </div>
                        )}

                        {success && (
                            <div className="bg-green-500/10 border border-green-500/50 text-green-200 px-4 py-2 rounded-lg text-sm text-center mb-6 relative z-10">
                                Password updated successfully! Redirecting...
                            </div>
                        )}

                        {/* Form */}
                        <form className="space-y-6 relative z-10" onSubmit={handleSubmit}>
                            {/* New Password Input */}
                            <div className="group">
                                <label className="block text-teal-100/90 text-sm font-semibold mb-2 ml-1" htmlFor="new-password">
                                    New Password
                                </label>
                                <div className="relative flex items-center">
                                    <input
                                        className="input-liquid w-full rounded-2xl px-5 py-4 text-white placeholder-teal-400/30 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-300 h-14"
                                        id="new-password"
                                        placeholder="••••••••"
                                        type="password"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        required
                                    />
                                    <button className="absolute right-4 text-teal-400/60 hover:text-teal-200 transition-colors cursor-pointer" type="button">
                                        <span className="material-symbols-outlined text-[20px]">visibility_off</span>
                                    </button>
                                </div>
                                {/* Strength Meter */}
                                <div className="flex gap-1 mt-2 px-1">
                                    <div className={`h-1 flex-1 rounded-full ${newPassword.length >= 2 ? 'bg-teal-600/50' : 'bg-teal-800/30'}`}></div>
                                    <div className={`h-1 flex-1 rounded-full ${newPassword.length >= 4 ? 'bg-teal-600/50' : 'bg-teal-800/30'}`}></div>
                                    <div className={`h-1 flex-1 rounded-full ${newPassword.length >= 6 ? 'bg-teal-600/50' : 'bg-teal-800/30'}`}></div>
                                    <div className={`h-1 flex-1 rounded-full ${newPassword.length >= 8 ? 'bg-teal-600/50' : 'bg-teal-800/30'}`}></div>
                                </div>
                            </div>

                            {/* Confirm Password Input */}
                            <div className="group">
                                <label className="block text-teal-100/90 text-sm font-semibold mb-2 ml-1" htmlFor="confirm-password">
                                    Confirm Password
                                </label>
                                <div className="relative flex items-center">
                                    <input
                                        className="input-liquid w-full rounded-2xl px-5 py-4 text-white placeholder-teal-400/30 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-transparent transition-all duration-300 h-14"
                                        id="confirm-password"
                                        placeholder="••••••••"
                                        type="password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        required
                                    />
                                    <button className="absolute right-4 text-teal-400/60 hover:text-teal-200 transition-colors cursor-pointer" type="button">
                                        <span className="material-symbols-outlined text-[20px]">visibility_off</span>
                                    </button>
                                </div>
                            </div>

                            {/* Action Button */}
                            <div className="pt-2">
                                <button
                                    className="w-full shadow-puffy-btn bg-white rounded-2xl h-14 flex items-center justify-center gap-2 group/btn relative overflow-hidden cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed"
                                    type="submit"
                                    disabled={loading || success}
                                >
                                    <span className="text-[#0d2b2b] font-bold text-lg tracking-wide z-10 group-hover/btn:scale-105 transition-transform">
                                        {loading ? 'Updating...' : 'Update Password'}
                                    </span>
                                    {!loading && <span className="material-symbols-outlined text-[#0d2b2b] z-10 transition-transform group-hover/btn:translate-x-1 text-[20px]">arrow_forward</span>}
                                    {/* Subtle shine effect on hover */}
                                    <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/50 to-transparent opacity-0 group-hover/btn:opacity-100 transition-opacity duration-500 transform -translate-x-full group-hover/btn:translate-x-full pointer-events-none"></div>
                                </button>
                            </div>
                        </form>

                        {/* Footer Link */}
                        <div className="mt-8 text-center relative z-10">
                            <Link className="inline-flex items-center gap-1.5 text-sm text-teal-200/60 hover:text-white transition-colors font-medium group/link" href="/auth/login">
                                <span className="material-symbols-outlined text-[16px] transition-transform group-hover/link:-translate-x-0.5">arrow_back</span>
                                Back to Login
                            </Link>
                        </div>

                        {/* Abstract decorative glow inside card */}
                        <div className="absolute top-0 right-0 w-64 h-64 bg-teal-500/10 rounded-full blur-[60px] pointer-events-none translate-x-1/2 -translate-y-1/2"></div>
                        <div className="absolute bottom-0 left-0 w-48 h-48 bg-teal-300/5 rounded-full blur-[40px] pointer-events-none -translate-x-1/3 translate-y-1/3"></div>
                    </div>

                    {/* Bottom Helper Text */}
                    <p className="text-center text-slate-400 text-xs mt-8 font-medium">
                        © 2024 Pikar AI. Secure Authentication.
                    </p>
                </main>
            </div>
        </div>
    );
}
