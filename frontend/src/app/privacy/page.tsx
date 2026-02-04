"use client";

import React from "react";
import Link from "next/link";
import Footer from "../components/Footer";
import { Brain } from "lucide-react";

export default function PrivacyPolicyPage() {
    return (
        <div className="bg-[#f8fcfc] bg-dot-grid bg-fixed text-[#0d1b1b] font-sans antialiased selection:bg-primary/30 min-h-screen flex flex-col">
            {/* Navbar - Simplified for subpages */}
            <header className="sticky top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
                <nav className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
                            <Brain className="h-5 w-5 text-white" />
                        </div>
                        <span className="text-xl font-bold tracking-tight text-[#0d1b1b]">
                            Pikar <span className="text-[#1a8a6e]">AI</span>
                        </span>
                    </Link>
                    <Link href="/" className="text-sm font-semibold text-[#4c9a9a] hover:text-[#0d1b1b] transition-colors">
                        Back to Home
                    </Link>
                </nav>
            </header>

            <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 flex-grow">
                <div className="mb-12 md:mb-20 flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="max-w-2xl">
                        <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-xs font-bold text-[#0ea5a5] mb-6 border border-gray-100 shadow-sm">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#13ecec] opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#13ecec]"></span>
                            </span>
                            Last Updated: October 24, 2023
                        </div>
                        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-[#0d1b1b] leading-[1.1]" style={{ fontFamily: 'var(--font-display)' }}>
                            Privacy Policy
                        </h1>
                        <p className="mt-6 text-lg text-[#4c9a9a] max-w-xl leading-relaxed">
                            Transparent. Secure. Your data, protected. We believe in clear communication about how we handle your information at Pikar AI.
                        </p>
                    </div>
                    <button className="group flex items-center gap-2 rounded-2xl bg-white px-6 py-3 text-sm font-bold text-[#0d1b1b] shadow-[4px_4px_10px_rgba(0,0,0,0.05),-4px_-4px_10px_#ffffff] hover:shadow-[6px_6px_14px_rgba(0,0,0,0.08),-6px_-6px_14px_#ffffff] transition-all border border-gray-50 active:scale-95">
                        <span className="material-symbols-outlined text-[#0ea5a5] group-hover:scale-110 transition-transform">download</span>
                        Download PDF
                    </button>
                </div>

                <div className="relative grid grid-cols-1 gap-12 lg:grid-cols-12 lg:gap-16">
                    <aside className="hidden lg:block lg:col-span-3">
                        <div className="sticky top-24 space-y-8">
                            <div className="glass-panel rounded-2xl p-4 shadow-lg shadow-gray-200/50 bg-white/60 backdrop-blur-md border border-white/60">
                                <h3 className="mb-3 px-3 text-xs font-bold uppercase tracking-wider text-[#4c9a9a]/80" style={{ fontFamily: 'var(--font-display)' }}>Contents</h3>
                                <nav className="flex flex-col gap-1 space-y-1">
                                    <a className="flex items-center justify-between rounded-xl bg-[#13ecec]/10 px-4 py-3 text-sm font-bold text-[#0d1b1b] transition-all border-l-4 border-[#13ecec]" href="#introduction">
                                        Introduction
                                        <span className="material-symbols-outlined text-[16px] text-[#0ea5a5]">arrow_forward</span>
                                    </a>
                                    <a className="group flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-[#4c9a9a] hover:bg-white hover:text-[#0d1b1b] transition-all hover:shadow-sm" href="#collection">
                                        Data Collection
                                    </a>
                                    <a className="group flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-[#4c9a9a] hover:bg-white hover:text-[#0d1b1b] transition-all hover:shadow-sm" href="#usage">
                                        How We Use Data
                                    </a>
                                    <a className="group flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-[#4c9a9a] hover:bg-white hover:text-[#0d1b1b] transition-all hover:shadow-sm" href="#rights">
                                        Your Rights
                                    </a>
                                    <a className="group flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-[#4c9a9a] hover:bg-white hover:text-[#0d1b1b] transition-all hover:shadow-sm" href="#cookies">
                                        Cookie Policy
                                    </a>
                                    <a className="group flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-[#4c9a9a] hover:bg-white hover:text-[#0d1b1b] transition-all hover:shadow-sm" href="#contact">
                                        Contact Us
                                    </a>
                                </nav>
                            </div>
                            <div className="rounded-3xl bg-[#102222] p-6 text-white shadow-2xl shadow-[#13ecec]/20 relative overflow-hidden group border border-gray-800">
                                <div className="absolute -top-10 -right-10 w-32 h-32 bg-[#13ecec]/20 rounded-full blur-3xl group-hover:bg-[#13ecec]/40 transition-all duration-700"></div>
                                <div className="size-10 rounded-full bg-white/10 flex items-center justify-center mb-4 backdrop-blur-md">
                                    <span className="material-symbols-outlined text-[#13ecec]">support_agent</span>
                                </div>
                                <h4 className="font-bold text-lg mb-1 relative z-10" style={{ fontFamily: 'var(--font-display)' }}>Have questions?</h4>
                                <p className="text-gray-400 text-sm mb-4 relative z-10 leading-relaxed">Our legal team is here to help clarify any concerns you might have.</p>
                                <a className="inline-flex items-center text-[#13ecec] text-sm font-bold hover:text-white transition-colors relative z-10 group/link" href="#contact">
                                    Get in touch <span className="material-symbols-outlined text-sm ml-1 group-hover/link:translate-x-1 transition-transform">arrow_outward</span>
                                </a>
                            </div>
                        </div>
                    </aside>
                    <div className="lg:col-span-9">
                        <div className="space-y-16">
                            <section className="scroll-mt-32" id="introduction">
                                <p className="text-xl md:text-2xl leading-relaxed text-[#0d1b1b] font-medium drop-shadow-sm">
                                    At Pikar AI, we are committed to protecting your privacy. This policy outlines how we collect, use, and safeguard your personal information when you use our AI-powered services. We treat your data with the same care and respect that we would expect for our own.
                                </p>
                            </section>
                            <section className="scroll-mt-32" id="collection">
                                <div className="flex items-center gap-4 mb-8">
                                    <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm text-[#0ea5a5] border border-gray-100">
                                        <span className="material-symbols-outlined">dataset</span>
                                    </span>
                                    <h2 className="text-2xl md:text-3xl font-bold text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>1. Information We Collect</h2>
                                </div>
                                <div className="clay-card p-8 md:p-10 mb-8 relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 w-64 h-64 bg-[#13ecec]/5 rounded-bl-full -mr-16 -mt-16 transition-transform group-hover:scale-110"></div>
                                    <h3 className="text-xl font-bold mb-4 text-[#0d1b1b] relative z-10" style={{ fontFamily: 'var(--font-display)' }}>Personal Information</h3>
                                    <p className="text-[#4c9a9a] mb-6 leading-relaxed relative z-10 text-lg">
                                        When you register for Pikar AI, we collect information that personally identifies you to provide a tailored experience:
                                    </p>
                                    <div className="grid md:grid-cols-1 gap-4 relative z-10">
                                        <div className="flex items-start gap-4 p-4 rounded-xl bg-[#f8fcfc] border border-gray-100">
                                            <div className="mt-1">
                                                <span className="material-symbols-outlined text-[#0ea5a5]">badge</span>
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-[#0d1b1b] text-sm">Identity Data</h4>
                                                <p className="text-sm text-[#4c9a9a] mt-1">Full name, username, and profile preferences.</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-4 p-4 rounded-xl bg-[#f8fcfc] border border-gray-100">
                                            <div className="mt-1">
                                                <span className="material-symbols-outlined text-[#0ea5a5]">alternate_email</span>
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-[#0d1b1b] text-sm">Contact Data</h4>
                                                <p className="text-sm text-[#4c9a9a] mt-1">Email address, billing address, and telephone number.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="pl-6 border-l-2 border-[#13ecec]/30 py-2">
                                    <h3 className="text-lg font-bold mb-3 text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>Usage Data</h3>
                                    <p className="text-[#4c9a9a] leading-relaxed text-base md:text-lg">
                                        We also collect information on how the Service is accessed and used (&quot;Usage Data&quot;). This Usage Data may include information such as your computer&apos;s Internet Protocol address (e.g. IP address), browser type, browser version, the pages of our Service that you visit, the time and date of your visit, the time spent on those pages, unique device identifiers and other diagnostic data.
                                    </p>
                                </div>
                            </section>
                            <section className="scroll-mt-32" id="usage">
                                <div className="flex items-center gap-4 mb-8">
                                    <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm text-[#0ea5a5] border border-gray-100">
                                        <span className="material-symbols-outlined">settings_suggest</span>
                                    </span>
                                    <h2 className="text-2xl md:text-3xl font-bold text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>2. How We Use Your Data</h2>
                                </div>
                                <p className="text-[#4c9a9a] mb-8 leading-relaxed text-lg">
                                    Pikar AI uses the collected data for various purposes to provide and maintain our Service. We prioritize transparency in our operations:
                                </p>
                                <div className="grid md:grid-cols-2 gap-6">
                                    <div className="rounded-3xl bg-white p-7 border border-gray-50 shadow-[0px_4px_20px_rgba(0,0,0,0.02)] hover:shadow-[0px_8px_30px_rgba(0,0,0,0.04)] transition-all group">
                                        <div className="bg-blue-50 w-12 h-12 rounded-2xl flex items-center justify-center mb-5 text-blue-600 group-hover:scale-110 transition-transform duration-300">
                                            <span className="material-symbols-outlined">bolt</span>
                                        </div>
                                        <h4 className="font-bold text-[#0d1b1b] text-lg mb-2" style={{ fontFamily: 'var(--font-display)' }}>Service Provision</h4>
                                        <p className="text-base text-[#4c9a9a] leading-relaxed">To provide and maintain our Service, including to monitor the usage of our Service.</p>
                                    </div>
                                    <div className="rounded-3xl bg-white p-7 border border-gray-50 shadow-[0px_4px_20px_rgba(0,0,0,0.02)] hover:shadow-[0px_8px_30px_rgba(0,0,0,0.04)] transition-all group">
                                        <div className="bg-purple-50 w-12 h-12 rounded-2xl flex items-center justify-center mb-5 text-purple-600 group-hover:scale-110 transition-transform duration-300">
                                            <span className="material-symbols-outlined">campaign</span>
                                        </div>
                                        <h4 className="font-bold text-[#0d1b1b] text-lg mb-2" style={{ fontFamily: 'var(--font-display)' }}>Communication</h4>
                                        <p className="text-base text-[#4c9a9a] leading-relaxed">To contact you regarding updates, security alerts, and administrative messages.</p>
                                    </div>
                                    <div className="rounded-3xl bg-white p-7 border border-gray-50 shadow-[0px_4px_20px_rgba(0,0,0,0.02)] hover:shadow-[0px_8px_30px_rgba(0,0,0,0.04)] transition-all group">
                                        <div className="bg-teal-50 w-12 h-12 rounded-2xl flex items-center justify-center mb-5 text-teal-600 group-hover:scale-110 transition-transform duration-300">
                                            <span className="material-symbols-outlined">analytics</span>
                                        </div>
                                        <h4 className="font-bold text-[#0d1b1b] text-lg mb-2" style={{ fontFamily: 'var(--font-display)' }}>Improvement</h4>
                                        <p className="text-base text-[#4c9a9a] leading-relaxed">To provide analysis or valuable information so that we can improve the Service.</p>
                                    </div>
                                    <div className="rounded-3xl bg-white p-7 border border-gray-50 shadow-[0px_4px_20px_rgba(0,0,0,0.02)] hover:shadow-[0px_8px_30px_rgba(0,0,0,0.04)] transition-all group">
                                        <div className="bg-orange-50 w-12 h-12 rounded-2xl flex items-center justify-center mb-5 text-orange-600 group-hover:scale-110 transition-transform duration-300">
                                            <span className="material-symbols-outlined">security</span>
                                        </div>
                                        <h4 className="font-bold text-[#0d1b1b] text-lg mb-2" style={{ fontFamily: 'var(--font-display)' }}>Security</h4>
                                        <p className="text-base text-[#4c9a9a] leading-relaxed">To detect, prevent and address technical issues and unauthorized access.</p>
                                    </div>
                                </div>
                            </section>
                            <section className="scroll-mt-32" id="rights">
                                <div className="flex items-center gap-4 mb-8">
                                    <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm text-[#0ea5a5] border border-gray-100">
                                        <span className="material-symbols-outlined">gavel</span>
                                    </span>
                                    <h2 className="text-2xl md:text-3xl font-bold text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>3. Your Data Rights</h2>
                                </div>
                                <div className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-[#e0f7f7] to-[#f0fdfd] p-8 md:p-10 shadow-[inset_0_2px_4px_rgba(255,255,255,0.8),0_10px_30px_rgba(19,236,236,0.15)] border border-white">
                                    <div className="absolute top-0 right-0 -mt-20 -mr-20 h-80 w-80 rounded-full bg-[#13ecec]/20 blur-[80px]"></div>
                                    <div className="relative z-10">
                                        <h3 className="text-xl font-bold text-[#0d1b1b] mb-4 flex items-center gap-2" style={{ fontFamily: 'var(--font-display)' }}>
                                            <span className="material-symbols-outlined text-[#0ea5a5]">verified_user</span>
                                            GDPR &amp; CCPA Compliance
                                        </h3>
                                        <p className="text-[#0d1b1b]/80 mb-8 max-w-2xl leading-relaxed text-lg">
                                            We respect your privacy rights and provide you with reasonable access to the Personal Data that you may have provided through your use of the Services. Your principal rights under data protection law are:
                                        </p>
                                        <div className="grid gap-4 md:grid-cols-2">
                                            <div className="flex items-center gap-4 rounded-2xl bg-white/70 backdrop-blur-md p-5 shadow-sm border border-white/50 hover:bg-white transition-colors cursor-default">
                                                <span className="material-symbols-outlined text-[#0ea5a5] bg-[#13ecec]/10 p-2 rounded-lg">visibility</span>
                                                <span className="font-bold text-base text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>Right to Access</span>
                                            </div>
                                            <div className="flex items-center gap-4 rounded-2xl bg-white/70 backdrop-blur-md p-5 shadow-sm border border-white/50 hover:bg-white transition-colors cursor-default">
                                                <span className="material-symbols-outlined text-[#0ea5a5] bg-[#13ecec]/10 p-2 rounded-lg">edit</span>
                                                <span className="font-bold text-base text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>Right to Rectification</span>
                                            </div>
                                            <div className="flex items-center gap-4 rounded-2xl bg-white/70 backdrop-blur-md p-5 shadow-sm border border-white/50 hover:bg-white transition-colors cursor-default">
                                                <span className="material-symbols-outlined text-[#0ea5a5] bg-[#13ecec]/10 p-2 rounded-lg">delete</span>
                                                <span className="font-bold text-base text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>Right to Erasure</span>
                                            </div>
                                            <div className="flex items-center gap-4 rounded-2xl bg-white/70 backdrop-blur-md p-5 shadow-sm border border-white/50 hover:bg-white transition-colors cursor-default">
                                                <span className="material-symbols-outlined text-[#0ea5a5] bg-[#13ecec]/10 p-2 rounded-lg">block</span>
                                                <span className="font-bold text-base text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>Right to Restrict</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </section>
                            <section className="scroll-mt-32" id="cookies">
                                <div className="flex items-center gap-4 mb-8">
                                    <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm text-[#0ea5a5] border border-gray-100">
                                        <span className="material-symbols-outlined">cookie</span>
                                    </span>
                                    <h2 className="text-2xl md:text-3xl font-bold text-[#0d1b1b]" style={{ fontFamily: 'var(--font-display)' }}>4. Cookie Policy</h2>
                                </div>
                                <div className="bg-white rounded-3xl p-8 border border-gray-100 shadow-sm">
                                    <p className="text-[#4c9a9a] leading-relaxed mb-6 text-lg">
                                        We use cookies and similar tracking technologies to track the activity on our Service and hold certain information. Cookies are files with small amount of data which may include an anonymous unique identifier.
                                    </p>
                                    <p className="text-[#4c9a9a] leading-relaxed text-lg">
                                        You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent. However, if you do not accept cookies, you may not be able to use some portions of our Service.
                                    </p>
                                </div>
                            </section>
                            <section className="scroll-mt-32 pb-20 border-t border-gray-200 pt-16" id="contact">
                                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8 bg-gray-50 rounded-3xl p-8 md:p-12">
                                    <div>
                                        <h2 className="text-2xl font-bold text-[#0d1b1b] mb-2" style={{ fontFamily: 'var(--font-display)' }}>Still have questions?</h2>
                                        <p className="text-[#4c9a9a] text-lg">Our Data Protection Officer is available to assist you.</p>
                                    </div>
                                    <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
                                        <a className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0d1b1b] px-8 py-4 text-base font-bold text-white shadow-lg hover:bg-gray-800 transition-colors w-full sm:w-auto" href="mailto:privacy@pikar.ai">
                                            <span className="material-symbols-outlined text-[20px]">mail</span>
                                            privacy@pikar.ai
                                        </a>
                                        <a className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-8 py-4 text-base font-bold text-[#0d1b1b] shadow-md border border-gray-200 hover:bg-gray-50 transition-colors w-full sm:w-auto" href="#">
                                            Help Center
                                        </a>
                                    </div>
                                </div>
                            </section>
                        </div>
                    </div>
                </div>
            </main>
            <Footer />
        </div>
    );
}
