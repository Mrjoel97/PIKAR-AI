'use client'
import React, { useState } from 'react'
import { Send } from 'lucide-react'

export function ChatInterface() {
  const [messages, setMessages] = useState<{role: 'user' | 'agent', text: string}[]>([
    { role: 'agent', text: 'Hello! How can I help you today?' }
  ])
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim()) return
    setMessages([...messages, { role: 'user', text: input }])
    setInput('')
    // Simulate agent response
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'agent', text: 'I am a placeholder agent.' }])
    }, 100)
  }

  return (
    <div className="flex flex-col h-[500px] bg-white rounded-lg shadow-sm border">
      <div className="flex-1 overflow-auto p-4 space-y-4" role="log">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-3 rounded-lg ${msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
              {msg.text}
            </div>
          </div>
        ))}
      </div>
      <div className="p-4 border-t flex gap-2">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          className="flex-1 border rounded-lg px-4 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
          placeholder="Type a message..."
          aria-label="Message input"
        />
        <button 
          onClick={handleSend}
          className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700"
          aria-label="Send message"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  )
}
