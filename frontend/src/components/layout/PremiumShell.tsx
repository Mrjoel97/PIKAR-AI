'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    ChevronLeft,
    ChevronRight,
    LogOut,
    Brain,
    Menu,
    X
} from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { MAIN_INTERFACE_NAV_ITEMS } from './sidebarNav';

interface PremiumShellProps {
    children: React.ReactNode;
    chatPanel?: React.ReactNode;
}

export function PremiumShell({ children, chatPanel }: PremiumShellProps) {
    const [isNavCollapsed, setIsNavCollapsed] = useState(false);
    const [chatWidth, setChatWidth] = useState(25); // Percentage of available width
    const [isResizing, setIsResizing] = useState(false);
    const [isMobile, setIsMobile] = useState(false);
    const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
    const pathname = usePathname();

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

    const COLLAPSED_WIDTH = '60px';
    const EXPANDED_WIDTH = '260px';
    const navCollapsed = isNavCollapsed;
    const shouldShowChatPanel = Boolean(chatPanel) && !isMobile;

    return (
        <div className="flex min-h-screen h-[100dvh] bg-slate-50 text-slate-900 overflow-hidden font-inter selection:bg-teal-100 selection:text-teal-900">

            {/* Left Navigation Sidebar */}
            <motion.aside
                initial={false}
                animate={{ width: navCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH }}
                className="relative z-30 hidden md:flex flex-col bg-teal-900 backdrop-blur-xl border-r border-teal-800 shadow-[2px_0_24px_-12px_rgba(0,0,0,0.08)] transition-all duration-300 ease-in-out shrink-0"
            >
                {/* Logo Area */}
                <div className={`h-16 flex items-center ${navCollapsed ? 'justify-center' : 'px-6 justify-between'} transition-all`}>
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg">
                            <Brain className="h-5 w-5 text-white" />
                        </div>
                        {!navCollapsed && (
                            <motion.span
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="font-outfit font-bold text-lg text-white tracking-tight"
                            >
                                Pikar AI
                            </motion.span>
                        )}
                    </div>
                </div>

                {/* Navigation Items */}
                <nav className="flex-1 py-6 px-3 space-y-1">
                    {MAIN_INTERFACE_NAV_ITEMS.map((item) => {
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
                <div className="p-3 border-t border-teal-800">
                    <button
                        onClick={() => {
                            const newState = !isNavCollapsed;
                            setIsNavCollapsed(newState);
                            savePrefs(newState, chatWidth);
                        }}
                        className={`w-full flex items-center ${navCollapsed ? 'justify-center' : 'px-3'} py-2.5 rounded-lg hover:bg-teal-800 text-white transition-colors bg-transparent`}
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
                        className={`w-full mt-1 flex items-center ${navCollapsed ? 'justify-center' : 'px-3'} py-2.5 rounded-lg hover:bg-red-900/20 text-white hover:text-red-400 transition-colors`}
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
                    className={`absolute left-0 top-0 bottom-0 w-72 bg-teal-900 border-r border-teal-800 shadow-2xl transform transition-transform ${isMobileNavOpen ? 'translate-x-0' : '-translate-x-full'}`}
                >
                    <div className="h-16 flex items-center justify-between px-5 border-b border-teal-800">
                        <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg">
                                <Brain className="h-5 w-5 text-white" />
                            </div>
                            <span className="font-outfit font-bold text-lg text-white tracking-tight">Pikar AI</span>
                        </div>
                        <button
                            className="p-2 rounded-lg hover:bg-teal-800 text-white"
                            onClick={() => setIsMobileNavOpen(false)}
                            aria-label="Close navigation"
                        >
                            <X size={18} />
                        </button>
                    </div>

                    <nav className="flex-1 py-6 px-3 space-y-1">
                        {MAIN_INTERFACE_NAV_ITEMS.map((item) => {
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

                    <div className="p-3 border-t border-teal-800">
                        <button
                            onClick={handleSignOut}
                            className="w-full mt-1 flex items-center px-3 py-2.5 rounded-lg hover:bg-red-900/20 text-white hover:text-red-400 transition-colors"
                        >
                            <LogOut size={18} />
                            <span className="ml-3 text-sm font-medium">Sign Out</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Main Wrapper */}
            <div className="flex-1 flex relative overflow-hidden">

                {/* Chat Panel (Conditionally Rendered) */}
                {shouldShowChatPanel && (
                    <>
                        <div
                            className="absolute top-0 left-0 bottom-0 bg-white/50 backdrop-blur-3xl border-r border-slate-200 shadow-[10px_0_40px_-20px_rgba(0,0,0,0.03)] z-20 flex flex-col transition-[width] duration-0 ease-linear"
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
                        marginLeft: shouldShowChatPanel ? `${chatWidth}%` : '0',
                        width: shouldShowChatPanel ? `${100 - chatWidth}%` : '100%'
                    }}
                >
                    <div className="w-full max-w-full p-4 sm:p-6 lg:p-10">
                        <div className="md:hidden mb-4 flex items-center justify-between">
                            <button
                                onClick={() => setIsMobileNavOpen(true)}
                                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
                                aria-label="Open navigation"
                            >
                                <Menu size={16} />
                                Menu
                            </button>
                        </div>
                        {children}
                    </div>
                </main>

            </div>
        </div>
    );
}

function NavItem({ icon, label, collapsed, active, href }: { icon: React.ReactNode, label: string, collapsed: boolean, active?: boolean, href: string }) {
    return (
        <Link
            href={href}
            className={`
                w-full flex items-center ${collapsed ? 'justify-center' : 'px-3'} py-3 rounded-lg transition-all duration-200 group relative
                ${active
                    ? 'bg-gradient-to-r from-teal-800 to-transparent text-white'
                    : 'text-white hover:bg-teal-800 hover:text-white'
                }
            `}
        >
            <span className={`${active ? 'text-white' : 'text-white group-hover:text-white'} transition-colors`}>
                {icon}
            </span>
            {!collapsed && (
                <span className="ml-3 text-sm font-medium font-outfit tracking-wide">
                    {label}
                </span>
            )}

            {/* Active Indicator Bar */}
            {active && (
                <div className="absolute left-0 top-2 bottom-2 w-1 bg-teal-400 rounded-r-full" />
            )}

            {/* Tooltip for collapsed state */}
            {collapsed && (
                <div className="absolute left-full ml-3 px-2 py-1 bg-slate-800 text-white text-[10px] font-medium rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none">
                    {label}
                </div>
            )}
        </Link>
    )
}

export default PremiumShell;
