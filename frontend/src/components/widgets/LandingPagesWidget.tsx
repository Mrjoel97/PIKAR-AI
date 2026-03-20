'use client';

import React, { useState, useEffect } from 'react';
import { WidgetDefinition } from '@/types/widgets';
import {
    FileText,
    Globe,
    Copy,
    Trash2,
    Upload,
    ExternalLink,
    Plus,
    ChevronDown,
    ChevronUp,
} from 'lucide-react';
import {
    LandingPage,
    listPages,
    publishPage,
    unpublishPage,
    deletePage,
    duplicatePage,
    importPage,
} from '@/services/landing-pages';

interface Props {
    definition: WidgetDefinition;
    onAction?: (action: string, data: unknown) => void;
}

function formatRelativeTime(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMins > 0) return `${diffMins}m ago`;
    return 'just now';
}

export default function LandingPagesWidget({ definition, onAction }: Props) {
    const [pages, setPages] = useState<LandingPage[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [showImport, setShowImport] = useState(false);
    const [importTitle, setImportTitle] = useState('');
    const [importHtml, setImportHtml] = useState('');
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

    useEffect(() => {
        listPages()
            .then(({ pages: p }) => {
                setPages(p);
                setLoading(false);
            })
            .catch((err: unknown) => {
                setError(err instanceof Error ? err.message : 'Failed to load pages');
                setLoading(false);
            });
    }, []);

    const publishedCount = pages.filter(p => p.published).length;
    const draftCount = pages.filter(p => !p.published).length;
    const totalLeads = pages.reduce((sum, p) => sum + (p.submission_count ?? 0), 0);

    const recentPages = pages.slice(0, 5);

    const handleToggleExpand = (id: string) => {
        setExpandedId(prev => (prev === id ? null : id));
    };

    const handlePublishToggle = async (page: LandingPage) => {
        // Optimistic update
        setPages(prev =>
            prev.map(p =>
                p.id === page.id
                    ? { ...p, published: !p.published, published_at: !p.published ? new Date().toISOString() : null }
                    : p
            )
        );
        try {
            if (page.published) {
                await unpublishPage(page.id);
            } else {
                await publishPage(page.id);
            }
        } catch {
            // Revert on error
            setPages(prev =>
                prev.map(p =>
                    p.id === page.id ? { ...p, published: page.published, published_at: page.published_at } : p
                )
            );
        }
    };

    const handleDuplicate = async (page: LandingPage) => {
        try {
            const result = await duplicatePage(page.id);
            const newPage: LandingPage = {
                id: result.page_id,
                title: `${page.title} (copy)`,
                slug: result.slug,
                published: false,
                published_at: null,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                metadata: {},
                submission_count: 0,
            };
            setPages(prev => [newPage, ...prev]);
        } catch {
            // silently fail — could add toast here
        }
    };

    const handleDeleteConfirm = async (pageId: string) => {
        // Optimistic remove
        setPages(prev => prev.filter(p => p.id !== pageId));
        setConfirmDeleteId(null);
        if (expandedId === pageId) setExpandedId(null);
        try {
            await deletePage(pageId);
        } catch {
            // Could refresh list here
        }
    };

    const handleImportSubmit = async () => {
        if (!importTitle.trim() || !importHtml.trim()) return;
        try {
            const result = await importPage(importTitle, importHtml);
            const newPage: LandingPage = {
                id: result.page_id,
                title: importTitle,
                slug: result.slug,
                published: false,
                published_at: null,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                metadata: {},
                submission_count: 0,
            };
            setPages(prev => [newPage, ...prev]);
            setShowImport(false);
            setImportTitle('');
            setImportHtml('');
        } catch {
            // Could show error
        }
    };

    return (
        <div className="w-full bg-slate-900 text-slate-100 rounded-lg border border-slate-700 overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/80 flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-400" />
                    <h3 className="font-semibold text-slate-100">
                        {definition.title || 'Landing Pages'}
                    </h3>
                </div>
                <button
                    onClick={() => onAction?.('create_landing_page', {})}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-300 border border-indigo-500/40 rounded hover:bg-indigo-500/20 transition-colors"
                >
                    <Plus className="w-3 h-3" />
                    Create New
                </button>
            </div>

            {/* Quick Stats */}
            <div className="flex gap-4 px-4 py-2.5 border-b border-slate-700/60 bg-slate-800/40">
                <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    <span className="text-xs text-slate-400">
                        <span className="font-semibold text-green-400">{publishedCount}</span> Published
                    </span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-slate-500"></span>
                    <span className="text-xs text-slate-400">
                        <span className="font-semibold text-slate-300">{draftCount}</span> Drafts
                    </span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    <span className="text-xs text-slate-400">
                        <span className="font-semibold text-blue-400">{totalLeads}</span> Total Leads
                    </span>
                </div>
            </div>

            {/* Body */}
            <div className="p-3 space-y-2">
                {loading && (
                    <div className="text-center py-6 text-slate-500 text-sm">Loading pages…</div>
                )}

                {error && (
                    <div className="text-center py-4 text-red-400 text-sm">{error}</div>
                )}

                {!loading && !error && recentPages.length === 0 && !showImport && (
                    <div className="text-center py-8 space-y-3">
                        <p className="text-sm text-slate-400">
                            No landing pages yet — ask me to create one or import from Stitch
                        </p>
                        <div className="flex justify-center gap-2">
                            <button
                                onClick={() => onAction?.('create_landing_page', {})}
                                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-indigo-300 border border-indigo-500/40 rounded hover:bg-indigo-500/20 transition-colors"
                            >
                                <Plus className="w-3 h-3" />
                                Create Page
                            </button>
                            <button
                                onClick={() => setShowImport(true)}
                                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-300 border border-slate-600 rounded hover:bg-slate-700 transition-colors"
                            >
                                <Upload className="w-3 h-3" />
                                Import HTML
                            </button>
                        </div>
                    </div>
                )}

                {!loading && !error && recentPages.map(page => (
                    <div key={page.id} className="rounded-md border border-slate-700 overflow-hidden">
                        {/* Row */}
                        <div
                            className="flex items-center gap-3 px-3 py-2.5 cursor-pointer hover:bg-slate-800/60 transition-colors"
                            onClick={() => handleToggleExpand(page.id)}
                        >
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-slate-100 truncate">{page.title}</p>
                                <p className="text-xs text-slate-500 truncate">/{page.slug}</p>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                                <span
                                    className={`px-1.5 py-0.5 text-xs rounded font-medium ${
                                        page.published
                                            ? 'bg-green-500/20 text-green-400'
                                            : 'bg-slate-500/20 text-slate-400'
                                    }`}
                                >
                                    {page.published ? 'Published' : 'Draft'}
                                </span>
                                {page.submission_count > 0 && (
                                    <span className="text-xs text-blue-400">{page.submission_count} leads</span>
                                )}
                                <span className="text-xs text-slate-600">{formatRelativeTime(page.updated_at)}</span>
                                {expandedId === page.id ? (
                                    <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                                ) : (
                                    <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                                )}
                            </div>
                        </div>

                        {/* Expanded Actions */}
                        {expandedId === page.id && (
                            <div className="border-t border-slate-700 px-3 py-2.5 bg-slate-800/40 flex flex-wrap gap-2">
                                <a
                                    href={`/landing/${page.slug}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-300 border border-slate-600 rounded hover:bg-slate-700 transition-colors"
                                >
                                    <ExternalLink className="w-3 h-3" />
                                    Preview
                                </a>
                                <button
                                    onClick={() => handlePublishToggle(page)}
                                    className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border transition-colors ${
                                        page.published
                                            ? 'text-amber-400 border-amber-500/40 hover:bg-amber-500/20'
                                            : 'text-green-400 border-green-500/40 hover:bg-green-500/20'
                                    }`}
                                >
                                    <Globe className="w-3 h-3" />
                                    {page.published ? 'Unpublish' : 'Publish'}
                                </button>
                                <button
                                    onClick={() => handleDuplicate(page)}
                                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-300 border border-slate-600 rounded hover:bg-slate-700 transition-colors"
                                >
                                    <Copy className="w-3 h-3" />
                                    Duplicate
                                </button>
                                <button
                                    onClick={() => setShowImport(true)}
                                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-300 border border-slate-600 rounded hover:bg-slate-700 transition-colors"
                                >
                                    <Upload className="w-3 h-3" />
                                    Import HTML
                                </button>
                                {confirmDeleteId === page.id ? (
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-xs text-red-400">Delete?</span>
                                        <button
                                            onClick={() => handleDeleteConfirm(page.id)}
                                            className="px-2 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700 transition-colors"
                                        >
                                            Yes
                                        </button>
                                        <button
                                            onClick={() => setConfirmDeleteId(null)}
                                            className="px-2 py-1 text-xs font-medium text-slate-300 border border-slate-600 rounded hover:bg-slate-700 transition-colors"
                                        >
                                            No
                                        </button>
                                    </div>
                                ) : (
                                    <button
                                        onClick={() => setConfirmDeleteId(page.id)}
                                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-red-400 border border-red-500/40 rounded hover:bg-red-500/20 transition-colors"
                                    >
                                        <Trash2 className="w-3 h-3" />
                                        Delete
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                ))}

                {/* Import Form */}
                {showImport && (
                    <div className="rounded-md border border-slate-600 bg-slate-800/60 p-3 space-y-2">
                        <p className="text-xs font-semibold text-slate-300">Import HTML Page</p>
                        <input
                            type="text"
                            placeholder="Page title"
                            value={importTitle}
                            onChange={e => setImportTitle(e.target.value)}
                            className="w-full px-2.5 py-1.5 text-xs bg-slate-700 border border-slate-600 rounded text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                        />
                        <textarea
                            placeholder="Paste HTML content here…"
                            value={importHtml}
                            onChange={e => setImportHtml(e.target.value)}
                            rows={5}
                            className="w-full px-2.5 py-1.5 text-xs bg-slate-700 border border-slate-600 rounded text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                        />
                        <div className="flex gap-2">
                            <button
                                onClick={handleImportSubmit}
                                disabled={!importTitle.trim() || !importHtml.trim()}
                                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                            >
                                <Upload className="w-3 h-3" />
                                Import
                            </button>
                            <button
                                onClick={() => {
                                    setShowImport(false);
                                    setImportTitle('');
                                    setImportHtml('');
                                }}
                                className="px-3 py-1.5 text-xs font-medium text-slate-300 border border-slate-600 rounded hover:bg-slate-700 transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {/* Import shortcut at bottom when there are pages */}
                {!loading && !error && recentPages.length > 0 && !showImport && (
                    <button
                        onClick={() => setShowImport(true)}
                        className="w-full py-1.5 flex items-center justify-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 rounded transition-colors"
                    >
                        <Upload className="w-3 h-3" />
                        Import HTML
                    </button>
                )}
            </div>
        </div>
    );
}
