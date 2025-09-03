import React, { useEffect, useState } from 'react'
import { adminApi } from '@/lib/adminApi'
import { supabase } from '@/lib/supabase'

export default function AdminUsers() {
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const list = await adminApi.listProfiles({ search, limit: 50 })
      setUsers(list)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const updateTier = async (id, tier) => {
    await adminApi.updateProfile(id, { tier })
    load()
  }

  const updateRole = async (id, role) => {
    await adminApi.updateProfile(id, { admin_role: role })
    const { data: me } = await supabase.auth.getUser()
    // log audit action
    const { adminAuditService } = await import('@/services/adminAuditService')
    await adminAuditService.log({ action: 'set_admin_role', resource: `profile:${id}`, details: { by: me?.user?.id, role } })
    load()
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search email or username" className="border rounded px-3 py-2 w-full" />
        <button onClick={load} className="px-3 py-2 rounded bg-emerald-600 text-white">Search</button>
      </div>
      <div className="overflow-auto border rounded">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left">
              <th className="p-2">Email</th>
              <th className="p-2">Username</th>
              <th className="p-2">Tier</th>
              <th className="p-2">Admin Role</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-t">
                <td className="p-2">{u.email}</td>
                <td className="p-2">{u.username}</td>
                <td className="p-2">
                  <select value={u.tier || 'solopreneur'} onChange={e=>updateTier(u.id, e.target.value)} className="border rounded px-2 py-1">
                    {['solopreneur','startup','sme','enterprise'].map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </td>
                <td className="p-2">
                  <select value={u.admin_role || ''} onChange={e=>updateRole(u.id, e.target.value)} className="border rounded px-2 py-1">
                    <option value="">None</option>
                    {['SUPER_ADMIN','ADMIN','SUPPORT','ANALYST','MODERATOR'].map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td className="p-2">
                  <button className="px-2 py-1 rounded border">Impersonate</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

