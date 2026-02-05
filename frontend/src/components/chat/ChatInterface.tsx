'use client'
import React, { useEffect, useRef } from 'react'
import { Send, Bot, User, Loader2, Paperclip, Mic } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAgentChat } from '@/hooks/useAgentChat'
import { WidgetContainer } from '@/components/widgets/WidgetRegistry'
import { ThoughtProcess } from '@/components/chat/ThoughtProcess'
import { FileDropZone } from '@/components/chat/FileDropZone'
import { useFileUpload } from '@/hooks/useFileUpload'
import { WidgetDisplayService } from '@/services/widgetDisplay'
import { createClient } from '@/lib/supabase/client'
import { useRealtimeSession } from '@/hooks/useRealtimeSession';
import { usePresence } from '@/hooks/usePresence';

export interface ChatInterfaceProps {
  initialSessionId?: string;
  className?: string;
  agentName?: string;
}

export function ChatInterface({ initialSessionId, className, agentName }: ChatInterfaceProps) {
  const { messages, sendMessage, addMessage, isStreaming, toggleWidgetMinimized, isLoadingHistory } = useAgentChat(initialSessionId);
  const { uploadFile, isUploading } = useFileUpload();
  const [input, setInput] = React.useState('');
  const [isRecording, setIsRecording] = React.useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const widgetService = useRef(new WidgetDisplayService());

  // NEW: Get user info for presence
  const supabase = createClient();
  const [currentUserId, setCurrentUserId] = React.useState<string>('');

  React.useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) setCurrentUserId(data.user.id);
    });
  }, []);

  // NEW: Realtime session updates
  useRealtimeSession({
    sessionId: initialSessionId || '',
    userId: currentUserId,
    onNewEvent: (event) => {
      console.log('New session event received:', event);

      // Parse event content similar to useAgentChat logic
      let text = '';
      const eventData = event.event_data || event; // Handle flattened or nested structure

      if (eventData.content?.parts) {
        text = eventData.content.parts.map((p: any) => p.text || '').join('');
      } else if (typeof eventData.content === 'string') {
        text = eventData.content;
      }

      // Check if we should add this message (avoid duplicating our own if local optimistic update handled it?)
      // For now, assume realtime events are for OTHER users or async agent updates not caught by SSE
      if (text || eventData.widget) {
        addMessage({
          role: eventData.source === 'user' ? 'user' : 'agent',
          text: text,
          agentName: eventData.source,
          widget: eventData.widget
        });
      }
    },
  });

  // NEW: Presence tracking
  const { onlineUsers } = usePresence(
    initialSessionId ? `chat:${initialSessionId}` : null,
    currentUserId,
    'User' // Could fetch from user profile
  );

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

  const handleWidgetAction = async (messageIndex: number, action: string, payload?: unknown) => {
    const msg = messages[messageIndex];
    if (action === 'pin' && msg.widget) {
      const supabase = createClient();
      const { data } = await supabase.auth.getUser();
      if (data.user) {
        const wAny = msg.widget as any;
        if (wAny.id) {
          widgetService.current.pinWidget(wAny.id, data.user.id);
        } else {
          // Fallback: manually save as pinned if no ID, but hook should have injected it on reception
          const saved = widgetService.current.saveWidget(data.user.id, initialSessionId || 'default', msg.widget, true);
          if (saved) {
            (msg.widget as any).id = saved.id;
          }
        }
      }
    }
    console.log('Widget action:', { messageIndex, action, payload });
  };

  const handleFileDrop = async (file: File) => {
    if (isStreaming || isUploading) return;

    // Optimistic UI update could go here (e.g., "Uploading...")
    const result = await uploadFile(file);

    if (result) {
      // Send the agent prompt constructed by the backend
      sendMessage(result.summary_prompt);
    }
  };

  return (
    <div className={className || "relative h-[600px] bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800 overflow-hidden"}>
      <FileDropZone onFileDrop={handleFileDrop} disabled={isStreaming || isUploading}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="bg-slate-50 dark:bg-slate-800/50 p-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-teal-500 to-cyan-500 flex items-center justify-center text-white font-bold shadow-lg shadow-teal-500/20">
              {agentName ? agentName.charAt(0).toUpperCase() : <Bot size={20} />}
            </div>
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-slate-100 font-outfit">
                {agentName || 'Pikar AI'}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {agentName ? 'Personal Agent' : 'Executive Assistant & Orchestrator'}
              </p>
            </div>
            {/* NEW: Online users indicator */}
            {onlineUsers.length > 1 && (
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span>{onlineUsers.length} online</span>
              </div>
            )}
          </div>

          {isLoadingHistory && (
            <div className="absolute inset-0 z-10 bg-white/50 dark:bg-slate-900/50 flex items-center justify-center backdrop-blur-sm">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">Loading conversation...</span>
              </div>
            </div>
          )}

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
                        onToggleMinimized={() => toggleWidgetMinimized(i)}
                        onAction={(action, payload) => handleWidgetAction(i, action, payload)}
                        showPinButton={true}
                        onDismiss={() => {
                          console.log('Widget dismissed at index:', i);
                        }}
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
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
            <div className="relative flex items-center">
              <button
                onClick={() => document.getElementById('chat-file-input')?.click()}
                className="absolute left-2 text-slate-400 hover:text-indigo-500 transition-colors p-1.5"
                title="Upload file"
              >
                <Paperclip size={20} />
              </button>

              <input
                id="chat-file-input"
                type="file"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFileDrop(e.target.files[0]);
                }}
              />

              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isStreaming && handleSend()}
                disabled={isStreaming}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-10 pr-24 py-3 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition disabled:opacity-50 disabled:cursor-not-allowed text-black dark:text-white"
                placeholder="Type your message..."
              />

              <div className="absolute right-2 flex items-center gap-1">
                <button
                  onClick={() => {
                    setIsRecording(!isRecording);
                  }}
                  className={`p-2 rounded-lg transition-colors ${isRecording ? 'text-red-500 hover:bg-red-50' : 'text-slate-400 hover:text-indigo-500'}`}
                  title="Voice Input"
                >
                  <Mic size={20} className={isRecording ? "animate-pulse" : ""} />
                </button>

                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isStreaming}
                  className="p-2 bg-teal-900 text-white rounded-lg hover:bg-teal-800 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-sm cursor-pointer"
                >
                  {isStreaming ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                </button>
              </div>
            </div>
            <p className="text-center text-xs text-slate-400 mt-2">
              Pikar AI can make mistakes. Consider checking important information.
            </p>
          </div>
        </div>
      </FileDropZone >

      {/* Overlay loading state */}
      {
        isUploading && (
          <div className="absolute inset-0 z-50 bg-white/50 dark:bg-slate-900/50 flex items-center justify-center backdrop-blur-sm rounded-xl">
            <div className="flex flex-col items-center">
              <Loader2 size={32} className="animate-spin text-indigo-600" />
              <span className="mt-2 text-sm font-medium text-slate-700 dark:text-slate-300">Analyzing file...</span>
            </div>
          </div>
        )
      }
    </div >
  )
}