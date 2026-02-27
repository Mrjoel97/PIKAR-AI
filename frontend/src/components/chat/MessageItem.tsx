import React, { memo } from 'react';
import { Bot, User, Loader2, Maximize2, Clock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { WidgetContainer } from '@/components/widgets/WidgetRegistry';
import { ThoughtProcess } from '@/components/chat/ThoughtProcess';
import type { Message } from '@/hooks/useAgentChat';
import type { WidgetDefinition } from '@/types/widgets';

export interface MessageItemProps {
    msg: Message;
    index: number;
    onToggleWidgetMinimized: (index: number) => void;
    onWidgetAction: (index: number, action: string, payload?: unknown) => void;
    onWidgetDismiss: (index: number) => void;
    /** When provided, media widgets (image/video/video_spec) are clickable to view in workspace */
    onViewInWorkspace?: (widget: WidgetDefinition) => void;
}

export const MessageItem = memo(function MessageItem({
    msg,
    index,
    onToggleWidgetMinimized,
    onWidgetAction,
    onWidgetDismiss,
    onViewInWorkspace,
}: MessageItemProps) {
    const isMediaWidget = msg.widget && (msg.widget.type === 'image' || msg.widget.type === 'video' || msg.widget.type === 'video_spec');
    const handleMediaClick = () => {
        if (msg.widget && onViewInWorkspace) onViewInWorkspace(msg.widget);
    };
    return (
        <div className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

            {msg.role !== 'user' && (
                <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center flex-shrink-0 mt-1">
                    {msg.role === 'system' ? <span className="text-red-500">!</span> : <Bot size={16} className="text-indigo-600 dark:text-indigo-400" />}
                </div>
            )}

            <div className={`flex flex-col min-w-0 ${(msg.widget?.type === 'image' || msg.widget?.type === 'video' || msg.widget?.type === 'video_spec') ? 'max-w-full w-full' : 'max-w-[85%]'} ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.agentName && msg.role === 'agent' && (
                    <span className="text-xs text-slate-400 mb-1 ml-1">{msg.agentName}</span>
                )}

                {/* Thought Process (Traces) */}
                {msg.traces && msg.traces.length > 0 && (
                    <ThoughtProcess traces={msg.traces} isThinking={msg.isThinking} />
                )}

                {/* Text Content — show when there is text, thinking, or widget (fallback so response is never blank) */}
                {(msg.text || msg.isThinking || (msg.role === 'agent' && msg.widget && !msg.text)) && (
                    <div className={`p-4 rounded-2xl shadow-sm prose prose-sm dark:prose-invert max-w-none break-words overflow-hidden ${msg.role === 'user'
                        ? 'bg-teal-900 text-white rounded-br-none'
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
                                {msg.text || (msg.widget?.type === 'video' || msg.widget?.type === 'video_spec'
                                    ? 'Here\'s your video. You can play it below and find it in Knowledge Vault → Media.'
                                    : msg.widget?.type === 'image'
                                        ? 'Here\'s your image. You can view it below and find it in Knowledge Vault → Media.'
                                        : msg.widget
                                            ? 'Here\'s what I created for you.'
                                            : '')}
                            </ReactMarkdown>
                        )}
                        {msg.isQueued && (
                            <div className="flex items-center gap-1.5 mt-2 text-xs font-medium text-indigo-200/90 bg-indigo-700/30 px-2 py-1 rounded-md w-fit">
                                <Clock size={12} className="animate-pulse" />
                                <span>Queued...</span>
                            </div>
                        )}
                    </div>
                )}

                {/* Widget Content */}
                {msg.widget && (
                    <div className={`mt-2 overflow-hidden relative group ${isMediaWidget ? 'w-full max-w-full' : 'w-full max-w-full'}`}>
                        {isMediaWidget && onViewInWorkspace ? (
                            <div
                                onClick={(e) => {
                                    // Only trigger view-in-workspace when clicking the wrapper itself or the overlay label, not inner buttons (e.g. VideoSpecWidget "Show code")
                                    if ((e.target as HTMLElement).closest('button, [role="button"]')) return;
                                    handleMediaClick();
                                }}
                                className="w-full text-left rounded-xl overflow-hidden border-2 border-transparent hover:border-indigo-300 focus-within:border-indigo-300 transition-colors cursor-pointer"
                                title="Click to view in workspace"
                            >
                                <WidgetContainer
                                    definition={msg.widget}
                                    isMinimized={false}
                                    onToggleMinimized={() => onToggleWidgetMinimized(index)}
                                    onAction={(action, payload) => onWidgetAction(index, action, payload)}
                                    showPinButton={false}
                                    onDismiss={() => onWidgetDismiss(index)}
                                    fullFocus={true}
                                />
                                <span className="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-slate-800/80 text-white text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                                    <Maximize2 size={14} />
                                    View in workspace
                                </span>
                            </div>
                        ) : (
                            <div className="relative">
                                {onViewInWorkspace && (
                                    <button
                                        type="button"
                                        onClick={() => onViewInWorkspace(msg.widget!)}
                                        className="absolute top-2 right-2 z-10 inline-flex items-center gap-1 px-2 py-1 rounded-md bg-slate-900/80 text-white text-[11px] font-medium hover:bg-slate-900 transition-colors"
                                        title="Open in workspace"
                                    >
                                        <Maximize2 size={12} />
                                        Open
                                    </button>
                                )}
                                <WidgetContainer
                                    definition={msg.widget}
                                    isMinimized={msg.isMinimized}
                                    onToggleMinimized={() => onToggleWidgetMinimized(index)}
                                    onAction={(action, payload) => onWidgetAction(index, action, payload)}
                                    showPinButton={true}
                                    onDismiss={() => onWidgetDismiss(index)}
                                    fullFocus={msg.widget.type === 'image' || msg.widget.type === 'video' || msg.widget.type === 'video_spec'}
                                />
                            </div>
                        )}
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
