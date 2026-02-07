'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    LayoutDashboard,
    MessageSquare,
    Settings,
    PieChart,
    ChevronLeft,
    ChevronRight,
    LogOut,
    Zap,
    FileText,
    CreditCard,
    BookOpen,
    Globe,
    LifeBuoy,
    Brain,
    Database,
    Users
} from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { usePathname } from 'next/navigation';
import Link from 'next/link';

interface PremiumShellProps {
    children: React.ReactNode;
    chatPanel?: React.ReactNode;
}

export function PremiumShell({ children, chatPanel }: PremiumShellProps) {
    const [isNavCollapsed, setIsNavCollapsed] = useState(false);
    const [chatWidth, setChatWidth] = useState(25); // Percentage of available width
    const [isResizing, setIsResizing] = useState(false);
    const pathname = usePathname();

    // Persist layout preferences
    useEffect(() => {
        const saved = localStorage.getItem('pikar_layout_prefs');
        if (saved) {
            const { nav, chat } = JSON.parse(saved);
            setIsNavCollapsed(nav);
            setChatWidth(chat);
        }
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
            const sidebarWidth = isNavCollapsed ? 60 : 260; // Approximate sidebar width

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
    }, [isResizing, isNavCollapsed]);

    const handleSignOut = async () => {
        const supabase = createClient();
        await supabase.auth.signOut();
        window.location.href = '/';
    };

    const COLLAPSED_WIDTH = '60px';
    const EXPANDED_WIDTH = '260px';

    return (
        <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden font-inter selection:bg-teal-100 selection:text-teal-900">

            {/* Left Navigation Sidebar */}
            <motion.aside
                initial={false}
                animate={{ width: isNavCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH }}
                className="relative z-30 flex flex-col bg-teal-900 backdrop-blur-xl border-r border-teal-800 shadow-[2px_0_24px_-12px_rgba(0,0,0,0.08)] transition-all duration-300 ease-in-out shrink-0"
            >
                {/* Logo Area */}
                <div className={`h-16 flex items-center ${isNavCollapsed ? 'justify-center' : 'px-6 justify-between'} transition-all`}>
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg">
                            <Brain className="h-5 w-5 text-white" />
                        </div>
                        {!isNavCollapsed && (
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
                    <NavItem href="/dashboard/command-center" icon={<LayoutDashboard size={20} />} label="Command Center" collapsed={isNavCollapsed} active={pathname?.includes('/command-center')} />
                    <NavItem href="/dashboard/workspace" icon={<Zap size={20} />} label="My Workspace" collapsed={isNavCollapsed} active={pathname?.includes('/workspace')} />
                    <NavItem href="/dashboard/reports" icon={<PieChart size={20} />} label="Reports" collapsed={isNavCollapsed} active={pathname?.includes('/reports')} />
                    <NavItem href="/dashboard/vault" icon={<Database size={20} />} label="Knowledge Vault" collapsed={isNavCollapsed} active={pathname?.includes('/vault')} />
                    <NavItem href="/dashboard/community" icon={<Globe size={20} />} label="Join Community" collapsed={isNavCollapsed} active={pathname?.includes('/community')} />
                    <NavItem href="/dashboard/learning" icon={<BookOpen size={20} />} label="Learning Hub" collapsed={isNavCollapsed} active={pathname?.includes('/learning')} />
                    <NavItem href="/dashboard/support" icon={<LifeBuoy size={20} />} label="Contact Support" collapsed={isNavCollapsed} active={pathname?.includes('/support')} />
                    <NavItem href="/dashboard/history" icon={<MessageSquare size={20} />} label="Chat History" collapsed={isNavCollapsed} active={pathname?.includes('/history')} />
                    <NavItem href="/dashboard/billing" icon={<CreditCard size={20} />} label="Billing & Subscription" collapsed={isNavCollapsed} active={pathname?.includes('/billing')} />
                    <NavItem href="/dashboard/configuration" icon={<Settings size={20} />} label="Configuration" collapsed={isNavCollapsed} active={pathname?.includes('/configuration')} />
                </nav>

                {/* Footer / Collapse Toggle */}
                <div className="p-3 border-t border-teal-800">
                    <button
                        onClick={() => {
                            const newState = !isNavCollapsed;
                            setIsNavCollapsed(newState);
                            savePrefs(newState, chatWidth);
                        }}
                        className={`w-full flex items-center ${isNavCollapsed ? 'justify-center' : 'px-3'} py-2.5 rounded-lg hover:bg-teal-800 text-white transition-colors bg-transparent`}
                    >
                        {isNavCollapsed ? <ChevronRight size={18} /> : (
                            <>
                                <ChevronLeft size={18} />
                                <span className="ml-3 text-sm font-medium">Collapse</span>
                            </>
                        )}
                    </button>

                    <button
                        onClick={handleSignOut}
                        className={`w-full mt-1 flex items-center ${isNavCollapsed ? 'justify-center' : 'px-3'} py-2.5 rounded-lg hover:bg-red-900/20 text-white hover:text-red-400 transition-colors`}
                    >
                        <LogOut size={18} />
                        {!isNavCollapsed && <span className="ml-3 text-sm font-medium">Sign Out</span>}
                    </button>
                </div>
            </motion.aside>

            {/* Main Wrapper */}
            <div className="flex-1 flex relative overflow-hidden">

                {/* Chat Panel (Conditionally Rendered) */}
                {chatPanel && (
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
                        marginLeft: chatPanel ? `${chatWidth}%` : '0',
                        width: chatPanel ? `${100 - chatWidth}%` : '100%'
                    }}
                >
                    <div className="w-full max-w-full p-6 lg:p-10">
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
