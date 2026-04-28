'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { PremiumShell } from '@/components/layout/PremiumShell';
import { ActiveWorkspace } from '@/components/dashboard/ActiveWorkspace';
import { ChatInterface, ChatHistoryItem } from '@/components/chat/ChatInterface';
import { PersonaType } from '@/services/onboarding';
import { usePersona } from '@/contexts/PersonaContext';
import { useChatSession } from '@/contexts/ChatSessionContext';
import { AlertCircle, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { useSessionPreload } from '@/hooks/useSessionPreload';
import { useSessionMemoryManager } from '@/hooks/useSessionMemoryManager';
import {
    buildChatLaunchUrl,
    buildUrlWithoutDashboardLaunchParams,
    extractDashboardLaunchRequest,
} from '@/lib/onboarding/navigation';

interface PersonaDashboardLayoutProps {
    persona: PersonaType;
    title: string;
    description: string;
    children?: React.ReactNode;
    agentName?: string;
    showChat?: boolean;
    mobileLayout?: 'tabs' | 'fab';
    headerContent?: React.ReactNode;
    surface?: 'dashboard' | 'workspace';
    showGlobalKpiHeader?: boolean;
}

export default function PersonaDashboardLayout({
    persona: routePersona,
    title,
    description,
    children,
    agentName: propAgentName,
    showChat = false,
    mobileLayout = 'fab',
    headerContent,
    surface = 'dashboard',
    showGlobalKpiHeader = false,
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
    const router = useRouter();
    const pathname = usePathname();

    // Prompt to seed into the chat. `manual` is set from event handlers (e.g.
    // checklist clicks). `consumedLaunchKey` tracks which URL launch request
    // has already been consumed so we don't re-emit it on subsequent renders.
    const searchParams = useSearchParams();
    const [chatPromptState, setChatPromptState] = useState<{
        manual: string | null;
        consumedLaunchKey: string | null;
    }>({ manual: null, consumedLaunchKey: null });
    const launchRequest = useMemo(
        () => extractDashboardLaunchRequest(searchParams),
        [searchParams],
    );
    const initialChatPrompt = chatPromptState.manual
        ?? (launchRequest && launchRequest.key !== chatPromptState.consumedLaunchKey
            ? launchRequest.prompt
            : null);

    // Side-effect-only: clean the URL so a refresh doesn't re-fire the prompt.
    // No setState in the effect body — the consumed-key state is updated when
    // ChatInterface confirms it consumed the prompt.
    useEffect(() => {
        if (!launchRequest) return;
        if (launchRequest.key === chatPromptState.consumedLaunchKey) return;
        window.history.replaceState(
            {},
            '',
            buildUrlWithoutDashboardLaunchParams(pathname, searchParams),
        );
    }, [launchRequest, chatPromptState.consumedLaunchKey, pathname, searchParams]);

    const markPromptConsumed = () => {
        setChatPromptState((prev) => ({
            manual: null,
            consumedLaunchKey: launchRequest?.key ?? prev.consumedLaunchKey,
        }));
    };

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

    const handleChecklistAction = (prompt: string) => {
        if (showChat) {
            createNewChat();
            setChatPromptState({
                manual: prompt,
                consumedLaunchKey: launchRequest?.key ?? null,
            });
            return;
        }
        router.push(buildChatLaunchUrl(routePersona, prompt));
    };

    if (isLoading) {
        return (
            <PremiumShell surface={surface} mobileLayout={mobileLayout} showGlobalKpiHeader={showGlobalKpiHeader}>
                <div className="p-8 space-y-6">
                    {surface === 'workspace' ? (
                        <>
                            <div className="h-40 w-full rounded-[32px] border border-slate-100 bg-white/80 animate-pulse" />
                            <div className="h-52 w-full rounded-[28px] border border-slate-100 bg-white/80 animate-pulse" />
                            <div className="h-56 w-full rounded-[28px] border border-slate-100 bg-white/80 animate-pulse" />
                        </>
                    ) : (
                        <>
                            <div className="h-10 w-64 bg-slate-200 animate-pulse rounded-lg" />
                            <div className="h-4 w-96 bg-slate-100 animate-pulse rounded-md" />
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="h-48 bg-slate-50 border border-slate-100 animate-pulse rounded-xl" />
                                ))}
                            </div>
                        </>
                    )}
                </div>
            </PremiumShell>
        );
    }

    const isMismatch = currentPersona && currentPersona !== routePersona;
    const isWorkspaceSurface = surface === 'workspace';

    return (
        <PremiumShell
            surface={surface}
            mobileLayout={mobileLayout}
            showGlobalKpiHeader={showGlobalKpiHeader}
            chatPanel={showChat ? (
                <div className="h-full w-full flex flex-col bg-slate-50 border-l border-slate-200 overflow-hidden">

                    <div className="flex-1 overflow-hidden relative">
                        {sessionRestored ? (
                            <ChatInterface
                                initialSessionId={effectiveSessionId}
                                initialPrompt={initialChatPrompt ?? undefined}
                                onInitialPromptSent={markPromptConsumed}
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
                {!isWorkspaceSurface && isMismatch && (
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

                {children ?? (
                    <ActiveWorkspace
                        user={{}}
                        persona={routePersona}
                        onChecklistAction={handleChecklistAction}
                    />
                )}
            </div>
        </PremiumShell>
    );
}
