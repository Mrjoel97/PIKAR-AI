'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { PremiumShell } from '@/components/layout/PremiumShell';
import { CommandCenter } from '@/components/dashboard/CommandCenter';
import { ChatInterface, ChatHistoryItem } from '@/components/chat/ChatInterface';
import OnboardingChecklist from '@/components/dashboard/OnboardingChecklist';
import { PersonaType } from '@/services/onboarding';
import { usePersona } from '@/contexts/PersonaContext';
import { useChatSession } from '@/contexts/ChatSessionContext';
import { AlertCircle, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useState, useEffect, useMemo, Suspense } from 'react';
import { WidgetDisplayService, WIDGET_CHANGE_EVENT, WidgetChangeEventDetail, WIDGET_FOCUS_EVENT, WidgetFocusEventDetail, dispatchFocusWidget } from '@/services/widgetDisplay';
import { SavedWidget } from '@/types/widgets';
import { LayoutGrid, Pin, X } from 'lucide-react';
import { useSessionPreload } from '@/hooks/useSessionPreload';
import { useSessionMemoryManager } from '@/hooks/useSessionMemoryManager';
import { getDefaultWidgetSections } from '@/components/personas/personaWidgetDefaults';
import { WidgetContainer } from '@/components/widgets/WidgetRegistry';

interface PersonaDashboardLayoutProps {
    persona: PersonaType;
    title: string;
    description: string;
    children?: React.ReactNode;
    agentName?: string;
    showChat?: boolean;
    mobileLayout?: 'tabs' | 'fab';
    headerContent?: React.ReactNode;
}

