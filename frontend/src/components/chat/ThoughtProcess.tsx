import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Terminal, Brain, CheckCircle2 } from 'lucide-react';

export type TraceStep = {
    type: 'thinking' | 'tool_use' | 'tool_output';
    content: string;
    toolName?: string;
    isExpanded?: boolean;
};

interface ThoughtProcessProps {
    traces: TraceStep[];
    isThinking?: boolean;
}

export function ThoughtProcess({ traces, isThinking }: ThoughtProcessProps) {
    const [isOpen, setIsOpen] = useState(true);

    if ((!traces || traces.length === 0) && !isThinking) return null;

    return (
        <div className="mb-2 w-full max-w-2xl">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 text-xs font-medium text-slate-500 hover:text-indigo-600 transition-colors mb-2"
            >
                {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <Brain size={14} />
                <span>Thought Process {isThinking && "(Active)"}</span>
            </button>

            {isOpen && (
                <div className="pl-2 ml-1 border-l-2 border-slate-100 dark:border-slate-800 space-y-2">
                    {traces.map((step, idx) => (
                        <div key={idx} className="text-xs text-slate-600 dark:text-slate-400 font-mono">
                            <div className="flex items-start gap-2">
                                <span className="mt-0.5">
                                    {step.type === 'tool_use' ? (
                                        <Terminal size={12} className="text-amber-500" />
                                    ) : step.type === 'tool_output' ? (
                                        <CheckCircle2 size={12} className="text-emerald-500" />
                                    ) : (
                                        <div className="w-3 h-3 rounded-full border border-slate-300" />
                                    )}
                                </span>
                                <div className="flex-1 overflow-hidden">
                                    {step.toolName && (
                                        <span className="font-semibold text-slate-700 dark:text-slate-300 mr-1">
                                            {step.toolName}:
                                        </span>
                                    )}
                                    <span className="break-words opacity-80">{step.content}</span>
                                </div>
                            </div>
                        </div>
                    ))}

                    {isThinking && (
                        <div className="flex items-center gap-2 text-xs text-slate-400 animate-pulse pl-5">
                            <span>Thinking...</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
