'use client';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { CommandCenter } from '@/components/dashboard/CommandCenter';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { PersonaType } from '@/services/onboarding';
import { usePersona } from '@/contexts/PersonaContext';
import { AlertCircle, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface PersonaDashboardLayoutProps {
    persona: PersonaType;
    title: string;
    description: string;
    children?: React.ReactNode;
    agentName?: string;
    showChat?: boolean;
}

export default function PersonaDashboardLayout({ persona: routePersona, title, description, children, agentName, showChat = false }: PersonaDashboardLayoutProps) {
    const { persona: currentPersona, isLoading } = usePersona();

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
            chatPanel={showChat ? (
                <div className="h-full flex flex-col bg-slate-50 border-l border-slate-200">
                    <div className="p-4 border-b border-slate-200 bg-white/80 backdrop-blur-md">
                        <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2 font-outfit tracking-wide">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
                            </span>
                            {agentName || 'AI Assistant'}
                        </h3>
                    </div>
                    <div className="flex-1 overflow-hidden relative">
                        <ChatInterface
                            initialSessionId={undefined}
                            className="h-full border-none shadow-none rounded-none bg-transparent"
                            agentName={agentName}
                        />
                    </div>
                </div>
            ) : undefined}
        >
            <div className="relative">
                {isMismatch && (
                    <div className="mb-6 mx-6 mt-6 p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-amber-800 animate-in fade-in slide-in-from-top-4">
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
                {children || <CommandCenter user={{}} persona={routePersona} />}
            </div>
        </PremiumShell>
    );
}
