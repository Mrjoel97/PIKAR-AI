import React from 'react'

export function EnterpriseShell({ children }: { children?: React.ReactNode }) {
  return (
    <div className="enterprise-theme min-h-screen bg-slate-50">
      <header className="bg-slate-900 text-white p-4" role="banner">Enterprise Command Center</header>
      <main className="p-4">{children}</main>
    </div>
  )
}
