'use client'
import React, { useEffect, useState } from 'react';
import { WidgetProps } from './WidgetRegistry';
import { BriefingData } from '@/types/widgets';
import { Sun, CheckCircle, Clock } from 'lucide-react';
import Link from 'next/link';
import { fetchWithAuth } from '@/services/api';

export default function MorningBriefing({ definition }: WidgetProps) {
    const [data, setData] = useState<BriefingData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetchWithAuth('/briefing');
                const json = await res.json();
                setData(json);
            } catch (error) {
                console.error('Failed to load briefing', error);
                setData(null);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    if (loading) {
        return <div className="p-6 text-center text-slate-500 animate-pulse">Checking morning status...</div>;
    }

    if (!data) {
        return <div className="p-6 text-center text-red-500">Failed to load briefing.</div>;
    }

    return (
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white p-0 overflow-hidden relative">
            <div className="absolute top-0 right-0 p-8 opacity-10">
                <Sun size={120} />
            </div>

            <div className="p-6 relative z-10">
                <div className="flex items-center gap-3 mb-6">
                    <Sun className="text-yellow-300" size={28} />
                    <h2 className="text-2xl font-bold">{data.greeting}</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/20">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-100 mb-3 flex items-center gap-2">
                            <Clock size={14} /> Pending Actions
                        </h3>

                        {data.pending_approvals.length === 0 ? (
                            <div className="text-sm text-indigo-50 flex items-center gap-2">
                                <CheckCircle size={16} className="text-green-400" />
                                All clear! No pending items.
                            </div>
                        ) : (
                            <ul className="space-y-2">
                                {data.pending_approvals.map(item => {
                                    const hasReviewLink = Boolean(item.token);
                                    return (
                                        <li key={item.id} className="bg-white/10 rounded-lg p-2 flex items-center justify-between text-sm gap-3">
                                            <span className="truncate max-w-[150px]">{item.action_type}</span>
                                            {hasReviewLink ? (
                                                <Link
                                                    href={`/approval/${item.token}`}
                                                    className="px-3 py-1 bg-white text-indigo-600 rounded-md text-xs font-bold hover:bg-indigo-50 transition"
                                                >
                                                    Review
                                                </Link>
                                            ) : (
                                                <span className="px-3 py-1 bg-white/20 text-indigo-100 rounded-md text-xs font-bold">
                                                    Unavailable
                                                </span>
                                            )}
                                        </li>
                                    );
                                })}
                            </ul>
                        )}
                    </div>

                    <div className="bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/20">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-100 mb-3">Team Status</h3>
                        <div className="flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-emerald-300">{data.online_agents}</span>
                            <span className="text-sm text-indigo-100">Agents Online</span>
                        </div>
                        <div className="mt-2 text-xs text-indigo-200">
                            System Status: <span className="text-green-300">{data.system_status}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
