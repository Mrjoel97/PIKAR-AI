// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { memo, useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { AlertTriangle, Bot, BookmarkPlus, Check, Clock, Copy, ExternalLink, FolderOpen, Loader2, Maximize2, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { WidgetContainer } from '@/components/widgets/WidgetRegistry';
import { ThoughtProcess } from '@/components/chat/ThoughtProcess';
import { parseTldr, TldrSummary } from '@/components/chat/TldrSummary';
import { parseIntentOptions, IntentClarification } from '@/components/chat/IntentClarification';
import { MessageFeedback } from '@/components/chat/MessageFeedback';
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
    /** When provided, intent clarification option clicks send the selected text as a new message */
    onSendMessage?: (text: string) => void;
    /** Current chat session id — passed through to the Save-to-Vault action so saved notes can be back-linked. */
    sessionId?: string | null;
}

/**
 * Extract the persisted workspace item id (set by `_attach_contract_to_widget`
 * in app/agents/tools/media.py) so we can deep-link the chat widget back to
 * its Vault row. Falls back through widget.data.workspace_item_id and the
 * `workspace.workspaceItemId` envelope.
 */
function getWidgetWorkspaceItemId(widget: WidgetDefinition | undefined): string | undefined {
    if (!widget) return undefined;
    const fromWorkspace = widget.workspace?.workspaceItemId;
    if (typeof fromWorkspace === 'string' && fromWorkspace.trim()) return fromWorkspace;
    const data = (widget.data ?? {}) as Record<string, unknown>;
    const fromData = data.workspace_item_id;
    if (typeof fromData === 'string' && fromData.trim()) return fromData;
    return undefined;
}

