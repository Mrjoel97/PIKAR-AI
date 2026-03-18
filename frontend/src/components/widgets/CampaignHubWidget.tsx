'use client';

import React from 'react';
import {
    BarChart3,
    CheckCircle2,
    Circle,
    Clock,
    Eye,
    Globe,
    Image as ImageIcon,
    MousePointerClick,
    Send,
    Target,
    TrendingDown,
    TrendingUp,
    Video,
    Minus,
    FileText,
} from 'lucide-react';
import type { WidgetProps } from './WidgetRegistry';
import type { CampaignHubData } from '@/types/widgets';

const STATUS_COLORS: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600',
    in_review: 'bg-amber-100 text-amber-700',
    approved: 'bg-teal-100 text-teal-700',
    published: 'bg-emerald-100 text-emerald-700',
    active: 'bg-teal-100 text-teal-700',
    paused: 'bg-amber-100 text-amber-700',
    completed: 'bg-emerald-100 text-emerald-700',
};

const PLATFORM_ICONS: Record<string, string> = {
    twitter: '/icons/twitter.svg',
    linkedin: '/icons/linkedin.svg',
    facebook: '/icons/facebook.svg',
    instagram: '/icons/instagram.svg',
    tiktok: '/icons/tiktok.svg',
    youtube: '/icons/youtube.svg',
};

const CONTENT_TYPE_ICONS: Record<string, React.ReactNode> = {
    video: <Video size={14} className="text-purple-500" />,
    image: <ImageIcon size={14} className="text-blue-500" />,
    blog: <FileText size={14} className="text-orange-500" />,
    social: <Send size={14} className="text-pink-500" />,
    email: <Send size={14} className="text-teal-500" />,
};

function TrendIcon({ trend }: { trend?: 'up' | 'down' | 'flat' }) {
    if (trend === 'up') return <TrendingUp size={14} className="text-emerald-500" />;
    if (trend === 'down') return <TrendingDown size={14} className="text-red-500" />;
    return <Minus size={12} className="text-slate-400" />;
}

function StatusBadge({ status }: { status: string }) {
    const colorClass = STATUS_COLORS[status] || 'bg-slate-100 text-slate-600';
    return (
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${colorClass}`}>
            {status.replace(/_/g, ' ')}
        </span>
    );
}

function formatNumber(n: number | undefined): string {
    if (n === undefined || n === null) return '-';
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return n.toLocaleString();
}

export default function CampaignHubWidget({ definition }: WidgetProps) {
    const data = definition.data as unknown as CampaignHubData;
    const { campaign, content_pipeline, social_accounts, research_summary, stats } = data;

    return (
        <div className="space-y-5 p-1">
            {/* Quick Stats Row */}
            {stats && stats.length > 0 && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {stats.map((stat, i) => (
                        <div key={i} className="rounded-2xl border border-slate-100/80 bg-slate-50/50 p-4">
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{stat.label}</p>
                            <p className="mt-1 text-xl font-bold text-slate-800">{stat.value}</p>
                            {stat.change && (
                                <div className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                                    <TrendIcon trend={stat.trend} />
                                    <span>{stat.change}</span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Campaign Overview */}
            {campaign && (
                <div className="rounded-2xl border border-slate-100/80 bg-white p-5">
                    <div className="flex items-start justify-between gap-3">
                        <div>
                            <div className="flex items-center gap-2">
                                <Target size={16} className="text-teal-600" />
                                <h3 className="text-sm font-semibold text-slate-800">{campaign.name}</h3>
                            </div>
                            {campaign.target_audience && (
                                <p className="mt-1 text-xs text-slate-500">Audience: {campaign.target_audience}</p>
                            )}
                        </div>
                        <StatusBadge status={campaign.status} />
                    </div>
                    {campaign.metrics && (
                        <div className="mt-4 grid grid-cols-4 gap-3">
                            <div className="text-center">
                                <Eye size={14} className="mx-auto text-slate-400" />
                                <p className="mt-1 text-sm font-semibold text-slate-700">{formatNumber(campaign.metrics.impressions)}</p>
                                <p className="text-[10px] text-slate-400">Impressions</p>
                            </div>
                            <div className="text-center">
                                <MousePointerClick size={14} className="mx-auto text-slate-400" />
                                <p className="mt-1 text-sm font-semibold text-slate-700">{formatNumber(campaign.metrics.clicks)}</p>
                                <p className="text-[10px] text-slate-400">Clicks</p>
                            </div>
                            <div className="text-center">
                                <BarChart3 size={14} className="mx-auto text-slate-400" />
                                <p className="mt-1 text-sm font-semibold text-slate-700">{formatNumber(campaign.metrics.conversions)}</p>
                                <p className="text-[10px] text-slate-400">Conversions</p>
                            </div>
                            <div className="text-center">
                                <Target size={14} className="mx-auto text-slate-400" />
                                <p className="mt-1 text-sm font-semibold text-slate-700">
                                    {campaign.metrics.ctr !== undefined ? `${campaign.metrics.ctr.toFixed(1)}%` : '-'}
                                </p>
                                <p className="text-[10px] text-slate-400">CTR</p>
                            </div>
                        </div>
                    )}
                    {campaign.channels && campaign.channels.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                            {campaign.channels.map((ch) => (
                                <span key={ch} className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
                                    {ch}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Content Pipeline */}
            {content_pipeline && content_pipeline.items.length > 0 && (
                <div className="rounded-2xl border border-slate-100/80 bg-white p-5">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                            Content Pipeline
                        </h3>
                        <span className="text-xs text-slate-500">{content_pipeline.phase}</span>
                    </div>
                    <div className="space-y-2">
                        {content_pipeline.items.map((item, i) => (
                            <div key={i} className="flex items-center gap-3 rounded-xl bg-slate-50/50 px-3 py-2.5">
                                <div className="shrink-0">
                                    {CONTENT_TYPE_ICONS[item.type] || <Circle size={14} className="text-slate-400" />}
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm font-medium text-slate-700">{item.title}</p>
                                    {item.platform && (
                                        <p className="text-[10px] text-slate-400">{item.platform}</p>
                                    )}
                                </div>
                                <StatusBadge status={item.status} />
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Social Accounts */}
            {social_accounts && social_accounts.length > 0 && (
                <div className="rounded-2xl border border-slate-100/80 bg-white p-5">
                    <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                        Connected Channels
                    </h3>
                    <div className="flex flex-wrap gap-2">
                        {social_accounts.map((acc) => (
                            <div
                                key={acc.platform}
                                className={`flex items-center gap-2 rounded-2xl border px-3.5 py-2 text-sm ${
                                    acc.connected
                                        ? 'border-teal-200 bg-teal-50/50 text-teal-700'
                                        : 'border-slate-200 bg-slate-50 text-slate-400'
                                }`}
                            >
                                {acc.connected ? (
                                    <CheckCircle2 size={14} className="text-teal-500" />
                                ) : (
                                    <Circle size={14} className="text-slate-300" />
                                )}
                                <span className="font-medium capitalize">{acc.platform}</span>
                                {acc.last_post && (
                                    <span className="flex items-center gap-1 text-[10px] text-slate-400">
                                        <Clock size={10} /> {acc.last_post}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Research Summary */}
            {research_summary && (
                <div className="rounded-2xl border border-slate-100/80 bg-white p-5">
                    <div className="flex items-center gap-2 mb-2">
                        <Globe size={14} className="text-indigo-500" />
                        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                            Market Intel
                        </h3>
                    </div>
                    <p className="text-sm text-slate-600 leading-relaxed">{research_summary}</p>
                </div>
            )}
        </div>
    );
}
