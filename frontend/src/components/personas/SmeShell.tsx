import React from 'react'

export function SmeShell({ children }: { children?: React.ReactNode }) {
  return (
    <div className="sme-theme min-h-screen bg-emerald-50">
      <header className="bg-emerald-700 text-white p-4" role="banner">SME Operations</header>
      <main className="p-4">{children}</main>
    </div>
  )
}