function ResearchSummaryCard({ msg }: { msg: Message }) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const research = msg.metadata?.research as any;
    if (!research) return null;

    const confidencePercent = typeof research.confidenceScore === 'number'
        ? Math.round(research.confidenceScore * 100)
        : null;

    return (
        <div className="mt-3 not-prose rounded-xl border border-sky-100 bg-sky-50/80 p-3 text-sm text-slate-700">
            <div className="flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-700">
                    {research.researchType || 'Research'}
                </span>
                {confidencePercent !== null && (
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        confidencePercent >= 80
                            ? 'bg-emerald-100 text-emerald-700'
                            : confidencePercent >= 60
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-rose-100 text-rose-700'
                    }`}>
                        {confidencePercent}% confidence
                    </span>
                )}
            </div>

            {research.topic && (
                <p className="mt-2 text-sm font-semibold text-slate-900">{research.topic}</p>
            )}

            {research.quickAnswer && (
                <p className="mt-2 text-sm leading-relaxed text-slate-700">{research.quickAnswer}</p>
            )}

            {research.citations.length > 0 && (
                <div className="mt-3 space-y-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                        Top citations
                    </p>
                    <div className="space-y-2">
                        {research.citations.slice(0, 3).map((citation: any, citationIndex: number) => {
                            const key = `${citation.url || citation.title}-${citationIndex}`;
                            const label = citation.title || citation.url || 'Untitled source';
                            const body = citation.snippet?.trim() || citation.url;

                            if (citation.url) {
                                return (
                                    <a
                                        key={key}
                                        href={citation.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="block rounded-lg border border-sky-100 bg-white/90 p-2 transition-colors hover:border-sky-200 hover:bg-white"
                                    >
                                        <span className="flex items-center gap-1 font-medium text-slate-900">
                                            {label}
                                            <ExternalLink className="h-3.5 w-3.5 text-slate-400" />
                                        </span>
                                        {body && (
                                            <span className="mt-1 block text-xs leading-relaxed text-slate-600">{body}</span>
                                        )}
                                    </a>
                                );
                            }

                            return (
                                <div key={key} className="rounded-lg border border-sky-100 bg-white/90 p-2">
                                    <span className="font-medium text-slate-900">{label}</span>
                                    {body && (
                                        <span className="mt-1 block text-xs leading-relaxed text-slate-600">{body}</span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {research.contradictions.length > 0 && (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    <div className="flex items-start gap-2">
                        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                        <div>
                            <p className="font-semibold">Potential contradictions</p>
                            <p className="mt-1 leading-relaxed">{research.contradictions[0]}</p>
                        </div>
                    </div>
                </div>
            )}

            {Array.isArray(research.conflicts) && research.conflicts.length > 0 && (
                <div className="mt-3 not-prose rounded-lg border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-900">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-rose-600" />
                        <p className="font-semibold uppercase tracking-[0.14em] text-[11px] text-rose-700">
                            Conflicting sources
                        </p>
                        <span className="inline-flex items-center rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-700">
                            {research.conflicts.length}
                        </span>
                    </div>
                    <p className="mt-1 leading-relaxed text-[11px] text-rose-700/90">
                        Findings where two sources disagree. Inspect both before relying on the claim.
                    </p>
                    <div className="mt-2 space-y-3">
                        {research.conflicts.slice(0, 3).map((conflict: any, conflictIndex: number) => {
                            const claim = (conflict.claim || '').toString().trim();
                            const sourceA = {
                                title: conflict.source_a_title || conflict.sourceATitle || `Source ${conflict.source_a_id ?? conflict.sourceAId ?? 'A'}`,
                                url: conflict.source_a_url || conflict.sourceAUrl || '',
                                excerpt: (conflict.source_a_excerpt || conflict.sourceAExcerpt || '').toString().trim(),
                            };
                            const sourceB = {
                                title: conflict.source_b_title || conflict.sourceBTitle || `Source ${conflict.source_b_id ?? conflict.sourceBId ?? 'B'}`,
                                url: conflict.source_b_url || conflict.sourceBUrl || '',
                                excerpt: (conflict.source_b_excerpt || conflict.sourceBExcerpt || '').toString().trim(),
                            };

                            const renderSourceCard = (source: { title: string; url: string; excerpt: string }, label: string) => (
                                <div className="flex-1 rounded-md border border-rose-100 bg-white/85 p-2">
                                    <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-rose-600">
                                        {label}
                                    </div>
                                    {source.url ? (
                                        <a
                                            href={source.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="mt-1 flex items-center gap-1 text-[12px] font-medium text-slate-900 hover:underline"
                                        >
                                            {source.title}
                                            <ExternalLink className="h-3 w-3 text-slate-400" />
                                        </a>
                                    ) : (
                                        <span className="mt-1 block text-[12px] font-medium text-slate-900">{source.title}</span>
                                    )}
                                    {source.excerpt && (
                                        <p className="mt-1 text-[11px] leading-relaxed text-slate-600">
                                            {source.excerpt.slice(0, 200)}
                                        </p>
                                    )}
                                </div>
                            );

                            return (
                                <div
                                    key={`conflict-${conflictIndex}`}
                                    className="rounded-md border border-rose-100 bg-white/60 p-2"
                                    data-testid="research-conflict"
                                >
                                    {claim && (
                                        <p className="text-[12px] font-medium leading-relaxed text-slate-900">
                                            {claim}
                                        </p>
                                    )}
                                    <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                                        {renderSourceCard(sourceA, 'Source A')}
                                        {renderSourceCard(sourceB, 'Source B')}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    {research.conflicts.length > 3 && (
                        <p className="mt-2 text-[11px] text-rose-700/80">
                            + {research.conflicts.length - 3} more conflict(s) in the saved Vault report.
                        </p>
                    )}
                </div>
            )}

            {research.recommendedNextQuestions.length > 0 && (
                <div className="mt-3 space-y-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                        Recommended next questions
                    </p>
                    <div className="flex flex-wrap gap-2">
                        {research.recommendedNextQuestions.slice(0, 2).map((question: any) => (
                            <span
                                key={question}
                                className="rounded-full border border-sky-200 bg-white/90 px-2.5 py-1 text-xs text-slate-700"
                            >
                                {question}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export const MessageItem = memo(function MessageItem({
    msg,
    index,
    onToggleWidgetMinimized,
    onWidgetAction,
    onWidgetDismiss,
    onViewInWorkspace,
    onSendMessage,
    sessionId,
}: MessageItemProps) {
    const [copied, setCopied] = useState(false);
    const [savingToVault, setSavingToVault] = useState(false);
    const [savedToVault, setSavedToVault] = useState(false);
    const router = useRouter();
    const isMediaWidget = msg.widget && (msg.widget.type === 'image' || msg.widget.type === 'video' || msg.widget.type === 'video_spec');
    const widgetWorkspaceItemId = getWidgetWorkspaceItemId(msg.widget);
    const handleMediaClick = () => {
        if (msg.widget && onViewInWorkspace) onViewInWorkspace(msg.widget);
    };
    const handleCopyMessage = useCallback(async () => {
        const text = msg.text?.trim();
        if (!text || typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
            return;
        }

        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1800);
        } catch (error) {
            console.warn('Failed to copy chat message:', error);
        }
    }, [msg.text]);

    const handleSaveToVault = useCallback(async () => {
        const text = msg.text?.trim();
        if (!text || savingToVault) return;
        setSavingToVault(true);
        try {
            const resp = await fetch('/api/vault/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: text,
                    type: 'note',
                    session_id: sessionId ?? null,
                }),
            });
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            setSavedToVault(true);
            toast.success('Saved to Vault');
            window.setTimeout(() => setSavedToVault(false), 2200);
        } catch (err) {
            console.warn('[MessageItem] Save to Vault failed:', err);
            toast.error("Couldn't save — try again");
        } finally {
            setSavingToVault(false);
        }
    }, [msg.text, savingToVault, sessionId]);

    const handleFindInVault = useCallback(() => {
        if (!widgetWorkspaceItemId) return;
        router.push(`/dashboard/vault?item=${encodeURIComponent(widgetWorkspaceItemId)}`);
    }, [router, widgetWorkspaceItemId]);

    return (
        <div className={`group/message flex gap-3 max-w-full overflow-hidden ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

            {msg.role !== 'user' && (
                <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-teal-100">
                    {msg.role === 'system' ? <span className="text-red-500">!</span> : <Bot size={16} className="text-teal-600" />}
                </div>
            )}

            <div className={`flex min-w-0 flex-col ${(msg.widget?.type === 'image' || msg.widget?.type === 'video' || msg.widget?.type === 'video_spec') ? 'max-w-full w-full' : 'max-w-[95%] sm:max-w-[85%] md:max-w-[75%]'} ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.agentName && msg.role === 'agent' && (
                    <span className="mb-1 ml-1 text-xs text-slate-400">{msg.agentName}</span>
                )}

                {msg.role === 'agent' && msg.traces && msg.traces.length > 0 && (
                    <ThoughtProcess traces={msg.traces} isThinking={msg.isThinking} />
                )}

                {(msg.text || msg.isThinking || msg.metadata?.research || (msg.role === 'agent' && msg.widget && !msg.text)) && (() => {
                    // Detect TL;DR block in agent messages (before default markdown)
                    const tldrData = msg.role === 'agent' && msg.text ? parseTldr(msg.text) : null;
                    const afterTldr = tldrData ? tldrData.remainingText : msg.text;

                    // Detect intent clarification block (before default markdown)
                    const intentData = msg.role === 'agent' && afterTldr ? parseIntentOptions(afterTldr) : null;
                    const displayText = intentData ? intentData.remainingText : afterTldr;

                    return (
                    <div className={`relative max-w-full overflow-hidden break-words rounded-2xl p-3 sm:p-4 shadow-sm ${msg.role === 'user'
                        ? 'prose-invert bg-teal-900 text-white rounded-br-none'
                        : msg.role === 'system'
                            ? 'prose prose-sm max-w-none bg-red-50 text-red-600 border border-red-100'
                            : 'prose prose-sm max-w-none bg-white text-slate-700 border border-slate-100/80 rounded-bl-none'
                        }`}>
                        {msg.role === 'user' && msg.text && (
                            <button
                                type="button"
                                onClick={handleCopyMessage}
                                className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-md bg-white/10 px-2 py-1 text-[11px] font-medium text-white/85 transition-colors hover:bg-white/20"
                                title="Copy your message"
                            >
                                {copied ? <Check size={12} /> : <Copy size={12} />}
                                {copied ? 'Copied' : 'Copy'}
                            </button>
                        )}
                        {tldrData && (
                            <TldrSummary
                                summary={tldrData.summary}
                                keyNumber={tldrData.keyNumber}
                                nextStep={tldrData.nextStep}
                            />
                        )}
                        {intentData ? (
                            <>
                                <IntentClarification
                                    introText={intentData.introText}
                                    options={intentData.options}
                                    onSelect={(text) => onSendMessage?.(text)}
                                />
                                {intentData.remainingText && (
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {intentData.remainingText}
                                    </ReactMarkdown>
                                )}
                            </>
                        ) : msg.isThinking && !msg.text ? (
                            <div className="flex items-center gap-2 text-slate-400">
                                <Loader2 size={14} className="animate-spin" />
                                <span className="text-xs">Thinking...</span>
                            </div>
                        ) : msg.role === 'user' ? (
                            <div className="pr-14 text-sm leading-6 whitespace-pre-wrap break-words select-text">
                                {displayText || ''}
                            </div>
                        ) : (
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {displayText || (msg.widget?.type === 'video' || msg.widget?.type === 'video_spec'
                                    ? 'Here\'s your video. You can play it below and find it in Knowledge Vault → Media.'
                                    : msg.widget?.type === 'image'
                                        ? 'Here\'s your image. You can view it below and find it in Knowledge Vault → Media.'
                                        : msg.widget
                                            ? 'Here\'s what I created for you.'
                                            : '')}
                            </ReactMarkdown>
                        )}

                        <ResearchSummaryCard msg={msg} />

                        {msg.isQueued && (
                            <div className="mt-2 flex w-fit items-center gap-1.5 rounded-md bg-teal-700/30 px-2 py-1 text-xs font-medium text-teal-200/90">
                                <Clock size={12} className="animate-pulse" />
                                <span>Queued...</span>
                            </div>
                        )}
                    </div>
                    );
                })()}

                {msg.role === 'agent' && !msg.isThinking && (
                    <div className="mt-1 flex items-center gap-2">
                        {msg.interactionId && (
                            <MessageFeedback interactionId={msg.interactionId} />
                        )}
                        {msg.text?.trim() && (
                            <button
                                type="button"
                                onClick={handleSaveToVault}
                                disabled={savingToVault || savedToVault}
                                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-400 opacity-0 transition-all hover:bg-teal-50 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-60 group-hover/message:opacity-100 focus:opacity-100"
                                title="Save this message to the Knowledge Vault"
                                aria-label="Save to Vault"
                                data-testid="save-to-vault"
                            >
                                {savingToVault ? (
                                    <Loader2 size={12} className="animate-spin" />
                                ) : savedToVault ? (
                                    <Check size={12} />
                                ) : (
                                    <BookmarkPlus size={12} />
                                )}
                                <span>{savedToVault ? 'Saved' : savingToVault ? 'Saving...' : 'Save to Vault'}</span>
                            </button>
                        )}
                    </div>
                )}

                {msg.widget && isMediaWidget && widgetWorkspaceItemId && (
                    <button
                        type="button"
                        onClick={handleFindInVault}
                        className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-2.5 py-1 text-[11px] font-medium text-teal-700 transition-colors hover:bg-teal-100"
                        title="Find this asset in the Knowledge Vault"
                        data-testid="find-in-vault"
                    >
                        <FolderOpen size={12} />
                        Find in Vault
                    </button>
                )}

                {msg.widget && (
                    <div className={`relative mt-2 overflow-hidden group ${isMediaWidget ? 'w-full max-w-full' : 'w-full max-w-full'}`}>
                        {isMediaWidget && onViewInWorkspace ? (
                            <div
                                onClick={(e) => {
                                    if ((e.target as HTMLElement).closest('button, [role="button"]')) return;
                                    handleMediaClick();
                                }}
                                className="w-full cursor-pointer overflow-hidden rounded-xl border-2 border-transparent text-left transition-colors hover:border-teal-300 focus-within:border-teal-300"
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
                                <span className="pointer-events-none absolute right-2 top-2 flex items-center gap-1.5 rounded-lg bg-slate-800/80 px-2 py-1.5 text-xs font-medium text-white opacity-0 transition-opacity group-hover:opacity-100">
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
                                        className="absolute right-2 top-2 z-10 inline-flex items-center gap-1 rounded-md bg-slate-900/80 px-2 py-1 text-[11px] font-medium text-white transition-colors hover:bg-slate-900"
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
                <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-200">
                    <User size={16} className="text-slate-500" />
                </div>
            )}
        </div>
    );
});
