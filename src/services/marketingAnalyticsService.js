// Marketing Analytics Service - aggregates cross-platform metrics
import { auditService } from '@/services/auditService'
import * as f from '@/api/functions'

export const marketingAnalyticsService = {
  async getPlatformMetrics({ since, until, campaignId, metaObjectId, youtubeChannelId, linkedinAccountId } = {}) {
    const range = { since, until }
    const res = {}

    try {
      if (metaObjectId) {
        const { data, status } = await f.metaGetInsights({
          object_id: metaObjectId,
          metric: ['impressions', 'reach', 'engagement', 'clicks'],
          time_range: range
        })
        res.meta = status === 200 ? { ok: true, metrics: data } : { ok: false, error: data?.error || 'Failed' }
      } else {
        res.meta = { ok: true, metrics: {} }
      }
    } catch (e) {
      auditService.logSystem.error(e, 'analytics_meta_failed')
      res.meta = { ok: false, error: String(e?.message || e) }
    }

    try {
      // Fetch Twitter ad accounts as a connectivity check (extend with analytics endpoints once available)
      const { data, status } = await f.twitterGetAdAccounts()
      res.twitter = status === 200 ? { ok: true, metrics: { ad_accounts: data } } : { ok: false, error: data?.error || 'Failed' }
    } catch (e) {
      auditService.logSystem.error(e, 'analytics_twitter_failed')
      res.twitter = { ok: false, error: String(e?.message || e) }
    }

    try {
      const { data, status } = await f.linkedinGetLeads({ date_range: range })
      res.linkedin = status === 200 ? { ok: true, metrics: data } : { ok: false, error: data?.error || 'Failed' }
    } catch (e) {
      auditService.logSystem.error(e, 'analytics_linkedin_failed')
      res.linkedin = { ok: false, error: String(e?.message || e) }
    }

    try {
      if (youtubeChannelId) {
        const { data, status } = await f.youtubeGetAnalytics({ time_range: range, metrics: ['views', 'estimatedMinutesWatched'] })
        res.youtube = status === 200 ? { ok: true, metrics: data } : { ok: false, error: data?.error || 'Failed' }
      } else {
        res.youtube = { ok: true, metrics: {} }
      }
    } catch (e) {
      auditService.logSystem.error(e, 'analytics_youtube_failed')
      res.youtube = { ok: false, error: String(e?.message || e) }
    }

    try {
      const { data, status } = await f.tiktokGetVideos({ page: 1, page_size: 20 })
      res.tiktok = status === 200 ? { ok: true, metrics: { videos: data } } : { ok: false, error: data?.error || 'Failed' }
    } catch (e) {
      auditService.logSystem.error(e, 'analytics_tiktok_failed')
      res.tiktok = { ok: false, error: String(e?.message || e) }
    }

    return res
  },

  async snapshotAndNormalize({ campaignId, capturedAt = new Date().toISOString(), ...params }) {
    const metrics = await this.getPlatformMetrics(params)
    const { unified } = this.normalize(metrics)
    try {
      const { supabase } = await import('@/lib/supabase')
      const kpis = { ...unified }
      const platformKeys = Object.keys(metrics).filter(k => metrics[k]?.ok)
      for (const p of platformKeys) {
        await supabase.from('analytics_snapshots').insert({ campaign_id: campaignId, platform: p, kpis, captured_at: capturedAt })
      }
    } catch (e) {
      console.error('Snapshot save failed', e)
    }
    return { metrics, unified }
  },

  normalize(metricsByPlatform) {
    // Normalize to a common schema
    const unified = {
      impressions: 0,
      engagements: 0,
      clicks: 0,
      ctr: 0,
      videoViews: 0,
    }

    // Meta example
    const meta = metricsByPlatform.meta
    if (meta?.ok && meta.metrics) {
      const m = meta.metrics
      unified.impressions += Number(m.impressions || 0)
      unified.engagements += Number(m.engagement || 0)
      unified.clicks += Number(m.clicks || 0)
      if (unified.impressions > 0) unified.ctr = unified.clicks / unified.impressions
    }

    // YouTube example
    const yt = metricsByPlatform.youtube
    if (yt?.ok && yt.metrics) {
      unified.videoViews += Number(yt.metrics.views || 0)
    }

    return { unified, byPlatform: metricsByPlatform }
  }
}

export default marketingAnalyticsService

