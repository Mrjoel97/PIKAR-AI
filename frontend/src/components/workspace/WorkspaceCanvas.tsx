'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Columns2, LayoutGrid, Maximize2 } from 'lucide-react';
import { WidgetContainer } from '@/components/widgets/WidgetRegistry';
import { WidgetWorkspaceMode } from '@/types/widgets';
import { WorkspaceRenderableItem } from '@/services/widgetDisplay';

export function workspaceItemTitle(item: WorkspaceRenderableItem): string {
    return item.title
        || item.widget.title
        || item.widget.type.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

interface WorkspacePanelProps {
    item: WorkspaceRenderableItem;
    fullFocus: boolean;
}

export function WorkspacePanel({ item, fullFocus }: WorkspacePanelProps) {
    return (
        <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`bg-white rounded-[28px] border border-slate-100/80 overflow-hidden shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] ${fullFocus ? 'min-h-[520px]' : 'min-h-[320px]'}`}
        >
            <div className="flex items-center justify-between gap-3 border-b border-slate-100/80 bg-slate-50/50 px-5 py-3.5 rounded-t-[28px]">
                <div>
                    <p className="text-sm font-semibold text-slate-800">{workspaceItemTitle(item)}</p>
                    <p className="text-xs text-slate-500">{item.persistent ? 'Synced to workspace history' : 'Session workspace item'}</p>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                    {item.widget.type.replace(/_/g, ' ')}
                </span>
            </div>
            <div className={fullFocus ? 'min-h-[460px] bg-white' : 'min-h-[260px] bg-white'}>
                <WidgetContainer
                    definition={item.widget}
                    fullFocus={fullFocus}
                    className={fullFocus ? 'h-full w-full min-h-[460px] bg-white' : 'h-full w-full min-h-[260px] bg-white'}
                />
            </div>
        </motion.div>
    );
}

interface WorkspaceCanvasProps {
    items: WorkspaceRenderableItem[];
    activeItemId: string | null;
    layoutMode: WidgetWorkspaceMode;
    onLayoutChange: (mode: WidgetWorkspaceMode) => void;
    onSelectItem: (item: WorkspaceRenderableItem) => void;
}

export function WorkspaceCanvas({
    items,
    activeItemId,
    layoutMode,
    onLayoutChange,
    onSelectItem,
}: WorkspaceCanvasProps) {
    const activeItem = useMemo(
        () => items.find((item) => item.id === activeItemId) || items[items.length - 1] || null,
        [activeItemId, items],
    );

    const compareItems = useMemo(() => {
        if (items.length <= 1) return items;
        if (!activeItem) return items.slice(-2);
        const secondary = items.find((item) => item.id !== activeItem.id);
        return secondary ? [activeItem, secondary] : [activeItem];
    }, [activeItem, items]);

    if (items.length === 0) return null;

    const renderControls = () => (
        <div className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                        Workspace Canvas
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                        {activeItem ? `Showing ${workspaceItemTitle(activeItem)}.` : 'Showing the latest agent output.'}
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    {[
                        { mode: 'focus' as WidgetWorkspaceMode, label: 'Focus', icon: Maximize2 },
                        { mode: 'grid' as WidgetWorkspaceMode, label: 'Grid', icon: LayoutGrid },
                        { mode: 'compare' as WidgetWorkspaceMode, label: 'Compare', icon: Columns2 },
                    ].map(({ mode, label, icon: Icon }) => {
                        const disabled = mode === 'compare' && items.length < 2;
                        const active = layoutMode === mode || (mode === 'compare' && layoutMode === 'split');
                        return (
                            <button
                                key={mode}
                                type="button"
                                onClick={() => onLayoutChange(mode)}
                                disabled={disabled}
                                className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-semibold transition-all ${active ? 'bg-teal-600 text-white shadow-sm' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'} ${disabled ? 'cursor-not-allowed opacity-40' : ''}`}
                            >
                                <Icon size={15} />
                                {label}
                            </button>
                        );
                    })}
                </div>
            </div>
            {items.length > 1 && (
                <div className="mt-4 flex flex-wrap gap-2">
                    {items.map((item) => {
                        const selected = item.id === activeItemId;
                        return (
                            <button
                                key={item.id}
                                type="button"
                                onClick={() => onSelectItem(item)}
                                className={`rounded-2xl border px-4 py-2 text-sm font-medium transition-all ${selected ? 'border-teal-600 bg-teal-600 text-white shadow-sm' : 'border-slate-100/80 bg-white text-slate-600 hover:border-teal-200 hover:shadow-[0_8px_30px_-15px_rgba(15,23,42,0.15)]'}`}
                            >
                                {workspaceItemTitle(item)}
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );

    const renderBody = () => {
        if ((layoutMode === 'compare' || layoutMode === 'split') && compareItems.length > 1) {
            return (
                <div className="grid gap-4 xl:grid-cols-2">
                    {compareItems.map((item) => (
                        <WorkspacePanel key={item.id} item={item} fullFocus={false} />
                    ))}
                </div>
            );
        }
        if (layoutMode === 'grid') {
            return (
                <div className="grid gap-4 md:grid-cols-2">
                    {items.map((item) => (
                        <WorkspacePanel key={item.id} item={item} fullFocus={false} />
                    ))}
                </div>
            );
        }
        return activeItem ? <WorkspacePanel item={activeItem} fullFocus /> : null;
    };

    return (
        <div className="space-y-4">
            {renderControls()}
            {renderBody()}
        </div>
    );
}

export default WorkspaceCanvas;
