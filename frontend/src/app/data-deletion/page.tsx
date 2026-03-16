import React from "react";
import Link from "next/link";
import Footer from "../components/Footer";
import { Brain, ArrowLeft, Trash2, Shield, Mail, Settings, Database, Clock } from "lucide-react";
import ScrollToTop from "@/components/ui/ScrollToTop";

export default function DataDeletionPage() {
    const lastUpdated = "March 16, 2026";

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
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-rose-50 text-rose-600 text-sm font-semibold border border-rose-200">
                                <Trash2 className="w-4 h-4" />
                                Last updated: {lastUpdated}
                            </div>
                            <h1 className="text-4xl md:text-5xl lg:text-6xl font-black tracking-tight text-slate-900 leading-tight">
                                Data Deletion
                            </h1>
                            <p className="text-slate-600 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
                                You have the right to request the deletion of your personal data. Here&apos;s how to exercise that right with Pikar AI.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="mx-auto max-w-4xl px-6 py-12 md:py-16">
                    <div className="space-y-12">

                        {/* What Data We Store */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-[#1a8a6e]/10 text-[#1a8a6e] shrink-0">
                                    <Database className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">1. What Data We Store</h2>
                            </div>

                            <p className="text-slate-600 mb-6 leading-relaxed">
                                When you use Pikar AI, we store the following categories of data associated with your account:
                            </p>

                            <div className="grid md:grid-cols-2 gap-4">
                                {[
                                    { title: "Profile Information", desc: "Name, email address, and account preferences." },
                                    { title: "Business Data", desc: "Initiatives, workflows, campaigns, and financial records you create." },
                                    { title: "Connected Accounts", desc: "OAuth tokens for social media platforms (Facebook, Twitter, etc.)." },
                                    { title: "AI Interactions", desc: "Chat sessions, brain dumps, and agent-generated content." },
                                    { title: "Documents & Media", desc: "Uploaded files, generated reports, and media assets." },
                                    { title: "Usage Analytics", desc: "Activity logs, page views, and feature usage patterns." },
                                ].map((item) => (
                                    <div key={item.title} className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl border border-slate-100">
                                        <div className="w-2 h-2 rounded-full bg-[#1a8a6e] mt-2 shrink-0" />
                                        <div>
                                            <h4 className="font-semibold text-slate-800 text-sm">{item.title}</h4>
                                            <p className="text-xs text-slate-600 mt-1">{item.desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        {/* How to Request Deletion */}
                        <section className="bg-gradient-to-br from-[#1a8a6e]/5 to-[#1a8a6e]/10 rounded-2xl p-8 md:p-10 border border-[#1a8a6e]/20">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-[#1a8a6e] text-white shrink-0">
                                    <Shield className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">2. How to Request Deletion</h2>
                            </div>

                            <p className="text-slate-600 mb-8 leading-relaxed">
                                You can request the deletion of all your data using either of these methods:
                            </p>

                            <div className="space-y-6">
                                {/* Option A: Self-service */}
                                <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/50">
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#1a8a6e]/10 text-[#1a8a6e]">
                                            <Settings className="w-4 h-4" />
                                        </div>
                                        <h3 className="text-lg font-bold text-slate-900">Option A: Delete from Account Settings</h3>
                                    </div>
                                    <ol className="list-decimal list-inside space-y-2 text-slate-600 ml-11 text-sm leading-relaxed">
                                        <li>Log in to your Pikar AI account.</li>
                                        <li>Navigate to <strong>Settings</strong> from the sidebar.</li>
                                        <li>Scroll down to the <strong>Danger Zone</strong> section.</li>
                                        <li>Click <strong>&quot;Delete My Account&quot;</strong> and type <code className="bg-slate-100 px-1.5 py-0.5 rounded text-rose-600 font-mono text-xs">DELETE</code> to confirm.</li>
                                        <li>Your account and all data will be permanently removed immediately.</li>
                                    </ol>
                                </div>

                                {/* Option B: Email */}
                                <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/50">
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#1a8a6e]/10 text-[#1a8a6e]">
                                            <Mail className="w-4 h-4" />
                                        </div>
                                        <h3 className="text-lg font-bold text-slate-900">Option B: Email Our Privacy Team</h3>
                                    </div>
                                    <div className="ml-11 text-sm text-slate-600 leading-relaxed">
                                        <p className="mb-3">
                                            Send an email to{" "}
                                            <a href="mailto:privacy@pikar.ai" className="text-[#1a8a6e] font-semibold underline underline-offset-2 hover:text-[#0d6b4f]">
                                                privacy@pikar.ai
                                            </a>{" "}
                                            with the subject line <strong>&quot;Data Deletion Request&quot;</strong>. Include:
                                        </p>
                                        <ul className="list-disc list-inside space-y-1 text-slate-500">
                                            <li>The email address associated with your account</li>
                                            <li>Your full name (for identity verification)</li>
                                        </ul>
                                        <p className="mt-3 text-slate-500">
                                            We will process your request and confirm deletion within 7 business days.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* What Happens After Deletion */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-amber-50 text-amber-600 shrink-0">
                                    <Clock className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">3. What Happens After Deletion</h2>
                            </div>

                            <div className="space-y-4 text-slate-600 leading-relaxed">
                                <p>
                                    When your account is deleted, the following actions are taken <strong>immediately</strong>:
                                </p>
                                <ul className="space-y-3">
                                    {[
                                        "All personal profile data (name, email, preferences) is permanently removed.",
                                        "All business data (initiatives, workflows, campaigns, financial records) is permanently deleted.",
                                        "All connected social media accounts are disconnected and OAuth tokens are destroyed.",
                                        "All uploaded documents, media assets, and generated content are permanently removed.",
                                        "All AI interaction history (chat sessions, agent outputs) is permanently erased.",
                                        "Your authentication record is deleted from our identity system.",
                                    ].map((item) => (
                                        <li key={item} className="flex items-start gap-3">
                                            <Trash2 className="w-4 h-4 text-rose-400 mt-1 shrink-0" />
                                            <span className="text-sm">{item}</span>
                                        </li>
                                    ))}
                                </ul>
                                <div className="mt-6 p-4 bg-amber-50 rounded-xl border border-amber-200">
                                    <p className="text-sm text-amber-800">
                                        <strong>Important:</strong> Account deletion is permanent and cannot be undone.
                                        We may retain anonymized, non-personal data for aggregate analytics and legal compliance
                                        as required by applicable law.
                                    </p>
                                </div>
                            </div>
                        </section>

                        {/* Contact / CTA */}
                        <section className="bg-slate-900 text-white rounded-2xl p-8 md:p-10 shadow-lg relative overflow-hidden">
                            <div className="absolute inset-0 bg-gradient-to-br from-slate-800 to-slate-900 z-0"></div>
                            <div className="absolute -top-20 -right-20 w-64 h-64 bg-[#1a8a6e]/20 rounded-full blur-3xl"></div>
                            <div className="relative z-10">
                                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                                    <div>
                                        <h2 className="text-2xl font-bold text-white mb-2">Need help?</h2>
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
                                            href="/privacy"
                                            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-colors"
                                        >
                                            View Privacy Policy
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
