'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, Loader2, Trash2 } from 'lucide-react';
import { SavedWidget, WidgetDefinition, WidgetWorkspaceMode } from '@/types/widgets';
import {
    WidgetDisplayService,
    WIDGET_CHANGE_EVENT,
    WidgetChangeEventDetail,
    WORKSPACE_ACTIVITY_EVENT,
    WORKSPACE_ITEMS_EVENT,
    WorkspaceActivityEventDetail,
    WorkspaceItemsEventDetail,
    WorkspaceRenderableItem,
    buildWorkspaceRenderableItem,
    clearWorkspaceItems,
    isWorkspaceCanvasWidget,
    isWorkspaceCanvasWidgetType,
    setActiveWorkspaceItem,
} from '@/services/widgetDisplay';
import { createClient } from '@/lib/supabase/client';
import { useSessionControl } from '@/contexts/SessionControlContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PersonaType } from '@/services/onboarding';
import { DashboardBriefCard } from '@/components/dashboard/DashboardBriefCard';
import OnboardingChecklist from '@/components/dashboard/OnboardingChecklist';
import { WorkspaceCanvas } from '@/components/workspace/WorkspaceCanvas';

interface WorkspaceRow {
    id: string;
    user_id: string;
    bundle_id?: string | null;
    deliverable_id?: string | null;
    session_id?: string | null;
    workflow_execution_id?: string | null;
    widget_type: string;
    title?: string | null;
    layout_mode?: WidgetWorkspaceMode | null;
    widget_payload?: Record<string, unknown> | null;
    created_at: string;
    updated_at: string;
}

interface ActiveWorkspaceProps {
    user?: unknown;
    persona: PersonaType;
    /** Called when a checklist action button is clicked. Parents wire this to chat. */
    onChecklistAction?: (prompt: string) => void;
}

function stringValue(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim() ? value : undefined;
}

function mergeWorkspaceItems(items: WorkspaceRenderableItem[]): WorkspaceRenderableItem[] {
    const byId = new Map<string, WorkspaceRenderableItem>();
    for (const item of items) {
        byId.set(item.id, item);
    }
    return Array.from(byId.values()).sort((left, right) => {
        const leftTime = Date.parse(left.updatedAt || left.createdAt || '') || 0;
        const rightTime = Date.parse(right.updatedAt || right.createdAt || '') || 0;
        return leftTime - rightTime;
    });
}

function savedWidgetToWorkspaceItem(saved: SavedWidget): WorkspaceRenderableItem | null {
    if (!isWorkspaceCanvasWidget(saved.definition)) return null;
    return buildWorkspaceRenderableItem(saved.definition, saved.userId, {
        id: saved.id,
        sessionId: saved.sessionId,
        mode: saved.definition.workspace?.mode ?? 'focus',
        persistent: false,
        createdAt: saved.createdAt,
        updatedAt: saved.createdAt,
    });
}

