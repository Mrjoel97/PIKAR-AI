import React, { useState, useEffect } from 'react';
import { WidgetProps } from './WidgetRegistry';
import { User, Briefcase, TrendingUp, DollarSign, Gavel } from 'lucide-react';

interface TranscriptItem {
    speaker: string;
    content: string;
    sentiment: string;
}

interface BoardroomData {
    topic: string;
    transcript: TranscriptItem[];
    verdict: string;
}

export default function BoardroomWidget({ definition }: WidgetProps) {
    const data = definition.data as unknown as BoardroomData;
    const [visibleItems, setVisibleItems] = useState<TranscriptItem[]>([]);

    // Simulate streaming effect for the widget playback
    useEffect(() => {
        if (!data?.transcript) return;

        let i = 0;
        const interval = setInterval(() => {
            if (i < data.transcript.length) {
                setVisibleItems(prev => [...prev, data.transcript[i]]);
                i++;
            } else {
                clearInterval(interval);
            }
        }, 1500); // 1.5s delay between bubbles

        return () => clearInterval(interval);
    }, [data.transcript]);

    const getAvatar = (speaker: string) => {
        switch (speaker) {
            case 'CMO': return <TrendingUp className="text-blue-500" />;
            case 'CFO': return <DollarSign className="text-red-500" />;
            case 'CEO': return <Gavel className="text-purple-500" />;
            default: return <User className="text-gray-500" />;
        }
    };

    const getBgColor = (speaker: string) => {
        switch (speaker) {
            case 'CMO': return 'bg-blue-50 border-blue-100 dark:bg-blue-900/20 dark:border-blue-800';
            case 'CFO': return 'bg-red-50 border-red-100 dark:bg-red-900/20 dark:border-red-800';
            case 'CEO': return 'bg-purple-50 border-purple-100 dark:bg-purple-900/20 dark:border-purple-800';
            default: return 'bg-gray-50';
        }
    };

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl overflow-hidden flex flex-col h-full max-h-[600px]">
            <div className="p-4 bg-slate-900 text-white flex items-center gap-3">
                <Briefcase size={20} className="text-amber-400" />
                <div>
                    <h3 className="font-bold">The Boardroom</h3>
                    <p className="text-xs text-slate-400">Topic: {data.topic}</p>
                </div>
            </div>

            <div className="p-4 flex-1 overflow-y-auto space-y-4">
                {visibleItems.map((turn, idx) => (
                    <div key={idx} className={`flex gap-3 animate-fade-in-up ${turn.speaker === 'CEO' ? 'justify-center font-bold' : ''}`}>
                        {turn.speaker !== 'CEO' && (
                            <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center shrink-0">
                                {getAvatar(turn.speaker)}
                            </div>
                        )}

                        <div className={`p-4 rounded-2xl max-w-[80%] border ${getBgColor(turn.speaker)}`}>
                            <div className="text-xs font-bold mb-1 opacity-75">{turn.speaker}</div>
                            <p className="text-sm dark:text-slate-200">{turn.content}</p>
                        </div>

                        {turn.speaker === 'CEO' && (
                            <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center shrink-0">
                                {getAvatar(turn.speaker)}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {visibleItems.length === data.transcript.length && (
                <div className="p-4 border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Final Decision</h4>
                    <p className="text-sm text-slate-700 dark:text-slate-300 italic">"{data.verdict}"</p>
                </div>
            )}
        </div>
    );
}
