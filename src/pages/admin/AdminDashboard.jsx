import React, { useEffect, useState } from 'react'
import { adminApi } from '@/lib/adminApi'

export default function AdminDashboard() {
  const [profilesCount, setProfilesCount] = useState(0)
  const [logs, setLogs] = useState([])
  const [flags, setFlags] = useState([])

  useEffect(() => {
    adminApi.getProfilesCount().then(setProfilesCount).catch(console.error)
    adminApi.listAuditLogs({ limit: 5 }).then(setLogs).catch(console.error)
    adminApi.listFeatureFlags().then(setFlags).catch(console.error)
  }, [])

  return (
    <div className="space-y-4">
      <div className="grid md:grid-cols-3 gap-4">
        <div className="p-4 bg-white rounded-md border">
          <div className="text-sm text-gray-600">Total Users</div>
          <div className="text-3xl font-bold">{profilesCount}</div>
        </div>
        <div className="p-4 bg-white rounded-md border">
          <div className="text-sm text-gray-600">Feature Flags</div>
          <div className="text-3xl font-bold">{flags.length}</div>
        </div>
        <div className="p-4 bg-white rounded-md border">
          <div className="text-sm text-gray-600">Recent Audit</div>
          <div className="text-3xl font-bold">{logs.length}</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="p-4 bg-white rounded-md border">
          <div className="font-semibold mb-2">Recent Audit Logs</div>
          <ul className="text-sm text-gray-700 space-y-1">
            {logs.map(l => (
              <li key={l.id} className="flex justify-between">
                <span>{l.action}</span>
                <span className="text-gray-500">{new Date(l.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="p-4 bg-white rounded-md border">
          <div className="font-semibold mb-2">Feature Flags</div>
          <ul className="text-sm text-gray-700 space-y-1">
            {flags.map(f => (
              <li key={f.key} className="flex justify-between">
                <span>{f.key}</span>
                <span className="text-gray-500">{f.updated_at && new Date(f.updated_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

