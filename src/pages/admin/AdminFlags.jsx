import React, { useEffect, useState } from 'react'
import { adminApi } from '@/lib/adminApi'

export default function AdminFlags() {
  const [flags, setFlags] = useState([])
  const [key, setKey] = useState('')
  const [value, setValue] = useState('{}')
  const [desc, setDesc] = useState('')

  const load = async () => {
    const list = await adminApi.listFeatureFlags()
    setFlags(list)
  }

  useEffect(() => { load() }, [])

  const upsert = async () => {
    try {
      const parsed = JSON.parse(value)
      await adminApi.upsertFeatureFlag(key, parsed, desc)
      const { adminAuditService } = await import('@/services/adminAuditService')
      await adminAuditService.log({ action: 'upsert_flag', resource: `feature_flags:${key}`, details: { value: parsed, description: desc } })
      setKey(''); setValue('{}'); setDesc('');
      load()
    } catch (e) {
      alert('Invalid JSON')
    }
  }

  const remove = async (k) => {
    await adminApi.deleteFeatureFlag(k)
    const { adminAuditService } = await import('@/services/adminAuditService')
    await adminAuditService.log({ action: 'delete_flag', resource: `feature_flags:${k}` })
    load()
  }

  return (
    <div className="space-y-4">
      <div className="p-4 bg-white rounded-md border">
        <div className="font-semibold mb-2">Create/Update Flag</div>
        <div className="grid md:grid-cols-3 gap-2">
          <input value={key} onChange={e=>setKey(e.target.value)} placeholder="key" className="border rounded px-3 py-2" />
          <input value={desc} onChange={e=>setDesc(e.target.value)} placeholder="description" className="border rounded px-3 py-2" />
          <input value={value} onChange={e=>setValue(e.target.value)} placeholder='{"enabled":true}' className="border rounded px-3 py-2" />
        </div>
        <div className="mt-2">
          <button onClick={upsert} className="px-3 py-2 rounded bg-emerald-600 text-white">Save</button>
        </div>
      </div>

      <div className="p-4 bg-white rounded-md border">
        <div className="font-semibold mb-2">Flags</div>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left">
              <th className="p-2">Key</th>
              <th className="p-2">Description</th>
              <th className="p-2">Value</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {flags.map(f => (
              <tr key={f.key} className="border-t">
                <td className="p-2">{f.key}</td>
                <td className="p-2">{f.description}</td>
                <td className="p-2"><pre className="text-xs whitespace-pre-wrap">{JSON.stringify(f.value)}</pre></td>
                <td className="p-2"><button className="px-2 py-1 rounded border" onClick={()=>remove(f.key)}>Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

