import React from "react";
import Link from "next/link";
import Footer from "../../components/Footer";
import { Brain, ArrowLeft, CheckCircle2, Clock, AlertTriangle, Mail, HelpCircle } from "lucide-react";
import ScrollToTop from "@/components/ui/ScrollToTop";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DeletionStatus {
    id: string;
    status: "pending" | "completed" | "failed";
    platform: string;
    requested_at: string;
    completed_at: string | null;
}

async function fetchDeletionStatus(confirmationCode: string): Promise<DeletionStatus | null> {
    try {
        const res = await fetch(
            `${API_BASE_URL}/account/deletion-status/${encodeURIComponent(confirmationCode)}`,
            { cache: 'no-store' },
        );
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

function StatusCard({ status }: { status: DeletionStatus }) {
    const isCompleted = status.status === "completed";
    const isFailed = status.status === "failed";
    const isPending = status.status === "pending";

    return (
        <div className="bg-white rounded-2xl p-6 sm:p-8 md:p-10 shadow-sm border border-slate-100">
            <div className="text-center space-y-6">
                {/* Status Icon */}
                <div className="flex justify-center">
                    {isCompleted && (
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
                            <CheckCircle2 className="h-8 w-8 text-emerald-600" />
                        </div>
                    )}
                    {isPending && (
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-100 animate-pulse">
                            <Clock className="h-8 w-8 text-amber-600" />
                        </div>
                    )}
                    {isFailed && (
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-rose-100">
                            <AlertTriangle className="h-8 w-8 text-rose-600" />
                        </div>
                    )}
                </div>

                {/* Status Text */}
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 mb-2">
                        {isCompleted && "Data Deletion Complete"}
                        {isPending && "Deletion In Progress"}
                        {isFailed && "Deletion Failed"}
                    </h2>
                    <p className="text-slate-600 max-w-md mx-auto leading-relaxed">
                        {isCompleted &&
                            "All data associated with your account has been permanently deleted from our systems."}
                        {isPending &&
                            "Your data deletion request is being processed. Refresh this page to check for updates."}
                        {isFailed &&
                            "Something went wrong while processing your deletion request. Please contact our privacy team for assistance."}
                    </p>
                </div>

                {/* Details */}
                <div className="inline-flex flex-col gap-2 text-sm text-slate-500 bg-slate-50 rounded-xl px-4 sm:px-6 py-3 sm:py-4">
                    <div className="flex items-center justify-between gap-6">
                        <span>Request ID</span>
                        <span className="font-mono text-xs text-slate-700">{status.id.slice(0, 8)}...</span>
                    </div>
                    <div className="flex items-center justify-between gap-6">
                        <span>Source</span>
                        <span className="font-medium text-slate-700 capitalize">{status.platform}</span>
                    </div>
                    <div className="flex items-center justify-between gap-6">
                        <span>Requested</span>
                        <span className="font-medium text-slate-700">
                            {new Date(status.requested_at).toLocaleDateString("en-US", {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                            })}
                        </span>
                    </div>
                    {status.completed_at && (
                        <div className="flex items-center justify-between gap-6">
                            <span>Completed</span>
                            <span className="font-medium text-slate-700">
                                {new Date(status.completed_at).toLocaleDateString("en-US", {
                                    year: "numeric",
                                    month: "long",
                                    day: "numeric",
                                })}
                            </span>
                        </div>
                    )}
                </div>

                {isFailed && (
                    <a
                        href="mailto:privacy@pikar-ai.com?subject=Data%20Deletion%20Request%20Failed"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-[#1a8a6e] text-white font-semibold rounded-xl hover:bg-[#0d6b4f] transition-colors"
                    >
                        <Mail className="w-4 h-4" />
                        Contact Privacy Team
                    </a>
                )}
            </div>
        </div>
    );
}

function NotFoundCard() {
    return (
        <div className="bg-white rounded-2xl p-6 sm:p-8 md:p-10 shadow-sm border border-slate-100">
            <div className="text-center space-y-6">
                <div className="flex justify-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
                        <HelpCircle className="h-8 w-8 text-slate-400" />
                    </div>
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 mb-2">Request Not Found</h2>
                    <p className="text-slate-600 max-w-md mx-auto leading-relaxed">
                        We couldn&apos;t find a deletion request with this ID. The link may be invalid or expired.
                    </p>
                </div>
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <a
                        href="mailto:privacy@pikar-ai.com"
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-[#1a8a6e] text-white font-semibold rounded-xl hover:bg-[#0d6b4f] transition-colors"
                    >
                        <Mail className="w-4 h-4" />
                        Contact Privacy Team
                    </a>
                    <Link
                        href="/data-deletion"
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-slate-100 text-slate-700 font-semibold rounded-xl hover:bg-slate-200 transition-colors"
                    >
                        Data Deletion Info
                    </Link>
                </div>
            </div>
        </div>
    );
}

export default async function DeletionStatusPage({
    searchParams,
}: {
    searchParams: Promise<{ id?: string }>;
}) {
    const params = await searchParams;
    const confirmationCode = params.id;
    const status = confirmationCode ? await fetchDeletionStatus(confirmationCode) : null;

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
                <div className="bg-gradient-to-br from-slate-50 to-white border-b border-slate-100">
                    <div className="mx-auto max-w-4xl px-6 py-12 md:py-16">
                        <div className="text-center space-y-4">
                            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-slate-900">
                                Deletion Request Status
                            </h1>
                            <p className="text-slate-600 text-lg max-w-xl mx-auto">
                                Track the progress of your data deletion request.
                            </p>
                        </div>
                    </div>
                </div>

                <div className="mx-auto max-w-2xl px-6 py-12 md:py-16">
                    {status ? <StatusCard status={status} /> : <NotFoundCard />}
                </div>
            </main>

            <Footer />
            <ScrollToTop />
        </div>
    );
}