export default function PersonaDashboardLayout({
    persona: routePersona,
    title,
    description,
    children,
    agentName: propAgentName,
    showChat = false,
    mobileLayout = 'fab',
    headerContent
}: PersonaDashboardLayoutProps) {
    const { persona: currentPersona, isLoading, userId: ctxUserId, agentName: ctxAgentName } = usePersona();
    const {
        currentSessionId,
        setCurrentSessionId,
        sessionRestored,
        sessions,
        createNewChat,
        selectChat,
        clearAllChats,
        goToHistoryPage,
        refreshSessions,
        updateSessionTitle,
        updateSessionPreview,
        addSessionOptimistic,
    } = useChatSession();

    // Handle when a new session starts (first message sent)
    const handleSessionStarted = async (sessionId: string, firstMessage: string) => {
        setCurrentSessionId(sessionId);
        const title = firstMessage.trim().length > 60
            ? firstMessage.trim().substring(0, 60) + '...'
            : firstMessage.trim();
        const now = new Date().toISOString();
        addSessionOptimistic({ id: sessionId, title, createdAt: now, updatedAt: now });

        const updateWithRetry = async (attempt: number = 0) => {
            const maxAttempts = 4;
            const delay = Math.min(1000 * Math.pow(2, attempt), 8000);
            await new Promise(resolve => setTimeout(resolve, delay));
            try {
                await updateSessionTitle(sessionId, title);
                await refreshSessions();
                setTimeout(() => refreshSessions(), 2000);
            } catch (e) {
                if (attempt < maxAttempts - 1) {
                    console.debug(`Retrying session title update (attempt ${attempt + 1})...`);
                    await updateWithRetry(attempt + 1);
                } else {
                    console.error('Failed to update session title after retries:', e);
                }
            }
        };
        updateWithRetry();
    };

    // Handle agent response - update session preview with last agent message
    const handleAgentResponse = async (sessionId: string, agentMessage: string) => {
        try {
            await updateSessionPreview(sessionId, agentMessage);
        } catch (e) {
            // Non-critical, don't block
            console.debug('Failed to update session preview:', e);
        }
    };

    // Preload recent session histories into the active sessions map
    useSessionPreload(ctxUserId ?? null);

    // Evict idle sessions from memory to prevent unbounded map growth
    useSessionMemoryManager();

    // Use agent name from context (fetched from DB) with fallback to prop
    const agentName = ctxAgentName || propAgentName;
    const [pinnedWidgets, setPinnedWidgets] = useState<SavedWidget[]>([]);
    const [sessionWidgets, setSessionWidgets] = useState<SavedWidget[]>([]);

    // Initial prompt from URL (e.g. "Discuss with Agent" from initiative detail)
    const searchParams = useSearchParams();
    const [initialChatPrompt, setInitialChatPrompt] = useState<string | null>(() => {
        const context = searchParams.get('context');
        const initiativeId = searchParams.get('initiativeId');
        const title = searchParams.get('title');
        const fromJourney = searchParams.get('fromJourney') === '1';
        const outcomesPromptParam = searchParams.get('outcomesPrompt');
        const braindumpId = searchParams.get('braindump_id');

        if (braindumpId) {
            return `I want to continue working on my brain dump. The brain dump ID is ${braindumpId}. Please use the get_braindump_document tool to retrieve the exact document by ID, then help me continue validation and research based on its contents.`;
        }

        if (context === 'initiative' && initiativeId) {
            const safeTitle = title ? decodeURIComponent(title) : 'this initiative';
            if (fromJourney) {
                let prompt = `I started this initiative from a User Journey: "${safeTitle}" (initiative ID: ${initiativeId}). Please call start_journey_workflow first. If requirements are missing, ask me only for the missing inputs, save them with update_initiative, then retry start_journey_workflow.`;
                if (outcomesPromptParam) {
                    try {
                        const decoded = decodeURIComponent(outcomesPromptParam);
                        if (decoded.trim()) prompt += ` When asking for outcomes, you can use: "${decoded}"`;
                    } catch {
                        // ignore invalid encoding
                    }
                }
                return prompt;
            }
            return `I want to discuss this initiative with you: "${safeTitle}" (ID: ${initiativeId}). Please help me with next steps, phase progress, or any questions about it.`;
        }
        return null;
    });

    // Clear URL after reading so the prompt is not re-sent on refresh
    useEffect(() => {
        if (initialChatPrompt && (searchParams.get('context') === 'initiative' || searchParams.get('initiativeId') || searchParams.get('fromJourney') || searchParams.get('outcomesPrompt') || searchParams.get('braindump_id'))) {
            window.history.replaceState({}, '', window.location.pathname);
        }
    }, [initialChatPrompt, searchParams]);

    // When opening workspace from chat history, session is in URL so chat loads it even before state updates
    const sessionFromUrl = searchParams.get('session');
    const effectiveSessionId = (sessionFromUrl != null && sessionFromUrl !== '') ? sessionFromUrl : (currentSessionId ?? undefined);

    useEffect(() => {
        if (sessionFromUrl != null && sessionFromUrl !== '') {
            setCurrentSessionId(sessionFromUrl);
            window.history.replaceState({}, '', window.location.pathname);
        }
    }, [sessionFromUrl, setCurrentSessionId]);

    // Transform sessions to ChatHistoryItem format for ChatInterface
    const chatHistory: ChatHistoryItem[] = useMemo(() => {
        return sessions.slice(0, 10).map(session => ({
            id: session.id,
            title: session.title,
            timestamp: new Date(session.updatedAt),
            preview: session.preview,
        }));
    }, [sessions]);

    // Focus mode state - hide pinned widgets when a widget is focused
    const [isFocusMode, setIsFocusMode] = useState(false);

    // Load pinned and session widgets
    const loadPinnedWidgets = () => {
        if (ctxUserId) {
            const service = new WidgetDisplayService();
            setPinnedWidgets(service.getPinnedWidgets(ctxUserId));
        }
    };

    const loadSessionWidgets = () => {
        if (ctxUserId && effectiveSessionId) {
            const service = new WidgetDisplayService();
            setSessionWidgets(service.getSessionWidgets(ctxUserId, effectiveSessionId));
        } else {
            setSessionWidgets([]);
        }
    };

    // Initial load and reload on persona/user change
    useEffect(() => {
        loadPinnedWidgets();
    }, [ctxUserId, currentPersona]);

    // Load session widgets when current session changes (or user)
    useEffect(() => {
        loadSessionWidgets();
    }, [ctxUserId, effectiveSessionId]);

    // Listen for widget changes from chat or other components
    useEffect(() => {
        const handleWidgetChange = (event: Event) => {
            const detail = (event as CustomEvent<WidgetChangeEventDetail>).detail;
            if (detail.userId === ctxUserId || !ctxUserId) {
                loadPinnedWidgets();
                loadSessionWidgets();
            }
        };

        window.addEventListener(WIDGET_CHANGE_EVENT, handleWidgetChange);
        return () => {
            window.removeEventListener(WIDGET_CHANGE_EVENT, handleWidgetChange);
        };
    }, [ctxUserId, effectiveSessionId]);

    // Listen for focus mode changes to hide/show pinned widgets
    useEffect(() => {
        const handleFocusWidget = (event: Event) => {
            const detail = (event as CustomEvent<WidgetFocusEventDetail>).detail;
            // Only handle if the focus is for the current user
            if (detail.userId === ctxUserId || !ctxUserId) {
                setIsFocusMode(detail.widget !== null);
            }
        };

        window.addEventListener(WIDGET_FOCUS_EVENT, handleFocusWidget);
        return () => {
            window.removeEventListener(WIDGET_FOCUS_EVENT, handleFocusWidget);
        };
    }, [ctxUserId]);

    const handleUnpinWidget = (widgetId: string) => {
        if (ctxUserId) {
            const service = new WidgetDisplayService();
            service.unpinWidget(widgetId, ctxUserId);
            setPinnedWidgets(prev => prev.filter(w => w.id !== widgetId));
        }
    };

    const handleOpenWidgetInWorkspace = (widget: SavedWidget) => {
        if (ctxUserId) dispatchFocusWidget(widget.definition, ctxUserId);
    };

    const handleRemoveSessionWidget = (widgetId: string) => {
        if (ctxUserId) {
            const service = new WidgetDisplayService();
            service.deleteWidget(ctxUserId, widgetId);
            setSessionWidgets(prev => prev.filter(w => w.id !== widgetId));
            dispatchFocusWidget(null, ctxUserId);
        }
    };

    if (isLoading) {
        return (
            <PremiumShell>
                <div className="p-8 space-y-6">
                    <div className="h-10 w-64 bg-slate-200 animate-pulse rounded-lg" />
                    <div className="h-4 w-96 bg-slate-100 animate-pulse rounded-md" />
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-48 bg-slate-50 border border-slate-100 animate-pulse rounded-xl" />
                        ))}
                    </div>
                </div>
            </PremiumShell>
        );
    }

    const isMismatch = currentPersona && currentPersona !== routePersona;

    return (
        <PremiumShell
            mobileLayout={mobileLayout}
            chatPanel={showChat ? (
                <div className="h-full w-full flex flex-col bg-slate-50 border-l border-slate-200 overflow-hidden">

                    <div className="flex-1 overflow-hidden relative">
                        {sessionRestored ? (
                            <ChatInterface
                                initialSessionId={effectiveSessionId}
                                initialPrompt={initialChatPrompt ?? undefined}
                                onInitialPromptSent={() => setInitialChatPrompt(null)}
                                className="h-full border-none shadow-none rounded-none bg-transparent"
                                agentName={agentName}
                                chatHistory={chatHistory}
                                onNewChat={createNewChat}
                                onSelectChat={selectChat}
                                onClearAllChats={clearAllChats}
                                onCloseAllChats={() => {
                                    // Close all chats just clears current session view
                                    // User can still access from history
                                }}
                                onCloseChat={() => {
                                    // Start a new chat when closing current
                                    createNewChat();
                                }}
                                onShowChatHistory={goToHistoryPage}
                                onSessionStarted={handleSessionStarted}
                                onAgentResponse={handleAgentResponse}
                                onSessionIdReady={(id) => setCurrentSessionId(id)}
                            />
                        ) : (
                            <div className="h-full flex items-center justify-center bg-slate-50">
                                <div className="animate-pulse text-slate-400 text-sm">Loading chat…</div>
                            </div>
                        )}
                    </div>
                </div>
            ) : undefined}
        >
            <div className="relative">
                {headerContent}
                {isMismatch && (
                    <div className="mb-6 mx-4 sm:mx-6 mt-6 p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-amber-800 animate-in fade-in slide-in-from-top-4">
                        <div className="flex items-center gap-3">
                            <AlertCircle size={20} className="text-amber-600" />
                            <div>
                                <p className="text-sm font-semibold">Persona Mismatch</p>
                                <p className="text-xs opacity-90">You are viewing the {routePersona} dashboard but your profile is currently set to {currentPersona}.</p>
                            </div>
                        </div>
                        <Link
                            href={`/${currentPersona}`}
                            className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white text-xs font-bold rounded-lg hover:bg-amber-700 transition-colors shadow-sm shadow-amber-200"
                        >
                            Switch to {currentPersona} <ArrowRight size={14} />
                        </Link>
                    </div>
                )}

                {/* In-app onboarding checklist — shown until dismissed */}
                {ctxUserId && (
                    <OnboardingChecklist
                        persona={routePersona}
                        userId={ctxUserId}
                        onActionClick={(prompt) => {
                            setInitialChatPrompt(prompt);
                        }}
                    />
                )}

                {/* Widget lists: click to open in full focus in workspace (no minimized cards) */}
                {sessionWidgets.filter(w => w.definition.type !== 'image' && w.definition.type !== 'video' && w.definition.type !== 'video_spec' && w.definition.type !== 'morning_briefing').length > 0 && !isFocusMode && (
                    <div className="mx-4 sm:mx-6 mt-6 mb-4">
                        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                            <LayoutGrid size={16} />
                            This conversation
                        </h3>
                        <ul className="space-y-1 rounded-xl border border-slate-200 bg-white/80 overflow-hidden">
                            {sessionWidgets.filter(w => w.definition.type !== 'image' && w.definition.type !== 'video' && w.definition.type !== 'video_spec' && w.definition.type !== 'morning_briefing').map((widget, idx) => (
                                <li key={widget.id || idx} className="flex items-center justify-between gap-2 px-4 py-3 hover:bg-slate-50 border-b border-slate-100 last:border-b-0">
                                    <button
                                        type="button"
                                        onClick={() => handleOpenWidgetInWorkspace(widget)}
                                        className="flex-1 text-left text-sm font-medium text-slate-700 hover:text-indigo-600 truncate"
                                    >
                                        {(widget.definition.title as string) || widget.definition.type.replace(/_/g, ' ')}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => handleRemoveSessionWidget(widget.id)}
                                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Remove from list"
                                        aria-label="Remove"
                                    >
                                        <X size={16} />
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {pinnedWidgets.length > 0 && !isFocusMode && (
                    <div className="mx-4 sm:mx-6 mt-6 mb-4">
                        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                            <Pin size={16} />
                            Pinned
                        </h3>
                        <ul className="space-y-1 rounded-xl border border-slate-200 bg-white/80 overflow-hidden">
                            {pinnedWidgets.map((widget, idx) => (
                                <li key={widget.id || idx} className="flex items-center justify-between gap-2 px-4 py-3 hover:bg-slate-50 border-b border-slate-100 last:border-b-0">
                                    <button
                                        type="button"
                                        onClick={() => handleOpenWidgetInWorkspace(widget)}
                                        className="flex-1 text-left text-sm font-medium text-slate-700 hover:text-indigo-600 truncate"
                                    >
                                        {(widget.definition.title as string) || widget.definition.type.replace(/_/g, ' ')}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => handleUnpinWidget(widget.id)}
                                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Unpin"
                                        aria-label="Unpin"
                                    >
                                        <X size={16} />
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Default persona widgets — shown when user has zero pinned widgets and has not dismissed defaults */}
                {(() => {
                    const defaultsDismissed = ctxUserId
                        ? (typeof window !== 'undefined' && localStorage.getItem(`pikar_defaults_dismissed_${ctxUserId}`) === 'true')
                        : false;
                    const hasUserWidgets = pinnedWidgets.length > 0 || defaultsDismissed;
                    const defaultSections = hasUserWidgets ? [] : getDefaultWidgetSections(currentPersona);
                    if (defaultSections.length > 0 && !isFocusMode) {
                        return (
                            <div className="mx-4 sm:mx-6 mt-6 mb-4 space-y-6">
                                {defaultSections.map((section, sIdx) => (
                                    <div key={sIdx}>
                                        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                                            <LayoutGrid size={16} />
                                            <span className="hidden sm:inline">{section.title}</span>
                                            <span className="sm:hidden">{section.shortTitle}</span>
                                        </h3>
                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                            {section.widgets.map((def, idx) => (
                                                <WidgetContainer
                                                    key={`default-${sIdx}-${def.type}-${idx}`}
                                                    definition={def}
                                                    isMinimized={false}
                                                    showPinButton={false}
                                                    onDismiss={() => {
                                                        if (ctxUserId) {
                                                            localStorage.setItem(`pikar_defaults_dismissed_${ctxUserId}`, 'true');
                                                            loadPinnedWidgets();
                                                        }
                                                    }}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        );
                    }
                    return null;
                })()}

                {children || <CommandCenter user={{}} persona={routePersona} />}
            </div>
        </PremiumShell>
    );
}

// NOTE: useSearchParams() in this component ideally needs a Suspense boundary
// from the parent to avoid CSR bailout. Callers should wrap in <Suspense> if needed.
