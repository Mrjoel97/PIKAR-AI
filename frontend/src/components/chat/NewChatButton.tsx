'use client'

import { useEffect } from 'react'
import { useSessionControl } from '@/contexts/SessionControlContext'
import { Plus } from 'lucide-react'

export function NewChatButton() {
  const { createNewChat } = useSessionControl()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.altKey && e.key.toLowerCase() === 'n') {
        e.preventDefault()
        createNewChat()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [createNewChat])

  return (
    <button
      onClick={() => createNewChat()}
      className="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium text-zinc-100 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
      title="New Chat (Alt+N)"
    >
      <Plus className="h-4 w-4" />
      New Chat
    </button>
  )
}
