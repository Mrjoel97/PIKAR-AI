import React from 'react'
import { NavLink, Outlet } from 'react-router-dom'

export default function AdminLayout() {
  const link = (to, label) => (
    <NavLink to={to} className={({isActive}) => `px-3 py-2 rounded-md ${isActive ? 'bg-emerald-600 text-white' : 'text-gray-700 hover:bg-gray-100'}`}>{label}</NavLink>
  )
  return (
    <div className="min-h-screen grid grid-rows-[auto,1fr]">
      <header className="border-b bg-white">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <div className="font-bold">PIKAR AI Admin</div>
          <nav className="flex items-center gap-2 text-sm">
            {link('/admin','Dashboard')}
            {link('/admin/users','Users')}
            {link('/admin/agents','Agents')}
            {link('/admin/audit','Audit Logs')}
            {link('/admin/flags','Feature Flags')}
            {link('/admin/billing','Billing')}
            {link('/admin/settings','Settings')}
          </nav>
        </div>
      </header>
      <main className="bg-gray-50">
        <div className="max-w-7xl mx-auto p-4">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

