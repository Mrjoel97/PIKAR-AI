'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
    ChevronLeft,
    ChevronRight,
    LogOut,
    Brain,
    Menu,
    X,
    MessageCircle,
    Layers
} from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useSwipeGesture } from '@/hooks/useSwipeGesture';
import { usePersona } from '@/contexts/PersonaContext';
import { getPersonaNavItems } from './personaNavConfig';
import { SubscriptionBadge } from '@/components/billing/SubscriptionBadge';

interface PremiumShellProps {
    children: React.ReactNode;
    chatPanel?: React.ReactNode;
    mobileLayout?: 'tabs' | 'fab';
}

export function PremiumShell({ children, chatPanel, mobileLayout = 'fab' }: PremiumShellProps) {
    const [isNavCollapsed, setIsNavCollapsed] = useState(false);
    const [chatWidth, setChatWidth] = useState(25); // Percentage of available width
    const [isResizing, setIsResizing] = useState(false);
    const [isMobile, setIsMobile] = useState(false);
    const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
    const [isMobileChatOpen, setIsMobileChatOpen] = useState(false);
    const [activeMobileTab, setActiveMobileTab] = useState<'chat' | 'workspace'>('chat');
    const pathname = usePathname();

    // Persona-aware nav ordering
    let currentPersona: string | null = null;
    try {
        const ctx = usePersona();
        currentPersona = ctx.persona;
    } catch {
        // PremiumShell may render outside PersonaProvider (e.g., admin).
        // Fall back to default nav ordering.
    }
    const navItems = useMemo(() => getPersonaNavItems(currentPersona as 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null), [currentPersona]);

    // Persist layout preferences
    useEffect(() => {
        const saved = localStorage.getItem('pikar_layout_prefs');
        if (saved) {
            try {
                const { nav, chat } = JSON.parse(saved);
                setIsNavCollapsed(Boolean(nav));
                if (typeof chat === 'number' && Number.isFinite(chat)) {
                    setChatWidth(chat);
                }
            } catch {
                // Ignore malformed local storage and keep defaults.
            }
        }
    }, []);

    useEffect(() => {
        const media = window.matchMedia('(max-width: 768px)');
        const updateMobile = () => setIsMobile(media.matches);
        updateMobile();
        media.addEventListener('change', updateMobile);
        return () => media.removeEventListener('change', updateMobile);
    }, []);

    const savePrefs = (nav: boolean, chat: number) => {
        localStorage.setItem('pikar_layout_prefs', JSON.stringify({ nav, chat }));
    };

    // Resizing Logic (Calculated from LEFT side now)
    const startResizing = (e: React.MouseEvent) => {
        setIsResizing(true);
        e.preventDefault();
    };

    const stopResizing = () => {
        setIsResizing(false);
    };

    const resize = (e: MouseEvent) => {
        if (isResizing) {
            const containerWidth = window.innerWidth;
            const sidebarWidth = (isNavCollapsed || isMobile) ? 60 : 260; // Approximate sidebar width

            // Logic: Mouse X position minus sidebar width gives us the chat panel width in px
            const relativeX = e.clientX - sidebarWidth;
            const availableWidth = containerWidth - sidebarWidth;

            // Convert to percentage of the *content area* (not viewport)
            const newWidth = (relativeX / availableWidth) * 100;

            // Constraints: Min 15%, Max 45% of content area
            if (newWidth >= 15 && newWidth <= 50) {
                setChatWidth(newWidth);
            }
        }
    };

    useEffect(() => {
        if (isResizing) {
            window.addEventListener('mousemove', resize);
            window.addEventListener('mouseup', stopResizing);
        }
        return () => {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResizing);
        };
    }, [isResizing, isNavCollapsed, isMobile]);

    const handleSignOut = async () => {
        const supabase = createClient();
        await supabase.auth.signOut();
        window.location.href = '/';
    };

    useSwipeGesture({
        onSwipeOpen: () => setIsMobileNavOpen(true),
        onSwipeClose: () => setIsMobileNavOpen(false),
        isOpen: isMobileNavOpen,
        enabled: isMobile,
    });

    const COLLAPSED_WIDTH = '60px';
    const EXPANDED_WIDTH = '260px';
    const navCollapsed = isNavCollapsed;
    const hasChatPanel = Boolean(chatPanel);
    const shouldShowDesktopChat = hasChatPanel && !isMobile;
    const shouldShowMobileTabs = hasChatPanel && isMobile && mobileLayout === 'tabs';
    const shouldShowMobileFab = hasChatPanel && isMobile && mobileLayout === 'fab';

    // SubscriptionBadge is only safe to render when we're inside the
    // SubscriptionProvider tree. Plan 50-02 mounts SubscriptionProvider in
    // app/dashboard/layout.tsx, so we gate by pathname — PremiumShell is also
    // used from /departments/* and other routes that are NOT wrapped in the
    // SubscriptionProvider (see Plan 50-04 execution discovery). Calling
    // useSubscription() outside the provider throws, so we must branch at
    // render time rather than render-then-catch.
    const showSubscriptionBadge = Boolean(pathname?.startsWith('/dashboard'));

    return (
        <div className="flex min-h-screen h-[100dvh] bg-slate-50 text-slate-900 overflow-hidden font-inter selection:bg-teal-100 selection:text-teal-900">

            {/* Left Navigation Sidebar */}
            <motion.aside
                initial={false}
                animate={{ width: navCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH }}
                className="relative z-30 hidden md:flex flex-col bg-teal-900 backdrop-blur-xl border-r border-teal-800/60 shadow-[4px_0_30px_-12px_rgba(0,0,0,0.15)] transition-all duration-300 ease-in-out shrink-0"
            >
                {/* Logo Area */}
                <div className={`shrink-0 h-16 flex items-center border-b border-teal-800/60 ${navCollapsed ? 'justify-center' : 'px-6 justify-between'} transition-all`}>
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-teal-400 to-cyan-500 flex items-center justify-center shadow-[0_4px_20px_-4px_rgba(20,184,166,0.5)] ring-1 ring-white/10">
                            <Brain className="h-5 w-5 text-white drop-shadow-sm" />
                        </div>
                        {!navCollapsed && (
                            <motion.span
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="font-outfit font-bold text-lg text-white tracking-tight drop-shadow-sm"
                            >
                                Pikar AI
                            </motion.span>
                        )}
                    </div>
                </div>

                {/* Navigation Items */}
                <nav className={`flex-1 min-h-0 py-4 ${navCollapsed ? 'px-1.5' : 'px-3'} space-y-0.5 ${navCollapsed ? 'overflow-hidden' : 'overflow-y-auto scrollbar-thin scrollbar-thumb-teal-700 scrollbar-track-transparent'}`}>
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        return (
                            <NavItem
                                key={item.href}
                                href={item.href}
                                icon={<Icon size={20} />}
                                label={item.label}
                                collapsed={navCollapsed}
                                active={pathname?.startsWith(item.href)}
                            />
                        );
                    })}
                </nav>

                {/* Footer / Collapse Toggle */}
                <div className="shrink-0 p-3 border-t border-teal-800/60">
                    <button
                        onClick={() => {
                            const newState = !isNavCollapsed;
                            setIsNavCollapsed(newState);
                            savePrefs(newState, chatWidth);
                        }}
                        className={`w-full flex items-center ${navCollapsed ? 'justify-center' : 'px-3'} py-2.5 rounded-xl hover:bg-teal-800/70 text-teal-300 hover:text-white transition-all duration-200 bg-transparent`}
                    >
                        {navCollapsed ? <ChevronRight size={18} /> : (
                            <>
                                <ChevronLeft size={18} />
                                <span className="ml-3 text-sm font-medium">Collapse</span>
                            </>
                        )}
                    </button>

                    <button
                        onClick={handleSignOut}
                        className={`w-full mt-1 flex items-center ${navCollapsed ? 'justify-center' : 'px-3'} py-2.5 rounded-xl hover:bg-red-900/30 text-teal-300 hover:text-red-400 transition-all duration-200`}
                    >
                        <LogOut size={18} />
                        {!navCollapsed && <span className="ml-3 text-sm font-medium">Sign Out</span>}
                    </button>
                </div>
            </motion.aside>

            {/* Mobile Slide-Over Navigation */}
            <div className={`fixed inset-0 z-40 md:hidden ${isMobileNavOpen ? 'pointer-events-auto' : 'pointer-events-none'}`}>
                <div
                    className={`absolute inset-0 bg-black/40 transition-opacity ${isMobileNavOpen ? 'opacity-100' : 'opacity-0'}`}
                    onClick={() => setIsMobileNavOpen(false)}
                />
                <div
                    className={`absolute left-0 top-0 bottom-0 w-64 sm:w-72 bg-teal-900 border-r border-teal-800/60 shadow-[4px_0_30px_-12px_rgba(0,0,0,0.3)] transform transition-transform duration-300 ease-out flex flex-col max-h-[100dvh] overflow-y-auto ${isMobileNavOpen ? 'translate-x-0' : '-translate-x-full'}`}
                >
                    <div className="h-16 flex items-center justify-between px-5 border-b border-teal-800/60">
                        <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-teal-400 to-cyan-500 flex items-center justify-center shadow-[0_4px_20px_-4px_rgba(20,184,166,0.5)] ring-1 ring-white/10">
                                <Brain className="h-5 w-5 text-white drop-shadow-sm" />
                            </div>
                            <span className="font-outfit font-bold text-lg text-white tracking-tight drop-shadow-sm">Pikar AI</span>
                        </div>
                        <button
                            className="p-2 rounded-xl hover:bg-teal-800/70 text-teal-300 hover:text-white transition-all duration-200"
                            onClick={() => setIsMobileNavOpen(false)}
                            aria-label="Close navigation"
                        >
                            <X size={18} />
                        </button>
                    </div>

                    <nav className="flex-1 min-h-0 py-4 px-3 space-y-0.5 overflow-y-auto">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            return (
                                <NavItem
                                    key={item.href}
                                    href={item.href}
                                    icon={<Icon size={20} />}
                                    label={item.label}
                                    collapsed={false}
                                    active={pathname?.startsWith(item.href)}
                                />
                            );
                        })}
                    </nav>

                    <div className="shrink-0 p-3 border-t border-teal-800/60">
                        <button
                            onClick={handleSignOut}
                            className="w-full mt-1 flex items-center px-3 py-2.5 rounded-xl hover:bg-red-900/30 text-teal-300 hover:text-red-400 transition-all duration-200"
                        >
                            <LogOut size={18} />
                            <span className="ml-3 text-sm font-medium">Sign Out</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* === MOBILE TABBED LAYOUT (workspace page) === */}
            {shouldShowMobileTabs ? (
                <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden">
                    {/* Fixed header: hamburger + segmented control */}
                    <div className="shrink-0 flex items-center gap-2.5 px-3 py-2.5 bg-white border-b border-slate-200 safe-area-top z-20">
                        <button
                            onClick={() => setIsMobileNavOpen(true)}
                            className="shrink-0 inline-flex items-center justify-center h-10 w-10 rounded-xl border border-slate-100/80 bg-slate-50 text-slate-600 shadow-sm"
                            aria-label="Open navigation"
                        >
                            <Menu size={18} />
                        </button>

                        <div className="flex-1 min-w-0 flex bg-slate-100 rounded-xl p-1">
                            <button
                                onClick={() => setActiveMobileTab('chat')}
                                className={`flex-1 inline-flex items-center justify-center gap-1.5 py-2 text-sm font-semibold rounded-lg transition-all duration-200 ${
                                    activeMobileTab === 'chat'
                                        ? 'bg-white text-teal-700 shadow-sm'
                                        : 'text-slate-500 hover:text-slate-700'
                                }`}
                            >
                                <MessageCircle size={15} />
                                Chat
                            </button>
                            <button
                                onClick={() => setActiveMobileTab('workspace')}
                                className={`flex-1 inline-flex items-center justify-center gap-1.5 py-2 text-sm font-semibold rounded-lg transition-all duration-200 ${
                                    activeMobileTab === 'workspace'
                                        ? 'bg-white text-teal-700 shadow-sm'
                                        : 'text-slate-500 hover:text-slate-700'
                                }`}
                            >
                                <Layers size={15} />
                                Workspace
                            </button>
                        </div>

                        {showSubscriptionBadge && (
                            <div className="shrink-0">
                                <SubscriptionBadge />
                            </div>
                        )}
                    </div>

                    {/* Tab content — fills remaining height */}
                    <div className="flex-1 min-h-0 overflow-hidden relative">
                        {/* Chat tab */}
                        <div
                            className={`absolute inset-0 transition-opacity duration-200 ${
                                activeMobileTab === 'chat'
                                    ? 'opacity-100 z-10'
                                    : 'opacity-0 z-0 pointer-events-none'
                            }`}
                        >
                            {chatPanel}
                        </div>

                        {/* Workspace tab */}
                        <div
                            className={`absolute inset-0 overflow-y-auto transition-opacity duration-200 ${
                                activeMobileTab === 'workspace'
                                    ? 'opacity-100 z-10'
                                    : 'opacity-0 z-0 pointer-events-none'
                            }`}
                        >
                            <div className="p-4">
                                {children}
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <>
                    {/* === DESKTOP + MOBILE FAB LAYOUT === */}
                    <div className="flex-1 flex relative overflow-hidden">

                        {/* Chat Panel — Desktop side panel */}
                        {shouldShowDesktopChat && (
                            <>
                                <div
                                    className="absolute top-0 left-0 bottom-0 bg-white/50 backdrop-blur-3xl border-r border-slate-100/80 shadow-[10px_0_40px_-20px_rgba(0,0,0,0.05)] z-20 flex flex-col transition-[width] duration-0 ease-linear"
                                    style={{ width: `${chatWidth}%` }}
                                >
                                    {chatPanel}
                                </div>

                                {/* Resizable Handle */}
                                <div
                                    className="absolute top-0 bottom-0 z-30 w-1 hover:w-1.5 cursor-col-resize hover:bg-teal-400/50 transition-all flex items-center justify-center group"
                                    style={{ left: `${chatWidth}%` }}
                                    onMouseDown={startResizing}
                                >
                                    <div className="h-8 w-1 bg-slate-200 rounded-full group-hover:bg-teal-500 transition-colors origin-center" />
                                </div>
                            </>
                        )}

                        {/* Main Content Area */}
                        <main
                            className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar bg-slate-50 h-full"
                            style={{
                                marginLeft: shouldShowDesktopChat ? `${chatWidth}%` : '0',
                                width: shouldShowDesktopChat ? `${100 - chatWidth}%` : '100%',
                                touchAction: 'pan-y',
                            }}
                        >
                            <div className="w-full max-w-full p-4 sm:p-6 lg:p-10">
                                <div className="mb-4 flex items-center justify-between gap-3">
                                    <button
                                        onClick={() => setIsMobileNavOpen(true)}
                                        className="md:hidden inline-flex items-center gap-2 rounded-xl border border-slate-100/80 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-700 shadow-[0_2px_12px_-4px_rgba(15,23,42,0.12)] hover:bg-slate-50 hover:shadow-[0_4px_16px_-4px_rgba(15,23,42,0.15)] transition-all duration-200"
                                        aria-label="Open navigation"
                                    >
                                        <Menu size={16} />
                                        Menu
                                    </button>
                                    {/* Spacer so the badge hugs the right edge on desktop where the menu button is hidden. */}
                                    <div className="hidden md:block" />
                                    {showSubscriptionBadge && (
                                        <div className="ml-auto">
                                            <SubscriptionBadge />
                                        </div>
                                    )}
                                </div>
                                {children}
                            </div>
                        </main>

                    </div>

                    {/* Mobile Chat — Full-screen slide-up overlay (FAB mode only) */}
                    {shouldShowMobileFab && (
                        <>
                            <div
                                className={`fixed inset-0 z-50 flex flex-col bg-white transform transition-transform duration-300 ease-out ${
                                    isMobileChatOpen ? 'translate-y-0' : 'translate-y-full'
                                }`}
                            >
                                {/* Mobile chat header */}
                                <div className="shrink-0 h-14 flex items-center justify-between px-4 border-b border-slate-200 bg-white">
                                    <div className="flex items-center gap-3">
                                        <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-teal-400 to-cyan-500 flex items-center justify-center">
                                            <Brain className="h-4 w-4 text-white" />
                                        </div>
                                        <span className="font-outfit font-semibold text-slate-800 text-sm">Pikar AI Chat</span>
                                    </div>
                                    <button
                                        onClick={() => setIsMobileChatOpen(false)}
                                        className="p-2 rounded-xl hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-all"
                                        aria-label="Close chat"
                                    >
                                        <X size={20} />
                                    </button>
                                </div>

                                {/* Chat content — fills remaining space */}
                                <div className="flex-1 overflow-hidden">
                                    {chatPanel}
                                </div>
                            </div>

                            {/* FAB — hidden when chat is open */}
                            {!isMobileChatOpen && (
                                <button
                                    onClick={() => setIsMobileChatOpen(true)}
                                    className="fixed bottom-6 right-6 z-40 h-14 w-14 rounded-full bg-gradient-to-br from-teal-500 to-cyan-600 text-white shadow-[0_4px_24px_-4px_rgba(20,184,166,0.6)] hover:shadow-[0_6px_30px_-4px_rgba(20,184,166,0.7)] active:scale-95 transition-all duration-200 flex items-center justify-center"
                                    aria-label="Open chat"
                                >
                                    <MessageCircle size={24} />
                                </button>
                            )}
                        </>
                    )}
                </>
            )}
        </div>
    );
}

