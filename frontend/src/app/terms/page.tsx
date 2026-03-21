import type { Metadata } from "next";
import React from "react";
import Link from "next/link";
import Footer from "../components/Footer";
import { Brain, ArrowLeft, FileText, Shield } from "lucide-react";
import ScrollToTop from "@/components/ui/ScrollToTop";

export const metadata: Metadata = {
  title: "Terms of Service | Pikar AI",
  description: "The terms and conditions governing your use of the Pikar AI platform. Read before using our services.",
  alternates: { canonical: "https://pikar.ai/terms" },
  robots: { index: true, follow: false },
};

export default function TermsOfServicePage() {
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
                                <FileText className="w-4 h-4" />
                                Last updated: {lastUpdated}
                            </div>
                            <h1 className="text-4xl md:text-5xl lg:text-6xl font-black tracking-tight text-slate-900 leading-tight">
                                Terms of Service
                            </h1>
                            <p className="text-slate-600 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
                                Please read these terms carefully. By using Pikar AI, you agree to the rules that govern our relationship with you.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="mx-auto max-w-4xl px-6 py-12 md:py-16">
                    <div className="space-y-12">
                        
                        {/* Introduction */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-start gap-4 mb-6">
                                <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600 shrink-0">
                                    <FileText className="w-6 h-6" />
                                </div>
                                <div>
                                    <h2 className="text-2xl font-bold text-slate-900 mb-3">Introduction</h2>
                                    <p className="text-slate-600 leading-relaxed">
                                        Welcome to Pikar AI. By accessing our website and using our services, you acknowledge that you have read, understood, and agree to be bound by the following Terms of Service. If you do not agree with any part of these terms, you must discontinue use of our services immediately.
                                    </p>
                                </div>
                            </div>
                        </section>

                        {/* Definitions */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">1</span>
                                Definitions
                            </h2>
                            <div className="space-y-4">
                                <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
                                    <div className="min-w-[140px]">
                                        <span className="font-bold text-slate-800">Account</span>
                                    </div>
                                    <p className="text-slate-600 text-sm leading-relaxed">
                                        Means a unique account created for You to access our Service or parts of our Service.
                                    </p>
                                </div>
                                <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
                                    <div className="min-w-[140px]">
                                        <span className="font-bold text-slate-800">Company</span>
                                    </div>
                                    <p className="text-slate-600 text-sm leading-relaxed">
                                        Refers to Pikar AI (&quot;We&quot;, &quot;Us&quot; or &quot;Our&quot;).
                                    </p>
                                </div>
                                <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
                                    <div className="min-w-[140px]">
                                        <span className="font-bold text-slate-800">Content</span>
                                    </div>
                                    <p className="text-slate-600 text-sm leading-relaxed">
                                        Refers to content such as text, images, or other information that can be posted, uploaded, linked to or otherwise made available by You, regardless of the form of that content.
                                    </p>
                                </div>
                                <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
                                    <div className="min-w-[140px]">
                                        <span className="font-bold text-slate-800">Service</span>
                                    </div>
                                    <p className="text-slate-600 text-sm leading-relaxed">
                                        Refers to the Pikar AI platform, including our website, applications, and all related services.
                                    </p>
                                </div>
                            </div>
                        </section>

                        {/* User Obligations */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">2</span>
                                User Obligations
                            </h2>
                            <p className="text-slate-600 mb-6 leading-relaxed">
                                As a user of the Pikar AI platform, you agree to uphold certain standards of conduct. Failure to adhere to these obligations may result in the termination of your account.
                            </p>
                            <div className="grid md:grid-cols-2 gap-4">
                                <div className="p-5 rounded-xl bg-green-50 border border-green-100 flex gap-3 items-start">
                                    <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center shrink-0 mt-0.5">
                                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                                    </div>
                                    <div>
                                        <strong className="block text-slate-800 text-sm mb-1">Authentic Information</strong>
                                        <p className="text-xs text-slate-600">Provide accurate, current, and complete information during registration.</p>
                                    </div>
                                </div>
                                <div className="p-5 rounded-xl bg-green-50 border border-green-100 flex gap-3 items-start">
                                    <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center shrink-0 mt-0.5">
                                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                                    </div>
                                    <div>
                                        <strong className="block text-slate-800 text-sm mb-1">Account Security</strong>
                                        <p className="text-xs text-slate-600">Maintain the security of your password and accept all risks of unauthorized access.</p>
                                    </div>
                                </div>
                                <div className="p-5 rounded-xl bg-red-50 border border-red-100 flex gap-3 items-start">
                                    <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center shrink-0 mt-0.5">
                                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                                    </div>
                                    <div>
                                        <strong className="block text-slate-800 text-sm mb-1">No Illegal Use</strong>
                                        <p className="text-xs text-slate-600">Do not use the Service for any illegal or unauthorized purpose.</p>
                                    </div>
                                </div>
                                <div className="p-5 rounded-xl bg-red-50 border border-red-100 flex gap-3 items-start">
                                    <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center shrink-0 mt-0.5">
                                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                                    </div>
                                    <div>
                                        <strong className="block text-slate-800 text-sm mb-1">No Reverse Engineering</strong>
                                        <p className="text-xs text-slate-600">Do not attempt to reverse engineer any aspect of the Service.</p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Subscription & Payment */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">3</span>
                                Subscription &amp; Payment
                            </h2>
                            <div className="space-y-4 text-slate-600 leading-relaxed">
                                <p>
                                    Some parts of the Service are billed on a subscription basis. You will be billed in advance on a recurring and periodic basis. Billing cycles are set either on a monthly or annual basis, depending on the type of subscription plan you select when purchasing a Subscription.
                                </p>
                                <ul className="space-y-3 mt-4">
                                    <li className="flex items-start gap-3">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#1a8a6e] mt-2 shrink-0"></span>
                                        <span>At the end of each Billing Cycle, your Subscription will automatically renew under the exact same conditions unless you cancel it or Pikar AI cancels it.</span>
                                    </li>
                                    <li className="flex items-start gap-3">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#1a8a6e] mt-2 shrink-0"></span>
                                        <span>You may cancel your Subscription renewal either through your online account management page or by contacting our customer support team.</span>
                                    </li>
                                    <li className="flex items-start gap-3">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#1a8a6e] mt-2 shrink-0"></span>
                                        <span>Refunds are processed according to our refund policy. Please review your subscription terms for specific details.</span>
                                    </li>
                                </ul>
                            </div>
                        </section>

                        {/* Limitation of Liability */}
                        <section className="bg-slate-900 text-white rounded-2xl p-8 md:p-10 shadow-lg relative overflow-hidden">
                            <div className="absolute inset-0 bg-gradient-to-br from-slate-800 to-slate-900 z-0"></div>
                            <div className="relative z-10">
                                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                                    <span className="flex items-center justify-center w-8 h-8 rounded-full bg-white/10 text-white text-sm font-bold">4</span>
                                    Limitation of Liability
                                </h2>
                                <p className="text-slate-300 leading-relaxed mb-6">
                                    In no event shall Pikar AI, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from:
                                </p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                    <div className="flex items-start gap-3 text-slate-300">
                                        <Shield className="w-5 h-5 text-[#1a8a6e] shrink-0 mt-0.5" />
                                        <span>Your access to or use of or inability to access or use the Service.</span>
                                    </div>
                                    <div className="flex items-start gap-3 text-slate-300">
                                        <Shield className="w-5 h-5 text-[#1a8a6e] shrink-0 mt-0.5" />
                                        <span>Any conduct or content of any third party on the Service.</span>
                                    </div>
                                    <div className="flex items-start gap-3 text-slate-300">
                                        <Shield className="w-5 h-5 text-[#1a8a6e] shrink-0 mt-0.5" />
                                        <span>Any content obtained from the Service.</span>
                                    </div>
                                    <div className="flex items-start gap-3 text-slate-300">
                                        <Shield className="w-5 h-5 text-[#1a8a6e] shrink-0 mt-0.5" />
                                        <span>Unauthorized access, use or alteration of your transmissions or content.</span>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Intellectual Property */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">5</span>
                                Intellectual Property
                            </h2>
                            <div className="space-y-4 text-slate-600 leading-relaxed">
                                <p>
                                    The Service and its original content, features and functionality are and will remain the exclusive property of Pikar AI and its licensors. The Service is protected by copyright, trademark, and other laws.
                                </p>
                                <p>
                                    You retain ownership of any content you create or upload to the Service. By using our Service, you grant us a license to use, store, and process your content solely for the purpose of providing the Service to you.
                                </p>
                            </div>
                        </section>

                        {/* Termination */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">6</span>
                                Termination
                            </h2>
                            <div className="space-y-4 text-slate-600 leading-relaxed">
                                <p>
                                    We may terminate or suspend your account and bar access to the Service immediately, without prior notice or liability, under our sole discretion, for any reason whatsoever and without limitation, including but not limited to a breach of the Terms.
                                </p>
                                <p>
                                    If you wish to terminate your account, you may simply discontinue using the Service or contact us to request account deletion.
                                </p>
                            </div>
                        </section>

                        {/* Age Restriction */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">7</span>
                                Eligibility &amp; Age Restriction
                            </h2>
                            <div className="space-y-4 text-slate-600 leading-relaxed">
                                <p>
                                    The Service is intended solely for users who are 18 years of age or older. By accessing or using the Service, you represent and warrant that you are at least 18 years old and have the legal capacity to enter into a binding agreement.
                                </p>
                                <p>
                                    If you are between 16 and 18 years of age and located in the European Union, you may only use the Service with verifiable consent from a parent or legal guardian. We do not knowingly collect personal data from anyone under 16. If we learn that personal data of a user under 16 has been collected without appropriate consent, we will delete it promptly.
                                </p>
                            </div>
                        </section>

                        {/* Governing Law */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">8</span>
                                Governing Law &amp; Dispute Resolution
                            </h2>
                            <div className="space-y-4 text-slate-600 leading-relaxed">
                                <p>
                                    These Terms shall be governed by and construed in accordance with the laws of the State of California, United States, without regard to its conflict of law provisions.
                                </p>
                                <p>
                                    Any dispute arising from or relating to these Terms or the Service shall first be attempted to be resolved through good-faith negotiation. If unresolved within 30 days, disputes shall be submitted to binding arbitration in San Francisco, California, under the rules of the American Arbitration Association. Notwithstanding the foregoing, either party may seek injunctive or other equitable relief in any court of competent jurisdiction.
                                </p>
                                <p>
                                    If any provision of these Terms is found to be unenforceable or invalid, that provision will be limited or eliminated to the minimum extent necessary so that the Terms will otherwise remain in full force and effect.
                                </p>
                            </div>
                        </section>

                        {/* Contact & Related Policies */}
                        <section className="bg-gradient-to-br from-[#1a8a6e]/5 to-[#1a8a6e]/10 rounded-2xl p-8 md:p-10 border border-[#1a8a6e]/20">
                            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                                <div>
                                    <h2 className="text-2xl font-bold text-slate-900 mb-2">Have Questions?</h2>
                                    <p className="text-slate-600">Our team is here to help clarify any aspect of our Terms of Service.</p>
                                </div>
                                <div className="flex flex-col sm:flex-row gap-3">
                                    <a 
                                        href="mailto:legal@pikar.ai" 
                                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-[#1a8a6e] text-white font-semibold rounded-xl hover:bg-[#0d6b4f] transition-colors"
                                    >
                                        Contact Legal Team
                                    </a>
                                    <Link 
                                        href="/privacy" 
                                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white text-slate-700 font-semibold rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors"
                                    >
                                        View Privacy Policy
                                    </Link>
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
