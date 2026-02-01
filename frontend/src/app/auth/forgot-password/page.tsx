"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import styles from './styles.module.css';
import { resetPasswordForEmail } from '@/services/auth';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
      await resetPasswordForEmail(email);
      setMessage({ type: 'success', text: 'Password reset link sent! Check your email.' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to send reset link.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <style jsx global>{`
                @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
                .font-manrope { font-family: 'Manrope', sans-serif; }
            `}</style>

      <div className={`font-manrope antialiased text-gray-900 bg-[#f8f9fa] min-h-screen relative flex items-center justify-center overflow-hidden`}>
        <div className={`absolute inset-0 bg-dot-grid opacity-100 z-0 ${styles.bgDotGrid}`}></div>
        <div className={styles.textureOverlay}></div>
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-white rounded-full blur-3xl opacity-80"></div>
        <div className="absolute bottom-[-20%] right-[-10%] w-[700px] h-[700px] bg-gray-200/40 rounded-full blur-3xl"></div>

        <main className="relative z-20 w-full max-w-md px-4">
          <div className={`${styles.clayCard} bg-[#0d2d2d] rounded-[2rem] p-8 md:p-12 w-full mx-auto relative overflow-hidden group border border-white/5`}>
            <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent opacity-50 pointer-events-none"></div>
            <div className="relative z-10 flex flex-col items-center text-center">
              <div className="mb-8 p-3 rounded-2xl bg-white/5 backdrop-blur-sm shadow-inner ring-1 ring-white/10">
                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                  <path clipRule="evenodd" d="M39.475 21.6262C40.358 21.4363 40.6863 21.5589 40.7581 21.5934C40.7876 21.655 40.8547 21.857 40.8082 22.3336C40.7408 23.0255 40.4502 24.0046 39.8572 25.2301C38.6799 27.6631 36.5085 30.6631 33.5858 33.5858C30.6631 36.5085 27.6632 38.6799 25.2301 39.8572C24.0046 40.4502 23.0255 40.7407 22.3336 40.8082C21.8571 40.8547 21.6551 40.7875 21.5934 40.7581C21.5589 40.6863 21.4363 40.358 21.6262 39.475C21.8562 38.4054 22.4689 36.9657 23.5038 35.2817C24.7575 33.2417 26.5497 30.9744 28.7621 28.762C30.9744 26.5497 33.2417 24.7574 35.2817 23.5037C36.9657 22.4689 38.4054 21.8562 39.475 21.6262ZM4.41189 29.2403L18.7597 43.5881C19.8813 44.7097 21.4027 44.9179 22.7217 44.7893C24.0585 44.659 25.5148 44.1631 26.9723 43.4579C29.9052 42.0387 33.2618 39.5667 36.4142 36.4142C39.5667 33.2618 42.0387 29.9052 43.4579 26.9723C44.1631 25.5148 44.659 24.0585 44.7893 22.7217C44.9179 21.4027 44.7097 19.8813 43.5881 18.7597L29.2403 4.41187C27.8527 3.02428 25.8765 3.02573 24.2861 3.36776C22.6081 3.72863 20.7334 4.58419 18.8396 5.74801C16.4978 7.18716 13.9881 9.18353 11.5858 11.5858C9.18354 13.988 7.18717 16.4978 5.74802 18.8396C4.58421 20.7334 3.72865 22.6081 3.36778 24.2861C3.02574 25.8765 3.02429 27.8527 4.41189 29.2403Z" fill="currentColor" fillRule="evenodd"></path>
                </svg>
              </div>
              <h2 className="text-white text-3xl font-bold tracking-tight mb-3 drop-shadow-md">
                Forgot Password?
              </h2>
              <p className="text-gray-300 text-sm font-medium leading-relaxed mb-10 max-w-[280px]">
                Enter your email to receive a recovery link.
              </p>

              {message && (
                <div className={`mb-6 p-4 rounded-xl text-sm font-medium w-full ${message.type === 'success' ? 'bg-green-500/10 text-green-200 border border-green-500/20' : 'bg-red-500/10 text-red-200 border border-red-500/20'}`}>
                  {message.text}
                </div>
              )}

              <form onSubmit={handleSubmit} className="w-full flex flex-col gap-6">
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                    <span className="material-symbols-outlined text-gray-400">mail</span>
                  </div>
                  <input
                    className={`${styles.glassInput} w-full h-14 pl-12 pr-6 rounded-full text-white placeholder-gray-400 focus:outline-none text-base font-medium transition-all duration-300`}
                    id="email"
                    name="email"
                    placeholder="name@example.com"
                    required
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                  />
                </div>
                <button
                  className={`${styles.puffyButton} w-full h-14 rounded-full flex items-center justify-center gap-2 group/btn mt-2 disabled:opacity-70 disabled:cursor-not-allowed`}
                  type="submit"
                  disabled={isLoading}
                >
                  <span className="text-[#0d2b2b] text-base font-bold tracking-wide">
                    {isLoading ? 'Sending...' : 'Send Reset Link'}
                  </span>
                  {!isLoading && (
                    <span className="material-symbols-outlined text-[#0d2b2b] text-sm transition-transform duration-300 group-hover/btn:translate-x-1">arrow_forward</span>
                  )}
                </button>
              </form>
              <div className="mt-8 pt-4 border-t border-white/5 w-full">
                <Link href="/auth/login" className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors duration-200 text-sm font-semibold group/link">
                  <span className="material-symbols-outlined text-sm transition-transform duration-200 group-hover/link:-translate-x-1">arrow_back</span>
                  Back to Login
                </Link>
              </div>
            </div>
          </div>
          <p className="text-center mt-8 text-gray-400 text-xs font-medium">
            © {new Date().getFullYear()} Pikar AI. Secure Authentication.
          </p>
        </main>
      </div>
    </>
  );
}
