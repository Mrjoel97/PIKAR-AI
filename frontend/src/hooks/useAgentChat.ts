import { useState, useCallback, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

export type Message = {
  role: 'user' | 'agent' | 'system';
  text: string;
  agentName?: string;
  isThinking?: boolean;
};

export function useAgentChat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'agent', text: 'Hello! I am Pikar AI. How can I help you optimize your business today?', agentName: 'ExecutiveAgent' }
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const supabase = createClientComponentClient();
  
  // Persist session ID across renders
  const sessionIdRef = useRef<string>(`session-${Date.now()}`);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    const userMsg: Message = { role: 'user', text: content };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      let currentAgentMessage = '';
      let currentAgentName = 'ExecutiveAgent';

      // Add placeholder for streaming response
      setMessages((prev) => [
        ...prev, 
        { role: 'agent', text: '', agentName: currentAgentName, isThinking: true }
      ]);

      await fetchEventSource(`${API_URL}/a2a/pikar_ai/run_sse`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
           session_id: sessionIdRef.current,
           new_message: { parts: [{ text: content }] },
        }),
        async onopen(response) {
            if (response.ok) {
                return;
            } else {
                throw new Error(`Failed to connect: ${response.statusText}`);
            }
        },
        onmessage(msg) {
          if (msg.event === 'ping') return;

          try {
             // A2A SSE payload structure check
             const data = JSON.parse(msg.data);
             
             // Handle agent updates (orchestration)
             if (data.author && data.author !== 'user' && data.author !== 'system') {
                 if (data.author !== currentAgentName) {
                     currentAgentName = data.author;
                 }
             }

             // Handle content
             let newText = '';
             if (data.content && data.content.parts) {
                 newText = data.content.parts.map((p: any) => p.text).join('');
             } else if (data.content && typeof data.content === 'string') {
                 // Sometimes it might send raw string, though A2A usually sends Content object
                 newText = data.content;
             }

             if (newText) {
                 currentAgentMessage += newText;
                 
                 setMessages((prev) => {
                    const newMsgs = [...prev];
                    const lastMsg = newMsgs[newMsgs.length - 1];
                    if (lastMsg.role === 'agent') {
                        lastMsg.text = currentAgentMessage;
                        lastMsg.agentName = currentAgentName;
                        lastMsg.isThinking = false;
                    }
                    return newMsgs;
                 });
             }
          } catch (e) {
             // console.error('Error parsing chunk', e);
          }
        },
        onclose() {
          setIsStreaming(false);
        },
        onerror(err) {
           console.error('SSE Error', err);
           setIsStreaming(false);
           throw err; // rethrow to stop
        }
      });

    } catch (err) {
      console.error('Chat failed', err);
      setMessages((prev) => {
          // Remove the "thinking" placeholder if empty, or append error
          const newMsgs = [...prev];
          const lastMsg = newMsgs[newMsgs.length - 1];
          if (lastMsg.isThinking && !lastMsg.text) {
              return [...newMsgs.slice(0, -1), { role: 'system', text: 'Error: Failed to connect to Pikar AI.' }];
          }
          return [...prev, { role: 'system', text: 'Error: Connection interrupted.' }];
      });
      setIsStreaming(false);
    }
  }, [supabase]);

  return { messages, sendMessage, isStreaming };
}
