'use client';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { CommandCenter } from '@/components/dashboard/CommandCenter';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { PersonaType } from '@/services/onboarding';

interface PersonaDashboardLayoutProps {
    persona: PersonaType;
    title: string;
    description: string;
    children?: React.ReactNode;
    agentName?: string;
    showChat?: boolean;
}

export default function PersonaDashboardLayout({ persona, title, description, children, agentName, showChat = false }: PersonaDashboardLayoutProps) {
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
            {children || <CommandCenter user={{}} persona={persona} />}
        </PremiumShell>
    );
}
