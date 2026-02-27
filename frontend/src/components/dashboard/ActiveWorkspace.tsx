'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock, CheckCircle2, X, ArrowLeft, AlertCircle, Bot, Loader2 } from 'lucide-react';
import { WidgetContainer } from '@/components/widgets/WidgetRegistry';
import { WidgetDefinition, SavedWidget } from '@/types/widgets';
import {
    WidgetDisplayService,
    WIDGET_CHANGE_EVENT,
    WidgetChangeEventDetail,
    WIDGET_FOCUS_EVENT,
    WidgetFocusEventDetail,
    WORKSPACE_ACTIVITY_EVENT,
    WorkspaceActivityEventDetail,
} from '@/services/widgetDisplay';
import { createClient } from '@/lib/supabase/client';
import { useChatSession } from '@/contexts/ChatSessionContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/** Brief data from /briefing */
interface BriefData {
    greeting: string;
    pending_approvals: Array<{ action_type?: string; payload?: Record<string, unknown>; token?: string }>;
    online_agents: number;
    system_status: string;
}

interface ActiveWorkspaceProps {
    user: any;
    persona: string;
}

const API_URL = typeof window !== 'undefined' ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') : 'http://localhost:8000';

export function ActiveWorkspace({ user, persona }: ActiveWorkspaceProps) {
    const { currentSessionId } = useChatSession();
    const [workspaceWidgets, setWorkspaceWidgets] = useState<SavedWidget[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentUserId, setCurrentUserId] = useState<string | null>(null);
    const [userDisplayName, setUserDisplayName] = useState<string>('Executive');
    const [brief, setBrief] = useState<BriefData | null>(null);
    const [hasSessionWidgets, setHasSessionWidgets] = useState(false);

    const [focusedWidget, setFocusedWidget] = useState<WidgetDefinition | null>(null);
    const [activity, setActivity] = useState<WorkspaceActivityEventDetail | null>(null);
    const [isWidgetHidden, setIsWidgetHidden] = useState(false);
    const { sessions } = useChatSession();

    const loadWidgets = async () => {
        const supabase = createClient();
        const { data } = await supabase.auth.getUser();
        if (data?.user) {
            const user = data.user;
            setCurrentUserId(user.id);
            const meta = user.user_metadata as Record<string, unknown> | undefined;
            const raw = (meta?.full_name as string) || (meta?.name as string) || (user.email ? user.email.split('@')[0].replace(/[._]/g, ' ') : null);
            const name = raw?.trim();
            const display = name ? name.split(/\s+/).map((s: string) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()).join(' ') : 'Executive';
            setUserDisplayName(display);
            const service = new WidgetDisplayService();
            const pinned = service.getPinnedWidgets(user.id);
            const relevant = pinned.filter(w =>
                ['revenue_chart', 'initiative_dashboard', 'kanban_board', 'product_launch'].includes(w.definition.type)
            );
            setWorkspaceWidgets(relevant);
        }
        setLoading(false);
    };

    useEffect(() => {
        loadWidgets();
    }, []);

    useEffect(() => {
        const fetchBrief = async () => {
            try {
                const res = await fetch(`${API_URL}/briefing`);
                if (res.ok) {
                    const data = await res.json();
                    setBrief(data);
                }
            } catch {
                setBrief(null);
            }
        };
        fetchBrief();
    }, []);

    const updateHasSessionWidgets = () => {
        if (!currentUserId || !currentSessionId) {
            setHasSessionWidgets(false);
            return;
        }
        const service = new WidgetDisplayService();
        const session = service.getSessionWidgets(currentUserId, currentSessionId);
        const count = session.filter(w => w.definition.type !== 'image' && w.definition.type !== 'video' && w.definition.type !== 'video_spec' && w.definition.type !== 'morning_briefing').length;
        setHasSessionWidgets(count > 0);
    };

    useEffect(() => {
        updateHasSessionWidgets();
    }, [currentUserId, currentSessionId]);

    // Reset workspace view when session changes (new chat or switching chats)
    useEffect(() => {
        setFocusedWidget(null);
        setIsWidgetHidden(false);
        setActivity(null);
    }, [currentSessionId]);

    useEffect(() => {
        const handleWidgetChange = (event: Event) => {
            const detail = (event as CustomEvent<WidgetChangeEventDetail>).detail;
            if (detail.userId === currentUserId || !currentUserId) {
                loadWidgets();
                updateHasSessionWidgets();
            }
        };

        window.addEventListener(WIDGET_CHANGE_EVENT, handleWidgetChange);
        return () => window.removeEventListener(WIDGET_CHANGE_EVENT, handleWidgetChange);
    }, [currentUserId]);

    // Listen for focus widget events from chat
    useEffect(() => {
        const handleFocusWidget = (event: Event) => {
            const detail = (event as CustomEvent<WidgetFocusEventDetail>).detail;
            // Only handle if the focus is for the current user
            if (detail.userId === currentUserId || !currentUserId) {
                setFocusedWidget(detail.widget);
            }
        };

        window.addEventListener(WIDGET_FOCUS_EVENT, handleFocusWidget);
        return () => {
            window.removeEventListener(WIDGET_FOCUS_EVENT, handleFocusWidget);
        };
    }, [currentUserId]);

    // Close focus mode
    const closeFocusMode = () => {
        setFocusedWidget(null);
        setIsWidgetHidden(false);
        if (currentUserId) {
            const detail: WidgetFocusEventDetail = { widget: null, userId: currentUserId };
            window.dispatchEvent(new CustomEvent(WIDGET_FOCUS_EVENT, { detail }));
        }
    };

    // Listen for live workspace activity updates from the chat stream.
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
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

    // When the agent creates something (image, video, form, chart), show it in full focus in the workspace
    if (focusedWidget) {
        const latestTrace = activity?.traces && activity.traces.length > 0
            ? activity.traces[activity.traces.length - 1]
            : null;

        return (
            <div className="space-y-4">
                {/* Focus Mode: agent's work — user can go back to the normal brief card view */}
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between flex-wrap gap-2"
                >
                    <span className="text-sm font-medium text-slate-500">
                        Agent&apos;s work
                    </span>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={closeFocusMode}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 rounded-xl border border-slate-200 transition-all shadow-sm"
                        >
                            <ArrowLeft size={18} />
                            Back to brief
                        </button>
                        <button
                            onClick={closeFocusMode}
                            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                            title="Close and return to brief"
                            aria-label="Close"
                        >
                            <X size={20} />
                        </button>
                    </div>
                </motion.div>

                {activity && (
                    <motion.div
                        initial={{ opacity: 0, y: -6 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
                    >
                        <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2 text-sm text-slate-700 border-b border-slate-100 pb-2">
                                {activity.phase === 'running' ? (
                                    <Loader2 size={14} className="animate-spin text-teal-600" />
                                ) : (
                                    <Bot size={14} className={activity.phase === 'error' ? 'text-red-600' : 'text-teal-600'} />
                                )}
                                <span className="font-medium">{activity.agentName || 'Agent'} is working:</span>
                            </div>
                            <div className={`prose prose-sm md:prose-base dark:prose-invert max-w-none text-slate-600 overflow-y-auto pr-2 custom-scrollbar ${isWidgetHidden ? 'max-h-[600px]' : 'max-h-[150px]'}`}>
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {latestTrace?.content || activity.text || (activity.phase === 'running' ? 'Working...' : 'Update complete')}
                                </ReactMarkdown>
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* Full-view of what the agent created as workspace-native content */}
                {!isWidgetHidden ? (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.2 }}
                        className="bg-white rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.08)] border border-slate-200 overflow-hidden flex flex-col min-h-[calc(100vh-220px)]"
                    >
                        {/* Custom Tab/Header for closing the widget */}
                        <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-200">
                            <span className="text-sm font-semibold text-slate-700 font-outfit">
                                {focusedWidget.title || focusedWidget.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} Widget
                            </span>
                            <button
                                onClick={() => setIsWidgetHidden(true)}
                                className="p-1 hover:bg-slate-200 rounded-md text-slate-500 hover:text-red-500 transition-colors"
                                title="Close widget tab to view response in full"
                            >
                                <X size={16} />
                            </button>
                        </div>
                        <div className="flex-1 w-full relative">
                            <WidgetContainer
                                definition={focusedWidget}
                                fullFocus={true}
                                className="h-full w-full min-h-[400px] bg-white"
                            />
                        </div>
                    </motion.div>
                ) : (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex justify-center pt-2"
                    >
                        <button
                            onClick={() => setIsWidgetHidden(false)}
                            className="text-sm px-4 py-2 border border-slate-200 bg-white shadow-sm rounded-lg text-slate-600 hover:text-slate-900 font-medium flex items-center gap-2"
                        >
                            Open {focusedWidget.title || focusedWidget.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </button>
                    </motion.div>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-10">
            {/* Greeting – already on workspace; stay connected to brief */}
            <div className="space-y-2">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <h1 className="text-xl lg:text-3xl font-outfit font-bold text-slate-900 tracking-tight">
                        {greeting}, <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-cyan-600">{userDisplayName}</span>.
                    </h1>
                    <p className="text-slate-500 mt-2 text-sm">
                        {brief ? brief.system_status : 'Here is your active workspace.'}
                    </p>
                </motion.div>
            </div>

            {activity && (
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm"
                >
                    <div className="flex items-center gap-2 text-sm text-slate-700 border-b border-slate-100 pb-3">
                        {activity.phase === 'running' ? (
                            <Loader2 size={14} className="animate-spin text-teal-600" />
                        ) : (
                            <Bot size={14} className={activity.phase === 'error' ? 'text-red-600' : 'text-teal-600'} />
                        )}
                        <span className="font-semibold">{activity.agentName || 'Agent'} activity</span>
                    </div>
                    <div className="mt-3 prose prose-sm md:prose-base dark:prose-invert max-w-none text-slate-600 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {activity.traces?.[activity.traces.length - 1]?.content || activity.text || 'Agent is active in your workspace.'}
                        </ReactMarkdown>
                    </div>
                </motion.div>
            )}

            {/* Brief card – always shown when no widget is focused (widgets open in full focus from list above),
                BUT hidden if there's agent activity or if the user is in an active chat session a.k.a Has Messages. */}
            {(!activity && !hasSessionWidgets && !(currentSessionId && sessions.find(s => s.id === currentSessionId))) && (
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-full rounded-2xl bg-slate-50 p-6 sm:p-8 border border-slate-100/50 shadow-[inset_-5px_-5px_10px_rgba(255,255,255,0.8),inset_5px_5px_10px_rgba(0,0,0,0.05),0_15px_30px_rgba(0,0,0,0.05)]"
                >
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-bold text-slate-900">Your brief</h2>
                        <Clock size={20} className="text-slate-400" />
                    </div>
                    {brief ? (
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-slate-700">
                                <CheckCircle2 size={18} className="text-teal-500 shrink-0" />
                                <span>{brief.system_status}</span>
                            </div>
                            {brief.pending_approvals.length > 0 ? (
                                <div>
                                    <p className="text-sm font-medium text-slate-600 mb-2">
                                        {brief.pending_approvals.length} pending action{brief.pending_approvals.length !== 1 ? 's' : ''}
                                    </p>
                                    <ul className="space-y-2">
                                        {brief.pending_approvals.slice(0, 5).map((a, i) => (
                                            <li key={i} className="text-sm text-slate-600 flex items-center gap-2">
                                                <AlertCircle size={14} className="text-amber-500 shrink-0" />
                                                {a.action_type || 'Approval'} pending
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            ) : (
                                <p className="text-sm text-slate-500">No pending approvals.</p>
                            )}
                        </div>
                    ) : (
                        <p className="text-slate-500 text-sm">Loading your brief…</p>
                    )}
                </motion.div>
            )}
        </div>
    );
}
