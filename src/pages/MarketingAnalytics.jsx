import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
// import { DateRangePicker } from '@/components/ui/date-range-picker'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { marketingAnalyticsService } from '@/services/marketingAnalyticsService'
import { Toaster, toast } from 'sonner'
import { supabase } from '@/lib/supabase'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'

export default function MarketingAnalytics() {
  const [since, setSince] = useState(() => new Date(Date.now() - 7*86400000).toISOString().slice(0,10))
  const [until, setUntil] = useState(() => new Date().toISOString().slice(0,10))
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [trends, setTrends] = useState([])

  const load = async () => {
    setLoading(true)
    try {
      const res = await marketingAnalyticsService.getPlatformMetrics({ since, until })
      setData(marketingAnalyticsService.normalize(res))
      // Load trends from Supabase snapshots
      const { data: snaps, error } = await supabase
        .from('analytics_snapshots')
        .select('*')
        .gte('captured_at', new Date(since).toISOString())
        .lte('captured_at', new Date(new Date(until).getTime() + 86400000).toISOString())
        .order('captured_at', { ascending: true })
      if (error) throw error
      const daily = new Map()
      for (const s of snaps || []) {
        const day = (s.captured_at || '').slice(0,10)
        const k = day
        const acc = daily.get(k) || { day: k, impressions: 0, clicks: 0, engagements: 0, videoViews: 0 }
        const kpis = s.kpis || {}
        acc.impressions += Number(kpis.impressions || 0)
        acc.clicks += Number(kpis.clicks || 0)
        acc.engagements += Number(kpis.engagements || 0)
        acc.videoViews += Number(kpis.videoViews || 0)
        daily.set(k, acc)
      }
      setTrends(Array.from(daily.values()))
    } catch (e) {
      console.error(e)
      toast.error('Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <Toaster richColors />
      <header className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">Marketing Analytics</div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-900 to-emerald-700 bg-clip-text text-transparent">Cross-platform performance overview</h1>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Select time range</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div>
            <div className="text-sm text-gray-600">Since</div>
            <input type="date" value={since} onChange={e => setSince(e.target.value)} className="border rounded px-3 py-1" />
          </div>
          <div>
            <div className="text-sm text-gray-600">Until</div>
            <input type="date" value={until} onChange={e => setUntil(e.target.value)} className="border rounded px-3 py-1" />
          </div>
          <button onClick={load} className="px-3 py-1.5 rounded-md bg-emerald-600 text-white text-sm hover:bg-emerald-700" disabled={loading}>{loading ? 'Loading...' : 'Apply'}</button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Unified KPIs</CardTitle>
          <CardDescription>Aggregated across all connected platforms</CardDescription>
        </CardHeader>
        <CardContent>
          {!data ? (
            <div className="text-gray-600">No data yet.</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Kpi label="Impressions" value={data.unified.impressions} />
              <Kpi label="Engagements" value={data.unified.engagements} />
              <Kpi label="Clicks" value={data.unified.clicks} />
              <Kpi label="CTR" value={(data.unified.ctr*100).toFixed(2)+'%'} />
              <Kpi label="Video Views" value={data.unified.videoViews} />
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Trends</CardTitle>
          <CardDescription>Aggregated KPI trends from snapshots</CardDescription>
        </CardHeader>
        <CardContent>
          {!trends.length ? (
            <div className="text-gray-600">No snapshots yet.</div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="impressions" stroke="#10b981" />
                  <Line type="monotone" dataKey="clicks" stroke="#6366f1" />
                  <Line type="monotone" dataKey="engagements" stroke="#f59e0b" />
                  <Line type="monotone" dataKey="videoViews" stroke="#ef4444" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>By Platform</CardTitle>
        </CardHeader>
        <CardContent>
          {!data ? (
            <div className="text-gray-600">No data yet.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(data.byPlatform).map(([platform, rpt]) => (
                <div key={platform} className="border rounded-lg p-4">
                  <div className="text-sm font-medium mb-2">{platform}</div>
                  {rpt.ok ? (
                    <pre className="text-xs overflow-auto">{JSON.stringify(rpt.metrics, null, 2)}</pre>
                  ) : (
                    <div className="text-xs text-red-600">{rpt.error}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function Kpi({ label, value }) {
  return (
    <div>
      <div className="text-sm text-gray-600">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  )
}

