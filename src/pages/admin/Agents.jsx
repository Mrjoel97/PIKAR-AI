import React, { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function Agents() {
  const [configs, setConfigs] = useState([])
  const [runs, setRuns] = useState([])
  const [form, setForm] = useState({ key: '', model: 'gpt-4o-mini', temperature: 0.3, system_prompt: '' })
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    const { data: cfgs } = await supabase.from('agent_configs').select('*').order('created_at')
    const { data: rn } = await supabase.from('agent_runs').select('*').order('created_at', { ascending: false }).limit(50)
    setConfigs(cfgs || [])
    setRuns(rn || [])
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const saveConfig = async () => {
    await supabase.from('agent_configs').upsert(form)
    setForm({ key: '', model: 'gpt-4o-mini', temperature: 0.3, system_prompt: '' })
    load()
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Agent Configurations</h2>
        <div className="flex gap-2 mb-2">
          <input value={form.key} onChange={e=>setForm({ ...form, key: e.target.value })} placeholder="key" className="border rounded px-2 py-1" />
          <input value={form.model} onChange={e=>setForm({ ...form, model: e.target.value })} placeholder="model" className="border rounded px-2 py-1" />
          <input type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={e=>setForm({ ...form, temperature: parseFloat(e.target.value) })} placeholder="temp" className="border rounded px-2 py-1 w-24" />
          <input value={form.system_prompt} onChange={e=>setForm({ ...form, system_prompt: e.target.value })} placeholder="system prompt" className="border rounded px-2 py-1 w-96" />
          <button onClick={saveConfig} className="px-3 py-1.5 rounded bg-emerald-600 text-white">Save</button>
        </div>
        <table className="min-w-full text-sm">
          <thead><tr className="bg-gray-50 text-left"><th className="p-2">Key</th><th className="p-2">Model</th><th className="p-2">Temp</th><th className="p-2">Enabled</th></tr></thead>
          <tbody>
            {configs.map(c => (<tr key={c.id} className="border-t"><td className="p-2">{c.key}</td><td className="p-2">{c.model}</td><td className="p-2">{c.temperature}</td><td className="p-2">{String(c.enabled)}</td></tr>))}
          </tbody>
        </table>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-2">Recent Runs</h2>
        <table className="min-w-full text-sm">
          <thead><tr className="bg-gray-50 text-left"><th className="p-2">Agent</th><th className="p-2">Actor</th><th className="p-2">Input</th><th className="p-2">Output</th><th className="p-2">Time</th></tr></thead>
          <tbody>
            {runs.map(r => (<tr key={r.id} className="border-t"><td className="p-2">{r.agent_key}</td><td className="p-2"><code>{r.actor_id || '—'}</code></td><td className="p-2 truncate max-w-xs">{r.input_summary}</td><td className="p-2 truncate max-w-xs">{r.output_summary}</td><td className="p-2">{new Date(r.created_at).toLocaleString()}</td></tr>))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

