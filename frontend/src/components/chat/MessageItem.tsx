import React, { memo } from 'react';
import { Bot, User, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { WidgetContainer } from '@/components/widgets/WidgetRegistry';
import { ThoughtProcess } from '@/components/chat/ThoughtProcess';
import type { Message } from '@/hooks/useAgentChat';

export interface MessageItemProps {
    msg: Message;
    index: number;
    onToggleWidgetMinimized: (index: number) => void;
    onWidgetAction: (index: number, action: string, payload?: unknown) => void;
    onWidgetDismiss: (index: number) => void;
}

export const MessageItem = memo(function MessageItem({
    msg,
    index,
    onToggleWidgetMinimized,
    onWidgetAction,
    onWidgetDismiss
}: MessageItemProps) {
    return (
        <div className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

            {msg.role !== 'user' && (
                <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center flex-shrink-0 mt-1">
                    {msg.role === 'system' ? <span className="text-red-500">!</span> : <Bot size={16} className="text-indigo-600 dark:text-indigo-400" />}
                </div>
            )}

            <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.agentName && msg.role === 'agent' && (
                    <span className="text-xs text-slate-400 mb-1 ml-1">{msg.agentName}</span>
                )}

                {/* Thought Process (Traces) */}
                {msg.traces && msg.traces.length > 0 && (
                    <ThoughtProcess traces={msg.traces} isThinking={msg.isThinking} />
                )}

                {/* Text Content */}
                {(msg.text || msg.isThinking) && (
                    <div className={`p-4 rounded-2xl shadow-sm prose prose-sm dark:prose-invert max-w-none ${msg.role === 'user'
                        ? 'bg-indigo-600 text-white rounded-br-none'
                        : msg.role === 'system'
                            ? 'bg-red-50 text-red-600 border border-red-100'
                            : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-100 dark:border-slate-700 rounded-bl-none'
                        }`}>
                        {msg.isThinking && !msg.text ? (
                            <div className="flex items-center gap-2 text-slate-400">
                                <Loader2 size={14} className="animate-spin" />
                                <span className="text-xs">Thinking...</span>
                            </div>
                        ) : (
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.text || ''}
                            </ReactMarkdown>
                        )}
                    </div>
                )}

                {/* Widget Content */}
                {msg.widget && (
                    <div className="mt-2 w-full min-w-[300px] max-w-[500px]">
                        <WidgetContainer
                            definition={msg.widget}
                            isMinimized={msg.isMinimized}
                            onToggleMinimized={() => onToggleWidgetMinimized(index)}
                            onAction={(action, payload) => onWidgetAction(index, action, payload)}
                            showPinButton={true}
                            onDismiss={() => onWidgetDismiss(index)}
                        />
                    </div>
                )}
            </div>

            {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0 mt-1">
                    <User size={16} className="text-slate-500 dark:text-slate-300" />
                </div>
            )}
        </div>
    );
});
