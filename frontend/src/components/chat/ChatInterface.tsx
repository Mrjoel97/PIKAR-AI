'use client'
import React, { useEffect, useRef } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAgentChat } from '@/hooks/useAgentChat'

export function ChatInterface() {
  const { messages, sendMessage, isStreaming } = useAgentChat();
  const [input, setInput] = React.useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput('');
  }

  return (
    <div className="flex flex-col h-[600px] bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
      {/* Header */}
      <div className="bg-slate-50 dark:bg-slate-800/50 p-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg text-indigo-600 dark:text-indigo-400">
            <Bot size={20} />
        </div>
        <div>
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">Pikar AI</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Executive Assistant & Orchestrator</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-6 bg-slate-50/50 dark:bg-slate-900/50">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            
            {msg.role !== 'user' && (
                <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center flex-shrink-0 mt-1">
                    {msg.role === 'system' ? <span className="text-red-500">!</span> : <Bot size={16} className="text-indigo-600 dark:text-indigo-400" />}
                </div>
            )}

            <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.agentName && msg.role === 'agent' && (
                    <span className="text-xs text-slate-400 mb-1 ml-1">{msg.agentName}</span>
                )}
                
                <div className={`p-4 rounded-2xl shadow-sm prose prose-sm dark:prose-invert max-w-none ${
                    msg.role === 'user' 
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
                            {msg.text}
                        </ReactMarkdown>
                    )}
                </div>
            </div>

            {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0 mt-1">
                    <User size={16} className="text-slate-500 dark:text-slate-300" />
                </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
        <div className="relative flex items-center">
            <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isStreaming && handleSend()}
            disabled={isStreaming}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 pr-12 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition disabled:opacity-50 disabled:cursor-not-allowed text-black dark:text-white"
            placeholder="Type your message..."
            />
            <button 
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="absolute right-2 p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-sm cursor-pointer"
            >
            {isStreaming ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
        </div>
        <p className="text-center text-xs text-slate-400 mt-2">
            Pikar AI can make mistakes. Consider checking important information.
        </p>
      </div>
    </div>
  )
}