function NavItem({ icon, label, collapsed, active, href }: { icon: React.ReactNode, label: string, collapsed: boolean, active?: boolean, href: string }) {
    return (
        <Link
            href={href}
            className={`
                w-full flex items-center ${collapsed ? 'justify-center' : 'px-3'} py-3 rounded-xl transition-all duration-200 group relative
                ${active
                    ? 'bg-teal-800/80 text-white shadow-[0_2px_12px_-4px_rgba(20,184,166,0.3)]'
                    : 'text-teal-200/80 hover:bg-teal-800/50 hover:text-white'
                }
            `}
        >
            <span className={`${active ? 'text-teal-300' : 'text-teal-400/70 group-hover:text-teal-300'} transition-colors`}>
                {icon}
            </span>
            {!collapsed && (
                <span className="ml-3 text-sm font-medium font-outfit tracking-wide">
                    {label}
                </span>
            )}

            {/* Active Indicator Bar */}
            {active && (
                <div className="absolute left-0 top-2 bottom-2 w-[3px] bg-gradient-to-b from-teal-300 to-cyan-400 rounded-r-full shadow-[0_0_8px_rgba(20,184,166,0.4)]" />
            )}

            {/* Tooltip for collapsed state */}
            {collapsed && (
                <div className="absolute left-full ml-3 px-2.5 py-1.5 bg-slate-800 text-white text-[10px] font-medium rounded-lg shadow-[0_4px_16px_-4px_rgba(0,0,0,0.3)] opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none">
                    {label}
                </div>
            )}
        </Link>
    )
}

export default PremiumShell;
