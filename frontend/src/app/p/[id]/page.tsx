'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';

export default function PublicPage() {
    const params = useParams();
    const id = params?.id as string;

    const [pageData, setPageData] = useState<{ html_content: string } | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!id) return;

        const fetchPage = async () => {
            try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${API_URL}/pages/${id}`);
                if (!res.ok) throw new Error("Page not found");
                const data = await res.json() as Record<string, unknown>;
                const htmlContent = typeof data.html_content === 'string' ? data.html_content : '';
                setPageData({ html_content: htmlContent });
            } catch (err: unknown) {
                const errorMessage = err instanceof Error ? err.message : 'Failed to load page';
                setError(errorMessage);
            } finally {
                setLoading(false);
            }
        };
        fetchPage();
    }, [id]);

    if (loading) return <div className="h-screen flex items-center justify-center">Loading...</div>;
    if (error) return <div className="h-screen flex items-center justify-center text-red-500">{error}</div>;

    // We render the HTML content directly.
    // In a real app we'd sanitize this or render the React component structure safely.
    // For V1 MVP, we trust the agent-generated HTML.
    return (
        <div className="min-h-screen bg-slate-50">
            {/* Branded header */}
            <motion.div
                initial={{ opacity: 0, y: -12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: [0.21, 0.47, 0.32, 0.98] }}
                className="border-b border-slate-200 bg-white px-6 py-4"
            >
                <span className="text-lg font-semibold text-slate-700">Pikar AI</span>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: [0.21, 0.47, 0.32, 0.98] }}
            >
                <div className="mx-auto max-w-4xl p-6">
                    <div className="rounded-[28px] border border-slate-100/80 bg-white p-8 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                        <div className="prose prose-slate prose-lg max-w-none" dangerouslySetInnerHTML={{ __html: pageData?.html_content ?? '' }} />
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
