import React from 'react'

export function StartupShell({ children }: { children?: React.ReactNode }) {
  return (
    <div className="startup-theme min-h-screen bg-indigo-50">
      <header className="bg-indigo-600 text-white p-4" role="banner">Startup Hub</header>
      <main className="p-4">{children}</main>
    </div>
  )
}
