"use client";

import React from "react";
import Link from "next/link";
import Footer from "../components/Footer";
import { Brain } from "lucide-react";

export default function TermsOfServicePage() {
    return (
        <div className="bg-[#f6f8f8] bg-dot-pattern bg-fixed text-slate-800 font-sans antialiased selection:bg-primary/30 min-h-screen flex flex-col">
            <div className="fixed inset-0 z-0 bg-dots pointer-events-none opacity-60"></div>

            {/* Navbar - Consistent with Privacy Policy */}
            <header className="sticky top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-100">
                <nav className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
                            <Brain className="h-5 w-5 text-white" />
                        </div>
                        <span className="text-xl font-bold tracking-tight text-slate-900">
                            Pikar <span className="text-primary">AI</span>
                        </span>
                    </Link>
                    <Link href="/" className="text-sm font-semibold text-primary hover:text-primary-dark transition-colors">
                        Back to Home
                    </Link>
                </nav>
            </header>

            <main className="relative z-10 flex-grow flex flex-col items-center py-20 px-4 sm:px-6">
                <div className="w-full max-w-[840px] flex flex-col gap-10">
                    <div className="text-center space-y-4 py-6">
                        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 text-primary-dark text-sm font-semibold border border-primary/20">
                            <span className="material-symbols-outlined text-[18px]">history</span>
                            Last updated: October 24, 2023
                        </div>
                        <h1 className="text-slate-900 text-5xl md:text-6xl font-black tracking-tight leading-[1.1]" style={{ fontFamily: 'var(--font-display)' }}>
                            Terms of Service
                        </h1>
                        <p className="text-slate-500 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
                            Please read these terms carefully. By using Pikar AI, you’re agreeing to the rules that govern our relationship with you.
                        </p>
                    </div>

                    <section className="clay-card p-8 md:p-12">
                        <div className="flex items-start gap-4 mb-6">
                            <div className="p-3 rounded-2xl bg-indigo-50 text-indigo-600">
                                <span className="material-symbols-outlined text-3xl">gavel</span>
                            </div>
                            <div>
                                <h3 className="text-2xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'var(--font-display)' }}>Introduction</h3>
                                <p className="text-slate-600 leading-relaxed text-base">
                                    Welcome to Pikar AI. By accessing our website and using our services, you acknowledge that you have read, understood, and agree to be bound by the following Terms of Service. If you do not agree with any part of these terms, you must discontinue use of our services immediately.
                                </p>
                            </div>
                        </div>
                    </section>

                    <section className="clay-card p-8 md:p-12 relative overflow-hidden group">
                        <div className="absolute -top-20 -right-20 w-40 h-40 bg-primary/10 rounded-full blur-3xl pointer-events-none group-hover:bg-primary/20 transition-all duration-500"></div>
                        <h3 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3" style={{ fontFamily: 'var(--font-display)' }}>
                            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-500 text-sm">1</span>
                            Definitions
                        </h3>
                        <div className="space-y-6">
                            <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100/50">
                                <div className="min-w-[120px]">
                                    <span className="font-bold text-slate-800">Account</span>
                                </div>
                                <p className="text-slate-600 text-sm leading-relaxed">
                                    Means a unique account created for You to access our Service or parts of our Service.
                                </p>
                            </div>
                            <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100/50">
                                <div className="min-w-[120px]">
                                    <span className="font-bold text-slate-800">Company</span>
                                </div>
                                <p className="text-slate-600 text-sm leading-relaxed">
                                    Refers to Pikar AI, located at 123 Innovation Drive, Tech City (&quot;We&quot;, &quot;Us&quot; or &quot;Our&quot;).
                                </p>
                            </div>
                            <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100/50">
                                <div className="min-w-[120px]">
                                    <span className="font-bold text-slate-800">Content</span>
                                </div>
                                <p className="text-slate-600 text-sm leading-relaxed">
                                    Refers to content such as text, images, or other information that can be posted, uploaded, linked to or otherwise made available by You, regardless of the form of that content.
                                </p>
                            </div>
                        </div>
                    </section>

                    <section className="clay-card p-8 md:p-12">
                        <h3 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3" style={{ fontFamily: 'var(--font-display)' }}>
                            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-500 text-sm">2</span>
                            User Obligations
                        </h3>
                        <p className="text-slate-600 mb-6 leading-relaxed">
                            As a user of the Pikar AI platform, you agree to uphold certain standards of conduct. Failure to adhere to these obligations may result in the termination of your account.
                        </p>
                        <div className="grid md:grid-cols-2 gap-4">
                            <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex gap-3 items-start">
                                <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                                <div>
                                    <strong className="block text-slate-800 text-sm mb-1">Authentic Info</strong>
                                    <p className="text-xs text-slate-500">Provide accurate, current, and complete information during registration.</p>
                                </div>
                            </div>
                            <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex gap-3 items-start">
                                <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                                <div>
                                    <strong className="block text-slate-800 text-sm mb-1">Security</strong>
                                    <p className="text-xs text-slate-500">Maintain the security of your password and accept all risks of unauthorized access.</p>
                                </div>
                            </div>
                            <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex gap-3 items-start">
                                <span className="material-symbols-outlined text-red-400 mt-0.5">cancel</span>
                                <div>
                                    <strong className="block text-slate-800 text-sm mb-1">No Illegal Use</strong>
                                    <p className="text-xs text-slate-500">Do not use the Service for any illegal or unauthorized purpose.</p>
                                </div>
                            </div>
                            <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex gap-3 items-start">
                                <span className="material-symbols-outlined text-red-400 mt-0.5">cancel</span>
                                <div>
                                    <strong className="block text-slate-800 text-sm mb-1">No Reverse Eng.</strong>
                                    <p className="text-xs text-slate-500">Do not attempt to reverse engineer any aspect of the Service.</p>
                                </div>
                            </div>
                        </div>
                    </section>

                    <section className="clay-card p-8 md:p-12">
                        <h3 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3" style={{ fontFamily: 'var(--font-display)' }}>
                            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-500 text-sm">3</span>
                            Subscription &amp; Payment
                        </h3>
                        <div className="prose prose-slate prose-p:text-slate-600 max-w-none">
                            <p className="mb-4">
                                Some parts of the Service are billed on a subscription basis (&quot;Subscription(s)&quot;). You will be billed in advance on a recurring and periodic basis (&quot;Billing Cycle&quot;). Billing cycles are set either on a monthly or annual basis, depending on the type of subscription plan you select when purchasing a Subscription.
                            </p>
                            <ul className="list-none pl-0 space-y-3">
                                <li className="flex items-start gap-3">
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 shrink-0"></span>
                                    <span>At the end of each Billing Cycle, your Subscription will automatically renew under the exact same conditions unless you cancel it or Pikar AI cancels it.</span>
                                </li>
                                <li className="flex items-start gap-3">
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 shrink-0"></span>
                                    <span>You may cancel your Subscription renewal either through your online account management page or by contacting Pikar AI customer support team.</span>
                                </li>
                            </ul>
                        </div>
                    </section>

                    <section className="clay-card p-8 md:p-12 bg-slate-900 text-white relative overflow-hidden">
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-slate-800 to-slate-900 z-0"></div>
                        <div className="relative z-10">
                            <h3 className="text-2xl font-bold text-white mb-6 flex items-center gap-3" style={{ fontFamily: 'var(--font-display)' }}>
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-white/10 text-white text-sm">4</span>
                                Limitation of Liability
                            </h3>
                            <p className="text-slate-300 leading-relaxed mb-6">
                                In no event shall Pikar AI, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from:
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                <div className="flex items-start gap-3 text-slate-300">
                                    <span className="material-symbols-outlined text-primary text-lg">warning</span>
                                    <span>Your access to or use of or inability to access or use the Service.</span>
                                </div>
                                <div className="flex items-start gap-3 text-slate-300">
                                    <span className="material-symbols-outlined text-primary text-lg">warning</span>
                                    <span>Any conduct or content of any third party on the Service.</span>
                                </div>
                                <div className="flex items-start gap-3 text-slate-300">
                                    <span className="material-symbols-outlined text-primary text-lg">warning</span>
                                    <span>Any content obtained from the Service.</span>
                                </div>
                                <div className="flex items-start gap-3 text-slate-300">
                                    <span className="material-symbols-outlined text-primary text-lg">warning</span>
                                    <span>Unauthorized access, use or alteration of your transmissions or content.</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    <section className="clay-card p-8 md:p-12 flex flex-col items-center text-center">
                        <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-6">
                            <span className="material-symbols-outlined text-3xl">mail</span>
                        </div>
                        <h3 className="text-2xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'var(--font-display)' }}>Still have questions?</h3>
                        <p className="text-slate-600 mb-6">Our legal team is here to help clarify any aspect of our Terms of Service.</p>
                        <a className="inline-flex items-center gap-2 text-primary font-bold hover:text-primary-dark transition-colors border-b-2 border-primary/20 hover:border-primary pb-0.5" href="mailto:legal@pikar.ai">
                            legal@pikar.ai
                            <span className="material-symbols-outlined text-sm">arrow_outward</span>
                        </a>
                    </section>
                </div>
            </main>

            <Footer />

            <button
                aria-label="Back to top"
                className="glass-button fixed bottom-8 right-8 z-50 p-3 rounded-full text-primary hover:text-primary-dark transition-all hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-primary/50 group"
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            >
                <span className="material-symbols-outlined text-2xl group-hover:scale-110 transition-transform">arrow_upward</span>
            </button>
        </div>
    );
}
