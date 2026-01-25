import React from 'react'

export function SolopreneurShell({ children }: { children?: React.ReactNode }) {
  return (
    <div className="solopreneur-theme min-h-screen bg-blue-50">
      <header className="bg-blue-600 text-white p-4" role="banner">Solopreneur Workspace</header>
      <main className="p-4">{children}</main>
    </div>
  )
}
