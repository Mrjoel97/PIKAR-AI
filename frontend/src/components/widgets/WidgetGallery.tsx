'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useState } from 'react';
import { SavedWidget } from '@/types/widgets';
import { WidgetDisplayService } from '@/services/widgetDisplay';
import { WidgetContainer } from './WidgetRegistry';
import { Trash2, Maximize2, Star, Calendar, Filter } from 'lucide-react';

interface WidgetGalleryProps {
    userId: string;
}

export function WidgetGallery({ userId }: WidgetGalleryProps) {
    const [widgets, setWidgets] = useState<SavedWidget[]>([]);
    const [filter, setFilter] = useState<'all' | 'pinned' | 'session'>('all');
    const [selectedSession, setSelectedSession] = useState<string | null>(null);
    const [sessions, setSessions] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const loadWidgets = () => {
        setIsLoading(true);
        const service = new WidgetDisplayService();

        try {
            const pinned = service.getPinnedWidgets(userId);
            const allSessionIds = service.getAllSessions(userId);
            setSessions(allSessionIds);

            let displayedWidgets: SavedWidget[] = [];

            if (filter === 'pinned') {
                displayedWidgets = pinned;
            } else if (filter === 'session' && selectedSession) {
                displayedWidgets = service.getSessionWidgets(userId, selectedSession);
            } else {
                // 'all' - combine unique widgets from pinned and recent sessions
                // To avoid too many, let's just show pinned + aggregated
                // Actually 'all' usually means everything.
                const sessionWidgets = allSessionIds.flatMap(sid => service.getSessionWidgets(userId, sid));
                // De-duplicate by ID roughly
                const all = [...pinned, ...sessionWidgets];
                // Filter distinct by ID
                const seen = new Set();
                displayedWidgets = all.filter(w => {
                    const duplicate = seen.has(w.id);
                    seen.add(w.id);
                    return !duplicate;
                });
            }

            setWidgets(displayedWidgets.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()));
        } catch (e) {
            console.error('Failed to load widgets', e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadWidgets();
    }, [userId, filter, selectedSession]);

    const handlePinToggle = (widget: SavedWidget) => {
        const service = new WidgetDisplayService();
        if (widget.isPinned) {
            service.unpinWidget(widget.id, userId);
        } else {
            service.pinWidget(widget.id, userId);
        }
        loadWidgets();
    };

    const handleDelete = (widgetId: string) => {
        const service = new WidgetDisplayService();
        service.deleteWidget(userId, widgetId);
        loadWidgets();
    };

    return (
        <div className="space-y-6">
            {/* Controls */}
            <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setFilter('all')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'all'
                            ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300'
                            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700'
                            }`}
                    >
                        All Widgets
                    </button>
                    <button
                        onClick={() => setFilter('pinned')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'pinned'
                            ? 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-200'
                            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700'
                            }`}
                    >
                        Pinned
                    </button>
                    <button
                        onClick={() => setFilter('session')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'session'
                            ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300'
                            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700'
                            }`}
                    >
                        By Session
                    </button>
                </div>

                {filter === 'session' && (
                    <select
                        value={selectedSession || ''}
                        onChange={(e) => setSelectedSession(e.target.value)}
                        className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm max-w-xs"
                    >
                        <option value="">Select a session...</option>
                        {sessions.map(sid => (
                            <option key={sid} value={sid}>
                                Session {sid.substring(0, 8)}...
                            </option>
                        ))}
                    </select>
                )}
            </div>

            {/* Grid */}
            {isLoading ? (
                <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                </div>
            ) : widgets.length === 0 ? (
                <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
                    <p className="text-slate-500 dark:text-slate-400">No widgets found.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                    {widgets.map(w => (
                        <div key={w.id} className="relative group">
                            <WidgetContainer
                                definition={w.definition}
                                isMinimized={w.isMinimized}
                                showPinButton={true}
                                onAction={(action) => {
                                    if (action === 'pin') handlePinToggle(w);
                                }}
                                onDismiss={() => handleDelete(w.id)}
                            />
                            {/* Overlay Controls (Optional, if we want more than what container provides) */}
                            {/* The container handles pin and dismiss (delete) logic via props now */}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default WidgetGallery;
