'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Loader2, MessageSquare, Send } from 'lucide-react';
import { useAdminChat } from '@/hooks/useAdminChat';
import { ConfirmationCard } from './ConfirmationCard';

/**
 * AdminChatPanel is a collapsible chat panel docked to the bottom of the admin layout.
 * It connects to the AdminAgent via SSE and renders ConfirmationCard when the agent
 * requires a high-tier action to be confirmed before execution.
 */
export function AdminChatPanel() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    confirmAction,
    rejectAction,
    pendingConfirmation,
    isConfirming,
  } = useAdminChat();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (isExpanded && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isExpanded]);

  // Focus input when panel expands
  useEffect(() => {
    if (isExpanded && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isExpanded]);

  const handleSend = async () => {
    const text = inputValue.trim();
    if (!text || isStreaming) return;
    setInputValue('');
    await sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className={`fixed bottom-0 right-4 z-50 flex flex-col bg-gray-900 border border-gray-700 rounded-t-xl shadow-2xl transition-all duration-300 ${
        isExpanded ? 'w-96 h-[480px]' : 'w-80 h-12'
      }`}
    >
      {/* Header / toggle bar */}
      <button
        type="button"
        onClick={() => setIsExpanded((v) => !v)}
        className="flex items-center gap-2 px-4 h-12 flex-shrink-0 text-sm font-medium text-gray-200 hover:text-white w-full text-left"
        aria-expanded={isExpanded}
        aria-label={isExpanded ? 'Collapse admin chat' : 'Expand admin chat'}
      >
        <MessageSquare size={16} className="text-indigo-400" />
        <span className="flex-1">Admin Agent</span>
        {isStreaming && <Loader2 size={14} className="animate-spin text-indigo-400" />}
        {isExpanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
      </button>

      {/* Expanded panel body */}
      {isExpanded && (
        <>
          {/* Message list */}
          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
            {messages.map((msg, idx) => {
              if (msg.role === 'system') {
                return (
                  <div key={msg.id ?? idx} className="text-center text-xs text-gray-500 py-1">
                    {msg.text}
                  </div>
                );
              }

              if (msg.role === 'user') {
                return (
                  <div key={msg.id ?? idx} className="flex justify-end">
                    <div className="max-w-[75%] bg-indigo-600 text-white rounded-xl rounded-br-sm px-3 py-2 text-sm break-words">
                      {msg.text}
                    </div>
                  </div>
                );
              }

              // Agent message
              return (
                <div key={msg.id ?? idx} className="flex flex-col gap-1">
                  <div className="flex items-start gap-2">
                    <div className="w-6 h-6 rounded-full bg-indigo-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <MessageSquare size={12} className="text-indigo-200" />
                    </div>
                    <div className="max-w-[85%]">
                      {msg.isThinking ? (
                        <div className="flex items-center gap-1.5 px-3 py-2 bg-gray-800 rounded-xl rounded-bl-sm text-sm text-gray-400">
                          <Loader2 size={12} className="animate-spin" />
                          <span>Thinking…</span>
                        </div>
                      ) : (
                        msg.text && (
                          <div className="px-3 py-2 bg-gray-800 text-gray-100 rounded-xl rounded-bl-sm text-sm break-words whitespace-pre-wrap">
                            {msg.text}
                          </div>
                        )
                      )}
                      {/* Confirmation card inline in message list */}
                      {msg.confirmation && pendingConfirmation?.token === msg.confirmation.token && (
                        <ConfirmationCard
                          confirmation={msg.confirmation}
                          onConfirm={confirmAction}
                          onReject={rejectAction}
                          isProcessing={isConfirming}
                        />
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Error banner */}
          {error && (
            <div className="px-3 py-2 text-xs text-red-400 bg-red-950/40 border-t border-red-800">
              {error}
            </div>
          )}

          {/* Input bar */}
          <div className="flex items-center gap-2 px-3 py-2 border-t border-gray-700 flex-shrink-0">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything about the platform…"
              disabled={isStreaming}
              className="flex-1 bg-gray-800 text-gray-100 text-sm placeholder-gray-500 rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
              aria-label="Admin chat input"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!inputValue.trim() || isStreaming}
              className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors flex-shrink-0"
              aria-label="Send message"
            >
              <Send size={14} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