function workspaceRowToWidget(row: WorkspaceRow): WidgetDefinition | null {
    if (!isWorkspaceCanvasWidgetType(row.widget_type)) {
        return null;
    }

    const payload = (row.widget_payload || {}) as Record<string, unknown>;
    const workspace = {
        mode: row.layout_mode || 'focus',
        bundleId: row.bundle_id || stringValue(payload.bundle_id),
        deliverableId: row.deliverable_id || stringValue(payload.deliverable_id),
        workspaceItemId: row.id,
        sessionId: row.session_id || stringValue(payload.session_id),
        workflowExecutionId: row.workflow_execution_id || stringValue(payload.workflow_execution_id),
    };

    if (row.widget_type === 'image') {
        const imageUrl = stringValue(payload.file_url) || stringValue(payload.imageUrl);
        if (!imageUrl) return null;
        return {
            type: 'image',
            title: row.title || 'Image',
            data: {
                imageUrl,
                prompt: stringValue(payload.prompt),
                caption: stringValue(payload.caption),
                asset_id: stringValue(payload.asset_id),
                bundle_id: row.bundle_id || stringValue(payload.bundle_id),
                deliverable_id: row.deliverable_id || stringValue(payload.deliverable_id),
                workspace_item_id: row.id,
                session_id: row.session_id || stringValue(payload.session_id),
                workflow_execution_id: row.workflow_execution_id || stringValue(payload.workflow_execution_id),
                editable_url: stringValue(payload.editable_url),
                platform_profile: stringValue(payload.platform_profile),
            },
            workspace,
        };
    }

    if (row.widget_type === 'video') {
        const videoUrl = stringValue(payload.file_url) || stringValue(payload.videoUrl);
        if (!videoUrl) return null;
        return {
            type: 'video',
            title: row.title || stringValue(payload.title) || 'Video',
            data: {
                videoUrl,
                title: row.title || stringValue(payload.title),
                caption: stringValue(payload.caption),
                thumbnailUrl: stringValue(payload.thumbnail_url),
                storyboard_captions: Array.isArray(payload.storyboard_captions)
                    ? payload.storyboard_captions.filter((value): value is string => typeof value === 'string')
                    : undefined,
                asset_id: stringValue(payload.asset_id),
                bundle_id: row.bundle_id || stringValue(payload.bundle_id),
                deliverable_id: row.deliverable_id || stringValue(payload.deliverable_id),
                workspace_item_id: row.id,
                session_id: row.session_id || stringValue(payload.session_id),
                workflow_execution_id: row.workflow_execution_id || stringValue(payload.workflow_execution_id),
                editable_url: stringValue(payload.editable_url),
                platform_profile: stringValue(payload.platform_profile),
            },
            workspace,
        };
    }

    if (row.widget_type === 'video_spec') {
        return {
            type: 'video_spec',
            title: row.title || 'Video concept',
            data: {
                title: row.title || stringValue(payload.title),
                prompt: stringValue(payload.prompt),
                caption: stringValue(payload.caption),
                scenes: Array.isArray(payload.scenes) ? payload.scenes : undefined,
                fps: typeof payload.fps === 'number' ? payload.fps : undefined,
                durationInFrames: typeof payload.durationInFrames === 'number' ? payload.durationInFrames : undefined,
                remotion_code: stringValue(payload.remotion_code),
                instructions: Array.isArray(payload.instructions)
                    ? payload.instructions.filter((value): value is string => typeof value === 'string')
                    : undefined,
                asset_id: stringValue(payload.asset_id),
                bundle_id: row.bundle_id || stringValue(payload.bundle_id),
                deliverable_id: row.deliverable_id || stringValue(payload.deliverable_id),
                workspace_item_id: row.id,
                session_id: row.session_id || stringValue(payload.session_id),
                workflow_execution_id: row.workflow_execution_id || stringValue(payload.workflow_execution_id),
                editable_url: stringValue(payload.editable_url),
                platform_profile: stringValue(payload.platform_profile),
            },
            workspace,
        };
    }

    if (row.widget_type === 'braindump_analysis') {
        return {
            type: 'braindump_analysis' as const,
            title: row.title || 'Brain Dump Analysis',
            data: {
                markdown: stringValue(payload.markdown) || '',
                documentId: stringValue(payload.document_id) || '',
                sessionId: row.session_id || stringValue(payload.session_id),
                title: row.title || 'Brain Dump Analysis',
                keyThemes: Array.isArray(payload.key_themes) ? payload.key_themes.filter((v: unknown): v is string => typeof v === 'string') : [],
                actionItemCount: typeof payload.action_item_count === 'number' ? payload.action_item_count : 0,
            },
            workspace,
        };
    }

    if (row.widget_type === 'campaign_hub') {
        return {
            type: 'campaign_hub' as const,
            title: row.title || 'Campaign Hub',
            data: payload,
            workspace,
        };
    }

    return null;
}

function workspaceRowToRenderableItem(row: WorkspaceRow): WorkspaceRenderableItem | null {
    const widget = workspaceRowToWidget(row);
    if (!widget) return null;
    return buildWorkspaceRenderableItem(widget, row.user_id, {
        id: row.id,
        sessionId: row.session_id || undefined,
        mode: row.layout_mode || 'focus',
        persistent: true,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
    });
}

