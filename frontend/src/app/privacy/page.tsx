import React from "react";
import Link from "next/link";
import Footer from "../components/Footer";
import { Brain, ArrowLeft, Shield, Eye, Lock, Database, Cookie, Mail } from "lucide-react";
import ScrollToTop from "@/components/ui/ScrollToTop";

export default function PrivacyPolicyPage() {
    const lastUpdated = "February 10, 2026";
    
    return (
        <div className="bg-[#f8fcfc] bg-dot-pattern bg-fixed text-slate-800 font-sans antialiased selection:bg-primary/30 min-h-screen flex flex-col">
            <div className="fixed inset-0 z-0 bg-dots pointer-events-none opacity-60"></div>

            {/* Navbar */}
            <header className="sticky top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-100">
                <nav className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
                            <Brain className="h-5 w-5 text-white" />
                        </div>
                        <span className="text-xl font-bold tracking-tight text-slate-900">
                            Pikar <span className="text-[#1a8a6e]">AI</span>
                        </span>
                    </Link>
                    <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-[#1a8a6e] hover:text-[#0d6b4f] transition-colors">
                        <ArrowLeft className="w-4 h-4" />
                        Back to Home
                    </Link>
                </nav>
            </header>

            <main className="relative z-10 flex-grow">
                {/* Hero Section */}
                <div className="bg-gradient-to-br from-slate-50 to-white border-b border-slate-100">
                    <div className="mx-auto max-w-4xl px-6 py-16 md:py-24">
                        <div className="text-center space-y-6">
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#1a8a6e]/10 text-[#1a8a6e] text-sm font-semibold border border-[#1a8a6e]/20">
                                <Shield className="w-4 h-4" />
                                Last updated: {lastUpdated}
                            </div>
                            <h1 className="text-4xl md:text-5xl lg:text-6xl font-black tracking-tight text-slate-900 leading-tight">
                                Privacy Policy
                            </h1>
                            <p className="text-slate-600 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
                                Transparent. Secure. Your data, protected. We believe in clear communication about how we handle your information at Pikar AI.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="mx-auto max-w-4xl px-6 py-12 md:py-16">
                    <div className="space-y-12">
                        
                        {/* Introduction */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <p className="text-lg md:text-xl leading-relaxed text-slate-700">
                                At Pikar AI, we are committed to protecting your privacy. This policy outlines how we collect, use, and safeguard your personal information when you use our AI-powered services. We treat your data with the same care and respect that we would expect for our own.
                            </p>
                        </section>

                        {/* Information We Collect */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-[#1a8a6e]/10 text-[#1a8a6e] shrink-0">
                                    <Database className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">1. Information We Collect</h2>
                            </div>
                            
                            <div className="space-y-6">
                                <div className="p-6 bg-slate-50 rounded-xl border border-slate-100">
                                    <h3 className="text-lg font-bold text-slate-900 mb-4">Personal Information</h3>
                                    <p className="text-slate-600 mb-4 leading-relaxed">
                                        When you register for Pikar AI, we collect information that personally identifies you to provide a tailored experience:
                                    </p>
                                    <div className="grid md:grid-cols-2 gap-4">
                                        <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-100">
                                            <Eye className="w-5 h-5 text-[#1a8a6e] shrink-0 mt-0.5" />
                                            <div>
                                                <h4 className="font-semibold text-slate-800 text-sm">Identity Data</h4>
                                                <p className="text-xs text-slate-600 mt-1">Full name, username, and profile preferences.</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-100">
                                            <Mail className="w-5 h-5 text-[#1a8a6e] shrink-0 mt-0.5" />
                                            <div>
                                                <h4 className="font-semibold text-slate-800 text-sm">Contact Data</h4>
                                                <p className="text-xs text-slate-600 mt-1">Email address, billing address, and telephone number.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="pl-6 border-l-2 border-[#1a8a6e]/30 py-2">
                                    <h3 className="text-lg font-bold text-slate-900 mb-3">Usage Data</h3>
                                    <p className="text-slate-600 leading-relaxed">
                                        We also collect information on how the Service is accessed and used. This Usage Data may include information such as your computer&apos;s Internet Protocol address (e.g. IP address), browser type, browser version, the pages of our Service that you visit, the time and date of your visit, the time spent on those pages, unique device identifiers and other diagnostic data.
                                    </p>
                                </div>
                            </div>
                        </section>

                        {/* How We Use Your Data */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-[#1a8a6e]/10 text-[#1a8a6e] shrink-0">
                                    <Lock className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">2. How We Use Your Data</h2>
                            </div>
                            
                            <p className="text-slate-600 mb-8 leading-relaxed">
                                Pikar AI uses the collected data for various purposes to provide and maintain our Service. We prioritize transparency in our operations:
                            </p>
                            
                            <div className="grid md:grid-cols-2 gap-6">
                                <div className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                                    <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center mb-4 text-blue-600">
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                                    </div>
                                    <h4 className="font-bold text-slate-900 mb-2">Service Provision</h4>
                                    <p className="text-sm text-slate-600 leading-relaxed">To provide and maintain our Service, including to monitor the usage of our Service.</p>
                                </div>
                                <div className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                                    <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center mb-4 text-purple-600">
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
                                    </div>
                                    <h4 className="font-bold text-slate-900 mb-2">Communication</h4>
                                    <p className="text-sm text-slate-600 leading-relaxed">To contact you regarding updates, security alerts, and administrative messages.</p>
                                </div>
                                <div className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                                    <div className="w-12 h-12 rounded-xl bg-teal-50 flex items-center justify-center mb-4 text-teal-600">
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                                    </div>
                                    <h4 className="font-bold text-slate-900 mb-2">Improvement</h4>
                                    <p className="text-sm text-slate-600 leading-relaxed">To provide analysis or valuable information so that we can improve the Service.</p>
                                </div>
                                <div className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                                    <div className="w-12 h-12 rounded-xl bg-orange-50 flex items-center justify-center mb-4 text-orange-600">
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                                    </div>
                                    <h4 className="font-bold text-slate-900 mb-2">Security</h4>
                                    <p className="text-sm text-slate-600 leading-relaxed">To detect, prevent and address technical issues and unauthorized access.</p>
                                </div>
                            </div>
                        </section>

                        {/* Your Data Rights */}
                        <section className="bg-gradient-to-br from-[#1a8a6e]/5 to-[#1a8a6e]/10 rounded-2xl p-8 md:p-10 border border-[#1a8a6e]/20">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-[#1a8a6e] text-white shrink-0">
                                    <Shield className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">3. Your Data Rights</h2>
                            </div>
                            
                            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/50 mb-6">
                                <h3 className="text-lg font-bold text-slate-900 mb-3 flex items-center gap-2">
                                    GDPR &amp; CCPA Compliance
                                </h3>
                                <p className="text-slate-600 leading-relaxed">
                                    We respect your privacy rights and provide you with reasonable access to the Personal Data that you may have provided through your use of the Services. Your principal rights under data protection law are:
                                </p>
                            </div>
                            
                            <div className="grid md:grid-cols-2 gap-4">
                                <div className="flex items-center gap-4 p-4 bg-white/80 backdrop-blur-sm rounded-xl border border-white/50">
                                    <Eye className="w-5 h-5 text-[#1a8a6e]" />
                                    <span className="font-semibold text-slate-900">Right to Access</span>
                                </div>
                                <div className="flex items-center gap-4 p-4 bg-white/80 backdrop-blur-sm rounded-xl border border-white/50">
                                    <svg className="w-5 h-5 text-[#1a8a6e]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                                    <span className="font-semibold text-slate-900">Right to Rectification</span>
                                </div>
                                <div className="flex items-center gap-4 p-4 bg-white/80 backdrop-blur-sm rounded-xl border border-white/50">
                                    <svg className="w-5 h-5 text-[#1a8a6e]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                    <span className="font-semibold text-slate-900">Right to Erasure</span>
                                </div>
                                <div className="flex items-center gap-4 p-4 bg-white/80 backdrop-blur-sm rounded-xl border border-white/50">
                                    <svg className="w-5 h-5 text-[#1a8a6e]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" /></svg>
                                    <span className="font-semibold text-slate-900">Right to Restrict</span>
                                </div>
                            </div>
                        </section>

                        {/* Cookie Policy */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-center gap-4 mb-6">
                                <div className="p-3 rounded-xl bg-amber-50 text-amber-600 shrink-0">
                                    <Cookie className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">4. Cookie Policy</h2>
                            </div>
                            
                            <div className="space-y-4 text-slate-600 leading-relaxed">
                                <p>
                                    We use cookies and similar tracking technologies to track the activity on our Service and hold certain information. Cookies are files with small amount of data which may include an anonymous unique identifier.
                                </p>
                                <p>
                                    You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent. However, if you do not accept cookies, you may not be able to use some portions of our Service.
                                </p>
                            </div>
                        </section>

                        {/* Data Retention */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">5</span>
                                Data Retention
                            </h2>
                            <div className="space-y-4 text-slate-600 leading-relaxed">
                                <p>
                                    We will retain your Personal Data only for as long as is necessary for the purposes set out in this Privacy Policy. We will retain and use your Personal Data to the extent necessary to comply with our legal obligations, resolve disputes, and enforce our legal agreements and policies.
                                </p>
                                <p>
                                    We will also retain Usage Data for internal analysis purposes. Usage Data is generally retained for a shorter period of time, except when this data is used to strengthen the security or to improve the functionality of our Service.
                                </p>
                            </div>
                        </section>

                        {/* Contact & Related Policies */}
                        <section className="bg-slate-900 text-white rounded-2xl p-8 md:p-10 shadow-lg relative overflow-hidden">
                            <div className="absolute inset-0 bg-gradient-to-br from-slate-800 to-slate-900 z-0"></div>
                            <div className="absolute -top-20 -right-20 w-64 h-64 bg-[#1a8a6e]/20 rounded-full blur-3xl"></div>
                            <div className="relative z-10">
                                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                                    <div>
                                        <h2 className="text-2xl font-bold text-white mb-2">Still have questions?</h2>
                                        <p className="text-slate-400">Our Data Protection Officer is available to assist you.</p>
                                    </div>
                                    <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
                                        <a 
                                            href="mailto:privacy@pikar.ai" 
                                            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-[#1a8a6e] text-white font-semibold rounded-xl hover:bg-[#0d6b4f] transition-colors"
                                        >
                                            <Mail className="w-4 h-4" />
                                            privacy@pikar.ai
                                        </a>
                                        <Link 
                                            href="/terms" 
                                            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-colors"
                                        >
                                            View Terms of Service
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        </section>
                    </div>
                </div>
            </main>

            <Footer />
            <ScrollToTop />
        </div>
    );
}
