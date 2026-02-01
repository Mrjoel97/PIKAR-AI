'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

export default function PublicPage() {
    const params = useParams();
    const id = params?.id as string;

    const [pageData, setPageData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!id) return;

        const fetchPage = async () => {
            try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${API_URL}/pages/${id}`);
                if (!res.ok) throw new Error("Page not found");
                const data = await res.json();
                setPageData(data);
            } catch (err: any) {
                setError(err.message);
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
        <div
            dangerouslySetInnerHTML={{ __html: pageData.html_content }}
        />
    );
}
