'use client';

import React, { useState, useMemo } from 'react';
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
    Users,
    Newspaper,
    ArrowUpRight,
    Trophy,
    Calendar,
    ChevronDown,
    ChevronUp,
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
    scheduled: 'bg-blue-100 text-blue-700',
    backlog: 'bg-slate-100 text-slate-500',
};

const CONTENT_TYPE_ICONS: Record<string, React.ReactNode> = {
    video: <Video size={14} className="text-purple-500" />,
    image: <ImageIcon size={14} className="text-blue-500" />,
    blog: <FileText size={14} className="text-orange-500" />,
    social: <Send size={14} className="text-pink-500" />,
    email: <Send size={14} className="text-teal-500" />,
};

const PIPELINE_TABS = ['all', 'draft', 'in_review', 'approved', 'published'] as const;
type PipelineTab = (typeof PIPELINE_TABS)[number];

const PIPELINE_TAB_LABELS: Record<PipelineTab, string> = {
    all: 'All',
    draft: 'Drafts',
    in_review: 'In Review',
    approved: 'Approved',
    published: 'Published',
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

function formatRelativeDate(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffH = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffH < 1) return 'Just now';
    if (diffH < 24) return `${diffH}h ago`;
    const diffD = Math.floor(diffH / 24);
    if (diffD < 7) return `${diffD}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** Tiny inline sparkline bar for trend visualization */
function SparkBar({ value, max, color }: { value: number; max: number; color: string }) {
    const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
    return (
        <div className="mt-2 h-1.5 w-full rounded-full bg-slate-100">
            <div
                className={`h-1.5 rounded-full ${color} transition-all duration-500`}
                style={{ width: `${pct}%` }}
            />
        </div>
    );
}

export default function CampaignHubWidget({ definition }: WidgetProps) {
    const data = definition.data as unknown as CampaignHubData;
    const {
        campaign,
        content_pipeline,
        social_accounts,
        research_summary,
        stats,
        competitors,
        news_feed,
        analytics_period,
        top_posts,
    } = data;

    const [pipelineTab, setPipelineTab] = useState<PipelineTab>('all');
    const [newsTopicFilter, setNewsTopicFilter] = useState<string>('all');
    const [competitorSortKey, setCompetitorSortKey] = useState<'followers' | 'engagement_rate' | 'recent_posts'>('followers');
    const [competitorSortAsc, setCompetitorSortAsc] = useState(false);

    // Filtered pipeline items based on active tab
    const filteredPipelineItems = useMemo(() => {
        if (!content_pipeline?.items) return [];
        if (pipelineTab === 'all') return content_pipeline.items;
        return content_pipeline.items.filter((item) => item.status === pipelineTab);
    }, [content_pipeline, pipelineTab]);

    // Pipeline tab counts
    const pipelineCounts = useMemo(() => {
        if (!content_pipeline?.items) return {} as Record<PipelineTab, number>;
        const counts: Record<string, number> = { all: content_pipeline.items.length };
        for (const item of content_pipeline.items) {
            counts[item.status] = (counts[item.status] ?? 0) + 1;
        }
        return counts;
    }, [content_pipeline]);

    // Unique news topics for filter
    const newsTopics = useMemo(() => {
        if (!news_feed) return [];
        const topics = new Set(news_feed.map((n) => n.topic).filter(Boolean));
        return Array.from(topics) as string[];
    }, [news_feed]);

    // Filtered news items
    const filteredNews = useMemo(() => {
        if (!news_feed) return [];
        if (newsTopicFilter === 'all') return news_feed;
        return news_feed.filter((n) => n.topic === newsTopicFilter);
    }, [news_feed, newsTopicFilter]);

    // Sorted competitors
    const sortedCompetitors = useMemo(() => {
        if (!competitors) return [];
        return [...competitors].sort((a, b) => {
            const aVal = a[competitorSortKey] ?? 0;
            const bVal = b[competitorSortKey] ?? 0;
            return competitorSortAsc ? aVal - bVal : bVal - aVal;
        });
    }, [competitors, competitorSortKey, competitorSortAsc]);

    // Compute max stat value for sparkline scaling
    const maxStatValue = useMemo(() => {
        if (!stats) return 1;
        return Math.max(
            ...stats.map((s) => {
                const num = parseFloat(s.value.replace(/[^0-9.]/g, ''));
                return isNaN(num) ? 0 : num;
            }),
            1
        );
    }, [stats]);

    const SPARK_COLORS = [
        'bg-teal-500',
        'bg-emerald-500',
        'bg-sky-500',
        'bg-violet-500',
    ];

    return (
        <div className="space-y-5 p-1">
            {/* Analytics Period Indicator */}
            {analytics_period && (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Calendar size={12} />
                    <span>Reporting period: {analytics_period}</span>
                </div>
            )}

            {/* Quick Stats Row with Sparklines */}
            {stats && stats.length > 0 && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {stats.map((stat, i) => {
                        const numVal = parseFloat(stat.value.replace(/[^0-9.]/g, ''));
                        return (
                            <div key={i} className="rounded-2xl border border-slate-100/80 bg-slate-50/50 p-4">
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{stat.label}</p>
                                <p className="mt-1 text-xl font-bold text-slate-800">{stat.value}</p>
                                {stat.change && (
                                    <div className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                                        <TrendIcon trend={stat.trend} />
                                        <span>{stat.change}</span>
                                    </div>
                                )}
                                {!isNaN(numVal) && (
                                    <SparkBar
                                        value={numVal}
                                        max={maxStatValue}
                                        color={SPARK_COLORS[i % SPARK_COLORS.length]}
                                    />
                                )}
                            </div>
                        );
                    })}
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

            {/* Content Pipeline with Tabs */}
            {content_pipeline && content_pipeline.items.length > 0 && (
                <div className="rounded-2xl border border-slate-100/80 bg-white p-5">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                            Content Pipeline
                        </h3>
                        <span className="text-xs text-slate-500">{content_pipeline.phase}</span>
                    </div>
                    {/* Tab Bar */}
                    <div className="mb-3 flex gap-1 overflow-x-auto rounded-xl bg-slate-100/80 p-0.5">
                        {PIPELINE_TABS.map((tab) => {
                            const count = pipelineCounts[tab] ?? 0;
                            if (tab !== 'all' && count === 0) return null;
                            return (
                                <button
                                    key={tab}
                                    onClick={() => setPipelineTab(tab)}
                                    className={`flex-shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                                        pipelineTab === tab
                                            ? 'bg-white text-slate-800 shadow-sm'
                                            : 'text-slate-500 hover:text-slate-700'
                                    }`}
                                >
                                    {PIPELINE_TAB_LABELS[tab]}
                                    {count > 0 && (
                                        <span className="ml-1.5 text-[10px] text-slate-400">
                                            {count}
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                    {/* Pipeline Items */}
                    <div className="space-y-2">
                        {filteredPipelineItems.length === 0 ? (
                            <p className="py-4 text-center text-xs text-slate-400">
                                No items in this stage
                            </p>
                        ) : (
                            filteredPipelineItems.map((item, i) => (
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
                            ))
                        )}
                    </div>
                </div>
            )}

            {/* Top Performing Posts */}
            {top_posts && top_posts.length > 0 && (
                <div className="rounded-2xl border border-slate-100/80 bg-white p-5">
                    <div className="flex items-center gap-2 mb-3">
                        <Trophy size={14} className="text-amber-500" />
                        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                            Top Performing
                        </h3>
                    </div>
                    <div className="space-y-2">
                        {top_posts.slice(0, 5).map((post, i) => (
                            <div key={i} className="flex items-center gap-3 rounded-xl bg-slate-50/50 px-3 py-2.5">
                                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-700">
                                    {i + 1}
                                </span>
                                <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm font-medium text-slate-700">{post.title}</p>
                                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                                        {post.platform && <span className="capitalize">{post.platform}</span>}
                                        {post.published_at && <span>{formatRelativeDate(post.published_at)}</span>}
                                    </div>
                                </div>
                                <div className="flex-shrink-0 text-right">
                                    {post.impressions !== undefined && (
                                        <p className="text-xs font-semibold text-slate-700">{formatNumber(post.impressions)}</p>
                                    )}
                                    {post.engagement_rate !== undefined && (
                                        <p className="text-[10px] text-emerald-600">{post.engagement_rate.toFixed(1)}% eng.</p>
                                    )}
                                </div>
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

            {/* Competitor Tracker */}
            {sortedCompetitors.length > 0 && (
                <div className="rounded-2xl border border-slate-100/80 bg-white p-5">
                    <div className="flex items-center gap-2 mb-3">
                        <Users size={14} className="text-violet-500" />
                        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                            Competitor Tracker
                        </h3>
                    </div>
                    {/* Sortable Header */}
                    <div className="mb-2 grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 px-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                        <span>Account</span>
                        {(['followers', 'engagement_rate', 'recent_posts'] as const).map((key) => (
                            <button
                                key={key}
                                onClick={() => {
                                    if (competitorSortKey === key) {
                                        setCompetitorSortAsc(!competitorSortAsc);
                                    } else {
                                        setCompetitorSortKey(key);
                                        setCompetitorSortAsc(false);
                                    }
                                }}
                                className="flex items-center gap-0.5 hover:text-slate-600 transition-colors"
                            >
                                {key === 'engagement_rate' ? 'Eng. Rate' : key === 'recent_posts' ? 'Posts' : 'Followers'}
                                {competitorSortKey === key && (
                                    competitorSortAsc ? <ChevronUp size={10} /> : <ChevronDown size={10} />
                                )}
                            </button>
                        ))}
                    </div>
                    {/* Competitor Rows */}
                    <div className="space-y-1.5">
                        {sortedCompetitors.map((comp, i) => (
                            <div key={i} className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 rounded-xl bg-slate-50/50 px-3 py-2.5">
                                <div className="min-w-0 flex items-center gap-2">
                                    {comp.avatar_url ? (
                                        <img
                                            src={comp.avatar_url}
                                            alt=""
                                            className="h-7 w-7 rounded-full object-cover flex-shrink-0"
                                        />
                                    ) : (
                                        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-violet-100 text-[10px] font-bold text-violet-600">
                                            {(comp.name || comp.handle).charAt(0).toUpperCase()}
                                        </div>
                                    )}
                                    <div className="min-w-0">
                                        <p className="truncate text-sm font-medium text-slate-700">
                                            {comp.name || comp.handle}
                                        </p>
                                        <p className="text-[10px] text-slate-400 capitalize">{comp.platform}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-1 text-xs text-slate-600">
                                    {formatNumber(comp.followers)}
                                    {comp.growth_trend && <TrendIcon trend={comp.growth_trend} />}
                                </div>
                                <span className="text-xs text-slate-600">
                                    {comp.engagement_rate !== undefined ? `${comp.engagement_rate.toFixed(1)}%` : '-'}
                                </span>
                                <span className="text-xs text-slate-600">
                                    {comp.recent_posts !== undefined ? comp.recent_posts : '-'}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Industry News Feed */}
            {news_feed && news_feed.length > 0 && (
                <div className="rounded-2xl border border-slate-100/80 bg-white p-5">
                    <div className="flex items-center gap-2 mb-3">
                        <Newspaper size={14} className="text-sky-500" />
                        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                            Industry News
                        </h3>
                    </div>
                    {/* Topic Filter Chips */}
                    {newsTopics.length > 0 && (
                        <div className="mb-3 flex flex-wrap gap-1.5">
                            <button
                                onClick={() => setNewsTopicFilter('all')}
                                className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors ${
                                    newsTopicFilter === 'all'
                                        ? 'bg-sky-100 text-sky-700'
                                        : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                                }`}
                            >
                                All
                            </button>
                            {newsTopics.map((topic) => (
                                <button
                                    key={topic}
                                    onClick={() => setNewsTopicFilter(topic)}
                                    className={`rounded-full px-2.5 py-1 text-[11px] font-medium capitalize transition-colors ${
                                        newsTopicFilter === topic
                                            ? 'bg-sky-100 text-sky-700'
                                            : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                                    }`}
                                >
                                    {topic}
                                </button>
                            ))}
                        </div>
                    )}
                    {/* News Cards */}
                    <div className="space-y-2">
                        {filteredNews.slice(0, 6).map((item) => (
                            <div key={item.id} className="rounded-xl bg-slate-50/50 px-3 py-3">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="min-w-0 flex-1">
                                        <p className="text-sm font-medium text-slate-700 leading-snug">
                                            {item.headline}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500 line-clamp-2 leading-relaxed">
                                            {item.summary}
                                        </p>
                                        <div className="mt-1.5 flex items-center gap-2 text-[10px] text-slate-400">
                                            <span className="font-medium">{item.source}</span>
                                            <span>{formatRelativeDate(item.published_at)}</span>
                                            {item.topic && (
                                                <span className="rounded bg-slate-200/80 px-1.5 py-0.5 text-[9px] font-medium uppercase text-slate-500">
                                                    {item.topic}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    {item.url && (
                                        <a
                                            href={item.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex-shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                                        >
                                            <ArrowUpRight size={14} />
                                        </a>
                                    )}
                                </div>
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
