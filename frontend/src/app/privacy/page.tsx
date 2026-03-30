import type { Metadata } from "next";
import React from "react";
import Link from "next/link";
import Footer from "../components/Footer";
import { Brain, ArrowLeft, Shield, Eye, Lock, Database, Cookie, Mail } from "lucide-react";
import ScrollToTop from "@/components/ui/ScrollToTop";

export const metadata: Metadata = {
  title: "Privacy Policy | Pikar AI",
  description: "How Pikar AI collects, uses, and protects your personal data. Google API Services User Data Policy compliant. GDPR & CCPA compliant. Last updated March 2026.",
  alternates: { canonical: "https://pikar.ai/privacy" },
  robots: { index: true, follow: false },
};

export default function PrivacyPolicyPage() {
    const lastUpdated = "March 30, 2026";
    
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

                        {/* Google User Data — required by Google API Services User Data Policy */}
                        <section id="google-user-data" className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-blue-50 text-blue-600 shrink-0">
                                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" /><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" /><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" /><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" /></svg>
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">3. Google User Data</h2>
                            </div>

                            <p className="text-slate-600 mb-8 leading-relaxed">
                                Pikar AI integrates with Google Workspace services to provide AI-powered business features. This section specifically describes how we access, use, store, and protect Google user data in compliance with the{' '}
                                <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer" className="text-[#1a8a6e] font-semibold hover:underline">Google API Services User Data Policy</a>.
                            </p>

                            {/* 3a. Data Accessed */}
                            <div className="space-y-6">
                                <div className="p-6 bg-slate-50 rounded-xl border border-slate-100">
                                    <h3 className="text-lg font-bold text-slate-900 mb-4">3a. Google Data We Access</h3>
                                    <p className="text-slate-600 mb-4 leading-relaxed">
                                        When you connect your Google account, we request access only to the data necessary to deliver the features you use. We access:
                                    </p>
                                    <div className="space-y-3">
                                        <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-100">
                                            <span className="w-6 h-6 rounded-full bg-red-100 text-red-600 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">R</span>
                                            <div>
                                                <p className="font-semibold text-slate-900 text-sm">Gmail Messages (Restricted)</p>
                                                <p className="text-slate-600 text-xs mt-1 leading-relaxed">
                                                    <strong>gmail.readonly:</strong> Read email metadata (sender, subject, date) and message bodies to generate daily briefings and prioritize your inbox via AI triage.<br />
                                                    <strong>gmail.modify:</strong> Modify email labels (e.g., archive, mark as read) based on your explicit instructions. No emails are ever deleted.<br />
                                                    <strong>gmail.send:</strong> Send emails on your behalf through AI agents, always with your review and approval before sending.
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-100">
                                            <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-600 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">S</span>
                                            <div>
                                                <p className="font-semibold text-slate-900 text-sm">Google Calendar (Sensitive)</p>
                                                <p className="text-slate-600 text-xs mt-1 leading-relaxed">Read upcoming events for scheduling briefings and create new events (meetings, reminders) when you request it through AI agents.</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-100">
                                            <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-600 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">S</span>
                                            <div>
                                                <p className="font-semibold text-slate-900 text-sm">Google Sheets &amp; Docs (Sensitive)</p>
                                                <p className="text-slate-600 text-xs mt-1 leading-relaxed">List, read, and write spreadsheets and documents to generate reports, financial analyses, and business documents on your behalf. Create Google Forms for customer feedback surveys.</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-100">
                                            <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-600 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">S</span>
                                            <div>
                                                <p className="font-semibold text-slate-900 text-sm">YouTube (Sensitive)</p>
                                                <p className="text-slate-600 text-xs mt-1 leading-relaxed">Upload and manage videos on your YouTube channel as part of social media content publishing workflows. This requires a separate explicit connection through our Social Accounts settings.</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-100">
                                            <span className="w-6 h-6 rounded-full bg-slate-200 text-slate-600 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">B</span>
                                            <div>
                                                <p className="font-semibold text-slate-900 text-sm">Basic Profile (Non-Sensitive)</p>
                                                <p className="text-slate-600 text-xs mt-1 leading-relaxed">Your email address, name, and profile picture for account identification and personalization.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* 3b. Data Usage */}
                                <div className="p-6 bg-slate-50 rounded-xl border border-slate-100">
                                    <h3 className="text-lg font-bold text-slate-900 mb-4">3b. How We Use Google Data</h3>
                                    <div className="space-y-3 text-slate-600 text-sm leading-relaxed">
                                        <p>Google user data is used exclusively to power the AI agent features you interact with:</p>
                                        <ul className="list-disc pl-6 space-y-2">
                                            <li><strong>Daily Briefings:</strong> Your AI agents read recent emails and calendar events to generate a morning executive summary.</li>
                                            <li><strong>Email Triage:</strong> Agents read inbox messages to classify them by priority and present an actionable summary.</li>
                                            <li><strong>Email Management:</strong> On your explicit instruction, agents archive emails or modify labels to keep your inbox organized.</li>
                                            <li><strong>Email Sending:</strong> Agents draft and send emails on your behalf, always requiring your approval before delivery.</li>
                                            <li><strong>Calendar Management:</strong> Agents read your schedule and create events for meetings, deadlines, and follow-ups.</li>
                                            <li><strong>Report Generation:</strong> Agents create or update Google Sheets and Docs with financial reports, analyses, and business documents.</li>
                                            <li><strong>Social Publishing:</strong> Agents upload videos to your connected YouTube channel as part of marketing workflows.</li>
                                        </ul>
                                        <p className="font-semibold text-slate-900 mt-4">Pikar AI does NOT use Google user data for advertising, marketing to third parties, or training AI/ML models.</p>
                                    </div>
                                </div>

                                {/* 3c. Data Sharing */}
                                <div className="p-6 bg-slate-50 rounded-xl border border-slate-100">
                                    <h3 className="text-lg font-bold text-slate-900 mb-4">3c. Google Data Sharing</h3>
                                    <div className="space-y-3 text-slate-600 text-sm leading-relaxed">
                                        <p>We do <strong>not</strong> sell, rent, or share your Google user data with third parties, except:</p>
                                        <ul className="list-disc pl-6 space-y-2">
                                            <li><strong>AI Processing:</strong> Email content and calendar data are sent to Google&apos;s Gemini AI models for natural language understanding (e.g., summarization, triage classification). This processing occurs via Google&apos;s API under their data processing terms, and no data is retained by the AI model after processing.</li>
                                            <li><strong>Infrastructure Providers:</strong> OAuth tokens are stored in Supabase (our authentication and database provider) with encryption at rest. Supabase acts as a data processor under our Data Processing Agreement.</li>
                                        </ul>
                                        <p>We do not transfer Google user data to any other third parties, advertisers, or data brokers.</p>
                                    </div>
                                </div>

                                {/* 3d. Data Storage & Protection */}
                                <div className="p-6 bg-slate-50 rounded-xl border border-slate-100">
                                    <h3 className="text-lg font-bold text-slate-900 mb-4">3d. Google Data Storage &amp; Protection</h3>
                                    <div className="space-y-3 text-slate-600 text-sm leading-relaxed">
                                        <ul className="list-disc pl-6 space-y-2">
                                            <li><strong>OAuth Tokens:</strong> Google OAuth access tokens and refresh tokens are stored securely in Supabase Auth with encryption at rest. Tokens are never exposed to client-side code or stored in browser storage.</li>
                                            <li><strong>Email Content:</strong> Email content is processed in real-time by AI agents and is <strong>not</strong> permanently stored. Only AI-generated summaries (e.g., briefing outputs) may be cached temporarily in Redis (up to 24 hours) for performance.</li>
                                            <li><strong>Calendar Data:</strong> Calendar event data is fetched on-demand and not persistently stored. Only event metadata used in briefings is cached temporarily.</li>
                                            <li><strong>Documents &amp; Spreadsheets:</strong> We store references (document IDs, titles, URLs) to Google Docs and Sheets created by agents, but the document content itself remains in Google&apos;s infrastructure.</li>
                                            <li><strong>YouTube:</strong> We store the OAuth connection status and platform username. Video content is uploaded directly to YouTube&apos;s API and not stored on our servers.</li>
                                            <li><strong>Security Measures:</strong> All data in transit uses TLS 1.2+. Database access uses Row Level Security (RLS) ensuring users can only access their own data. API endpoints require authenticated sessions.</li>
                                        </ul>
                                    </div>
                                </div>

                                {/* 3e. Data Retention & Deletion */}
                                <div className="p-6 bg-slate-50 rounded-xl border border-slate-100">
                                    <h3 className="text-lg font-bold text-slate-900 mb-4">3e. Google Data Retention &amp; Deletion</h3>
                                    <div className="space-y-3 text-slate-600 text-sm leading-relaxed">
                                        <ul className="list-disc pl-6 space-y-2">
                                            <li><strong>OAuth Tokens:</strong> Retained while your account is active. Immediately deleted when you disconnect your Google account or delete your Pikar AI account.</li>
                                            <li><strong>Cached Data:</strong> Temporary caches (briefing summaries, inbox snapshots) expire automatically within 24 hours.</li>
                                            <li><strong>Document References:</strong> References to created Google Docs/Sheets are retained for your Knowledge Vault. They can be deleted upon request.</li>
                                            <li><strong>Social Connections:</strong> YouTube connection tokens are deleted when you disconnect the platform from Settings.</li>
                                        </ul>
                                        <p className="mt-4"><strong>How to delete your Google data:</strong></p>
                                        <ul className="list-disc pl-6 space-y-2">
                                            <li>Visit <a href="/data-deletion" className="text-[#1a8a6e] font-semibold hover:underline">pikar.ai/data-deletion</a> to request full account and data deletion.</li>
                                            <li>Email <a href="mailto:privacy@pikar-ai.com" className="text-[#1a8a6e] font-semibold hover:underline">privacy@pikar-ai.com</a> to request deletion of specific Google data.</li>
                                            <li>Revoke Pikar AI&apos;s access at any time from your <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer" className="text-[#1a8a6e] font-semibold hover:underline">Google Account permissions</a> page.</li>
                                        </ul>
                                        <p className="mt-4">Upon receiving a deletion request, we will remove all Google user data from our systems within 30 days.</p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Lawful Basis for Processing — required by GDPR Art. 13/14 */}
                        <section className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600 shrink-0">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">4. Lawful Basis for Processing</h2>
                            </div>
                            <p className="text-slate-600 mb-6 leading-relaxed">
                                We process your personal data under the following legal bases as required by GDPR Article 6:
                            </p>
                            <div className="space-y-3">
                                <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl border border-slate-100">
                                    <span className="w-6 h-6 rounded-full bg-[#1a8a6e] text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">C</span>
                                    <div>
                                        <p className="font-semibold text-slate-900 text-sm">Consent (Art. 6(1)(a))</p>
                                        <p className="text-slate-600 text-xs mt-1 leading-relaxed">Marketing emails, waitlist updates, and optional analytics cookies. You may withdraw consent at any time by emailing privacy@pikar-ai.com.</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl border border-slate-100">
                                    <span className="w-6 h-6 rounded-full bg-blue-500 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">K</span>
                                    <div>
                                        <p className="font-semibold text-slate-900 text-sm">Contract Performance (Art. 6(1)(b))</p>
                                        <p className="text-slate-600 text-xs mt-1 leading-relaxed">Processing necessary to deliver the Service you signed up for, including account management and billing.</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl border border-slate-100">
                                    <span className="w-6 h-6 rounded-full bg-orange-500 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">L</span>
                                    <div>
                                        <p className="font-semibold text-slate-900 text-sm">Legal Obligation (Art. 6(1)(c))</p>
                                        <p className="text-slate-600 text-xs mt-1 leading-relaxed">Retaining records as required by applicable law (e.g. tax, anti-money laundering).</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl border border-slate-100">
                                    <span className="w-6 h-6 rounded-full bg-purple-500 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">I</span>
                                    <div>
                                        <p className="font-semibold text-slate-900 text-sm">Legitimate Interests (Art. 6(1)(f))</p>
                                        <p className="text-slate-600 text-xs mt-1 leading-relaxed">Fraud prevention, security monitoring, and improving Service quality, where these interests are not overridden by your rights.</p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Your Data Rights */}
                        <section className="bg-gradient-to-br from-[#1a8a6e]/5 to-[#1a8a6e]/10 rounded-2xl p-8 md:p-10 border border-[#1a8a6e]/20">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="p-3 rounded-xl bg-[#1a8a6e] text-white shrink-0">
                                    <Shield className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">5. Your Data Rights</h2>
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
                                {/* Art. 20 GDPR — Right to Data Portability */}
                                <div className="flex items-center gap-4 p-4 bg-white/80 backdrop-blur-sm rounded-xl border border-white/50">
                                    <svg className="w-5 h-5 text-[#1a8a6e]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                                    <span className="font-semibold text-slate-900">Right to Data Portability</span>
                                </div>
                                {/* Art. 21 GDPR — Right to Object */}
                                <div className="flex items-center gap-4 p-4 bg-white/80 backdrop-blur-sm rounded-xl border border-white/50">
                                    <svg className="w-5 h-5 text-[#1a8a6e]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                    <span className="font-semibold text-slate-900">Right to Object</span>
                                </div>
                            </div>

                            <div className="mt-4 p-4 bg-white/60 rounded-xl border border-white/50 text-sm text-slate-600 leading-relaxed">
                                To exercise any of these rights, email us at{' '}
                                <a href="mailto:privacy@pikar-ai.com" className="text-[#1a8a6e] font-semibold hover:underline">privacy@pikar-ai.com</a>.
                                We will respond within 30 days. You also have the right to lodge a complaint with your local data protection authority.
                            </div>
                        </section>

                        {/* Cookie Policy */}
                        <section id="cookie-policy" className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-slate-100">
                            <div className="flex items-center gap-4 mb-6">
                                <div className="p-3 rounded-xl bg-amber-50 text-amber-600 shrink-0">
                                    <Cookie className="w-6 h-6" />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900">6. Cookie Policy</h2>
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
                                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-sm font-bold">7</span>
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
                                            href="mailto:privacy@pikar-ai.com" 
                                            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-[#1a8a6e] text-white font-semibold rounded-xl hover:bg-[#0d6b4f] transition-colors"
                                        >
                                            <Mail className="w-4 h-4" />
                                            privacy@pikar-ai.com
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
