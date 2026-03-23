'use client'

import { toast } from 'sonner'

let activeToastCount = 0

export function showSessionReadyToast(
  sessionId: string,
  sessionTitle: string,
  onNavigate: (sessionId: string) => void,
) {
  if (document.visibilityState === 'hidden') return

  activeToastCount++

  if (activeToastCount > 2) {
    toast.dismiss()
    toast(`${activeToastCount} sessions ready`, {
      duration: 5000,
      onDismiss: () => { activeToastCount = 0 },
    })
    return
  }

  toast(`${sessionTitle} — Response ready`, {
    duration: 5000,
    action: {
      label: 'View',
      onClick: () => onNavigate(sessionId),
    },
    onDismiss: () => {
      activeToastCount = Math.max(0, activeToastCount - 1)
    },
  })
}
