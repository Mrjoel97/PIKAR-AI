import React, { useEffect, useState } from 'react'
import { adminApi } from '@/lib/adminApi'

export default function AdminAudit() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    adminApi.listAuditLogs({ limit: 100 }).then(setLogs).finally(()=>setLoading(false))
  }, [])

  return (
    <div className="p-2 bg-white rounded-md border">
      <div className="font-semibold mb-2">Audit Logs</div>
      {loading ? 'Loading...' : (
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left">
              <th className="p-2">Time</th>
              <th className="p-2">Action</th>
              <th className="p-2">Resource</th>
              <th className="p-2">Actor</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(l => (
              <tr key={l.id} className="border-t">
                <td className="p-2">{new Date(l.created_at).toLocaleString()}</td>
                <td className="p-2">{l.action}</td>
                <td className="p-2">{l.resource}</td>
                <td className="p-2">{l.actor_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