function normalizeSupabaseError(error: unknown): Record<string, unknown> | string {
    if (!error) return 'Unknown Supabase error';
    if (typeof error === 'string') return error;

    if (error instanceof Error) {
        return {
            name: error.name,
            message: error.message,
        };
    }

    if (typeof error === 'object') {
        const candidate = error as Record<string, unknown>;
        const normalized: Record<string, unknown> = {};

        for (const key of ['code', 'message', 'details', 'hint', 'status', 'statusText']) {
            const value = candidate[key];
            if (value !== undefined && value !== null && value !== '') {
                normalized[key] = value;
            }
        }

        if (Object.keys(normalized).length > 0) {
            return normalized;
        }
    }

    return String(error);
}

function isDurableWorkspaceSchemaError(error: unknown): boolean {
    if (!error || typeof error !== 'object') return false;

    const candidate = error as Record<string, unknown>;
    const code = typeof candidate.code === 'string' ? candidate.code : '';
    const message = typeof candidate.message === 'string' ? candidate.message.toLowerCase() : '';

    return code === '42P01'
        || code === '42703'
        || code === 'PGRST205'
        || (message.includes('workspace_items') && (
            message.includes('does not exist')
            || message.includes('could not find')
            || message.includes('schema cache')
        ));
}

export function ActiveWorkspace(props: ActiveWorkspaceProps) {
    void props.user;
    const { persona, onChecklistAction } = props;
    const { visibleSessionId: currentSessionId } = useSessionControl();
    const [currentUserId, setCurrentUserId] = useState<string | null>(null);
    const [userDisplayName, setUserDisplayName] = useState<string>('Executive');
    const [activity, setActivity] = useState<WorkspaceActivityEventDetail | null>(null);
    const [workspaceItems, setWorkspaceItems] = useState<WorkspaceRenderableItem[]>([]);
    const [activeItemId, setActiveItemId] = useState<string | null>(null);
    const [layoutMode, setLayoutMode] = useState<WidgetWorkspaceMode>('focus');
    const durableWorkspaceAvailableRef = useRef(true);

    const supabase = createClient();

    const loadWorkspaceState = useCallback(async () => {
        try {
            const { data } = await supabase.auth.getUser();
            const authUser = data?.user;
            if (!authUser) {
                setWorkspaceItems([]);
                setActiveItemId(null);
                setCurrentUserId(null);
                return;
            }

            setCurrentUserId(authUser.id);
            const meta = authUser.user_metadata as Record<string, unknown> | undefined;
            const raw = (meta?.full_name as string) || (meta?.name as string) || (authUser.email ? authUser.email.split('@')[0].replace(/[._]/g, ' ') : null);
            const name = raw?.trim();
            const display = name ? name.split(/\s+/).map((segment: string) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase()).join(' ') : 'Executive';
            setUserDisplayName(display);

            const widgetService = new WidgetDisplayService();
            const localItems = currentSessionId
                ? widgetService.getSessionWidgets(authUser.id, currentSessionId)
                    .map(savedWidgetToWorkspaceItem)
                    .filter((item): item is WorkspaceRenderableItem => Boolean(item))
                : [];

            let durableItems: WorkspaceRenderableItem[] = [];
            if (currentSessionId && durableWorkspaceAvailableRef.current) {
                const { data: rows, error } = await supabase
                    .from('workspace_items')
                    .select('*')
                    .eq('user_id', authUser.id)
                    .eq('session_id', currentSessionId)
                    .order('created_at', { ascending: true });

                if (error) {
                    const normalizedError = normalizeSupabaseError(error);
                    if (isDurableWorkspaceSchemaError(error)) {
                        durableWorkspaceAvailableRef.current = false;
                        console.warn('[ActiveWorkspace] Durable workspace storage is unavailable; falling back to local items only:', normalizedError);
                    } else {
                        console.error('[ActiveWorkspace] Failed to load durable workspace items:', normalizedError);
                    }
                } else {
                    durableWorkspaceAvailableRef.current = true;
                    durableItems = ((rows || []) as WorkspaceRow[])
                        .map((row: WorkspaceRow) => workspaceRowToRenderableItem(row))
                        .filter((item: WorkspaceRenderableItem | null): item is WorkspaceRenderableItem => Boolean(item));
                }
            }
            const merged = mergeWorkspaceItems([...localItems, ...durableItems]);
            const latest = merged[merged.length - 1] || null;
            setWorkspaceItems(merged);
            setActiveItemId(latest?.id || null);
            setLayoutMode(latest?.mode || 'focus');
        } finally {
            // no-op: keep immediate brief rendering instead of a blocking loading shell
        }
    }, [currentSessionId, supabase]);

    useEffect(() => {
        loadWorkspaceState();
    }, [loadWorkspaceState]);

    useEffect(() => {
        setActivity(null);
        setWorkspaceItems([]);
        setActiveItemId(null);
        setLayoutMode('focus');
    }, [currentSessionId]);

    useEffect(() => {
        const handleWidgetChange = (event: Event) => {
            const detail = (event as CustomEvent<WidgetChangeEventDetail>).detail;
            if (detail.userId === currentUserId || !currentUserId) {
                loadWorkspaceState();
            }
        };

        window.addEventListener(WIDGET_CHANGE_EVENT, handleWidgetChange);
        return () => window.removeEventListener(WIDGET_CHANGE_EVENT, handleWidgetChange);
    }, [currentUserId, loadWorkspaceState]);

    useEffect(() => {
        const handleWorkspaceItems = (event: Event) => {
            const detail = (event as CustomEvent<WorkspaceItemsEventDetail>).detail;
            const sameUser = detail.userId === currentUserId || !currentUserId;
            const sameSession = !currentSessionId || !detail.sessionId || detail.sessionId === currentSessionId;
            if (!sameUser || !sameSession) return;

            if (detail.layoutMode) {
                setLayoutMode(detail.layoutMode);
            }

            if (detail.action === 'clear') {
                setWorkspaceItems([]);
                setActiveItemId(null);
                return;
            }

            if (detail.action === 'remove' && detail.itemId) {
                setWorkspaceItems((prev) => prev.filter((item) => item.id !== detail.itemId));
                setActiveItemId((prev) => (prev === detail.itemId ? null : prev));
                return;
            }

            if (
                (detail.action === 'add' || detail.action === 'update') &&
                detail.item &&
                isWorkspaceCanvasWidget(detail.item.widget)
            ) {
                setWorkspaceItems((prev) => mergeWorkspaceItems([...prev, detail.item as WorkspaceRenderableItem]));
                return;
            }

            if (detail.action === 'set_active') {
                setActiveItemId(detail.itemId ?? null);
            }
        };

        window.addEventListener(WORKSPACE_ITEMS_EVENT, handleWorkspaceItems);
        return () => {
            window.removeEventListener(WORKSPACE_ITEMS_EVENT, handleWorkspaceItems);
        };
    }, [currentSessionId, currentUserId]);

    useEffect(() => {
        const handleWorkspaceActivity = (event: Event) => {
            const detail = (event as CustomEvent<WorkspaceActivityEventDetail>).detail;
            const sameUser = detail.userId === currentUserId || !currentUserId;
            const sameSession = !currentSessionId || detail.sessionId === currentSessionId;
            if (sameUser && sameSession) {
                setActivity(detail);
            }
        };

        window.addEventListener(WORKSPACE_ACTIVITY_EVENT, handleWorkspaceActivity);
        return () => {
            window.removeEventListener(WORKSPACE_ACTIVITY_EVENT, handleWorkspaceActivity);
        };
    }, [currentUserId, currentSessionId]);

    useEffect(() => {
        if (workspaceItems.length === 0) {
            if (activeItemId !== null) {
                setActiveItemId(null);
            }
            return;
        }

        if (!activeItemId || !workspaceItems.some((item) => item.id === activeItemId)) {
            setActiveItemId(workspaceItems[workspaceItems.length - 1].id);
        }
    }, [workspaceItems, activeItemId]);

    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    const latestTrace = activity?.traces && activity.traces.length > 0
        ? activity.traces[activity.traces.length - 1]
        : null;

    const hasWorkspaceContent = workspaceItems.length > 0;
    const isAgentWorking = Boolean(activity) || hasWorkspaceContent;

    const handleLayoutChange = (mode: WidgetWorkspaceMode) => {
        setLayoutMode(mode);
        if (currentUserId) {
            setActiveWorkspaceItem(currentUserId, activeItemId, currentSessionId || undefined, mode);
        }
    };

    const handleSelectItem = (item: WorkspaceRenderableItem) => {
        setActiveItemId(item.id);
        setLayoutMode('focus');
        if (currentUserId) {
            setActiveWorkspaceItem(currentUserId, item.id, currentSessionId || undefined, 'focus');
        }
    };

    const handleClearWorkspace = useCallback(async () => {
        if (currentUserId && currentSessionId) {
            new WidgetDisplayService().clearSessionWidgets(currentUserId, currentSessionId);

            if (durableWorkspaceAvailableRef.current) {
                const { error } = await supabase
                    .from('workspace_items')
                    .delete()
                    .eq('user_id', currentUserId)
                    .eq('session_id', currentSessionId);

                if (error && !isDurableWorkspaceSchemaError(error)) {
                    console.error('[ActiveWorkspace] Failed to clear durable workspace items:', normalizeSupabaseError(error));
                }
            }

            clearWorkspaceItems(currentUserId, currentSessionId);
        }

        setActivity(null);
        setWorkspaceItems([]);
        setActiveItemId(null);
        setLayoutMode('focus');
    }, [currentSessionId, currentUserId, supabase]);

    return (
        <motion.div
            className="min-h-full bg-white p-6 md:p-10 space-y-6"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col gap-4 border-b border-slate-100/80 pb-4 md:flex-row md:items-end md:justify-between"
            >
                <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-teal-600/80">
                        Agent Workspace
                    </p>
                    <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
                        {isAgentWorking ? 'Live work canvas' : `${greeting}, ${userDisplayName}.`}
                    </h1>
                    <p className="mt-2 max-w-3xl text-sm text-slate-600">
                        {isAgentWorking
                            ? 'Agent outputs stay here until you clear this workspace. Command Center cards are excluded so only real work remains visible.'
                            : 'Start from chat and the agent will stream its work here. Generated outputs stay available across reloads until you clear them.'}
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => { void handleClearWorkspace(); }}
                    disabled={!currentSessionId || (!activity && !hasWorkspaceContent)}
                    className={`inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2 text-sm font-semibold transition-all ${!currentSessionId || (!activity && !hasWorkspaceContent) ? 'cursor-not-allowed bg-slate-100 text-slate-400' : 'bg-slate-900 text-white hover:bg-slate-800 shadow-sm'}`}
                >
                    <Trash2 size={15} />
                    Clear workspace
                </button>
            </motion.div>

            {activity && (
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
                >
                    <div className="flex items-center gap-2 text-sm text-slate-700 border-b border-slate-100/80 pb-3">
                        {activity.phase === 'running' ? (
                            <Loader2 size={14} className="animate-spin text-teal-600" />
                        ) : (
                            <Bot size={14} className={activity.phase === 'error' ? 'text-red-600' : 'text-teal-600'} />
                        )}
                        <span className="font-semibold">{activity.agentName || 'Agent'} activity</span>
                    </div>
                    <div className="mt-3 prose prose-sm md:prose-base dark:prose-invert max-w-none text-slate-600 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {latestTrace?.content || activity.text || 'Agent is active in your workspace.'}
                        </ReactMarkdown>
                    </div>
                </motion.div>
            )}

            {hasWorkspaceContent && (
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <WorkspaceCanvas
                        items={workspaceItems}
                        activeItemId={activeItemId}
                        layoutMode={layoutMode}
                        onLayoutChange={handleLayoutChange}
                        onSelectItem={handleSelectItem}
                    />
                </motion.div>
            )}

            {!isAgentWorking && (
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-6"
                >
                    <DashboardBriefCard persona={persona} compact />
                    {currentUserId && (
                        <OnboardingChecklist
                            persona={persona}
                            userId={currentUserId}
                            onActionClick={onChecklistAction}
                        />
                    )}
                </motion.div>
            )}
        </motion.div>
    );
}
