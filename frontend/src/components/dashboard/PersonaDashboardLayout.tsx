import React from 'react';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { WidgetContainer } from '@/components/widgets/WidgetRegistry';
import { User, Sparkles, Zap, TrendingUp, Shield } from 'lucide-react';

interface PersonaDashboardLayoutProps {
    persona: 'solopreneur' | 'startup' | 'sme' | 'enterprise';
    title: string;
    description: string;
}

const PERSONA_CONFIG = {
    solopreneur: {
        icon: Zap,
        color: 'text-amber-500',
        bg: 'bg-amber-50 dark:bg-amber-900/20',
        widgetTitle: "Growth Hacks"
    },
    startup: {
        icon: TrendingUp,
        color: 'text-indigo-500',
        bg: 'bg-indigo-50 dark:bg-indigo-900/20',
        widgetTitle: "Scale Ops"
    },
    sme: {
        icon: User,
        color: 'text-blue-500',
        bg: 'bg-blue-50 dark:bg-blue-900/20',
        widgetTitle: "Department Feed"
    },
    enterprise: {
        icon: Shield,
        color: 'text-slate-500',
        bg: 'bg-slate-50 dark:bg-slate-800/20',
        widgetTitle: "Strategic Intel"
    }
};

const MOCK_SUGGESTIONS = {
    type: 'suggested_workflows',
    data: {
        suggestions: [
            {
                id: 'w_1',
                pattern_description: 'You frequently ask for competitor pricing summaries and then draft emails.',
                suggested_goal: 'Automate Competitor Monitoring',
                suggested_context: 'Based on your activity last Tuesday',
                status: 'pending'
            },
            {
                id: 'w_2',
                pattern_description: 'Weekly sales report generation followed by team channel post.',
                suggested_goal: 'Auto-Post Weekly Sales Stats',
                suggested_context: 'Detected recurring pattern',
                status: 'pending'
            }
        ]
    }
};

export default function PersonaDashboardLayout({ persona, title, description }: PersonaDashboardLayoutProps) {
    const config = PERSONA_CONFIG[persona];
    const Icon = config.icon;

    return (
        <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">

            {/* Top Bar */}
            <header className="px-6 py-4 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${config.bg} ${config.color}`}>
                        <Icon size={24} />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white">{title}</h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400">{description}</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <div className="px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-600 dark:text-slate-400">
                        Persona: {persona.toUpperCase()}
                    </div>
                </div>
            </header>

            {/* Main Content Grid */}
            <main className="flex-1 overflow-hidden p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Left: Chat Interface (2/3 width) */}
                <div className="lg:col-span-2 flex flex-col">
                    <ChatInterface initialSessionId={undefined} />
                </div>

                {/* Right: Smart Feed / Widgets (1/3 width) */}
                <div className="flex flex-col gap-6 overflow-y-auto">

                    {/* Continuous Learning Widget */}
                    <WidgetContainer
                        definition={MOCK_SUGGESTIONS}
                        onAction={(a, p) => console.log(a, p)}
                        isMinimized={false}
                    />

                    {/* Placeholder for other persona widgets */}
                    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-400 text-sm text-center border-dashed">
                        Additional {config.widgetTitle} Widgets appear here...
                    </div>
                </div>

            </main>
        </div>
    );
}
