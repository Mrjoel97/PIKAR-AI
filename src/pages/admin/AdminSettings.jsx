import React, { useEffect, useState } from 'react'
import { adminApi } from '@/lib/adminApi'

export default function AdminSettings() {
  const [cfg, setCfg] = useState({})

  useEffect(() => { adminApi.getSystemConfig().then(d=>setCfg(d?.config||{})).catch(console.error) }, [])

  const save = async () => {
    await adminApi.updateSystemConfig(cfg)
    alert('Saved')
  }

  return (
    <div className="space-y-3 p-4 bg-white rounded-md border">
      <div className="font-semibold">System Configuration</div>
      <textarea value={JSON.stringify(cfg, null, 2)} onChange={e=>{
        try { setCfg(JSON.parse(e.target.value)) } catch {}
      }} className="w-full h-64 border rounded p-2 font-mono text-xs"/>
      <button onClick={save} className="px-3 py-2 rounded bg-emerald-600 text-white">Save</button>
    </div>
  )
}

