import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { SocialCampaign, SocialAdVariant, SocialPost } from '@/api/entities'
import { supabase } from '@/lib/supabase'

export default function SupabaseDataMigrator() {
  const [busy, setBusy] = useState(false)
  const [summary, setSummary] = useState(null)

  const runMigration = async () => {
    setBusy(true)
    try {
      // Load from Base44 entities
      const campaigns = await SocialCampaign.list('-created_date')
      const variantsByCampaign = {}
      const postsByCampaign = {}

      for (const c of campaigns) {
        variantsByCampaign[c.id] = await SocialAdVariant.filter({ campaign_id: c.id })
        postsByCampaign[c.id] = await SocialPost.filter({ campaign_id: c.id })
      }

      // Insert into Supabase with minimal mapping
      let totalCampaigns = 0
      let totalVariants = 0
      let totalPosts = 0

      for (const c of campaigns) {
        const { data: insertedCampaign, error: campErr } = await supabase
          .from('social_campaigns')
          .insert({
            user_id: c.user_id || null,
            campaign_name: c.campaign_name,
            brand: c.brand,
            objective: c.objective,
            platforms: c.platforms,
            generated_plan: c.generated_plan || null,
            status: c.status || 'draft'
          })
          .select()
          .single()
        if (campErr) throw campErr
        totalCampaigns += 1

        const sourceVariants = variantsByCampaign[c.id] || []
        if (sourceVariants.length) {
          const rows = sourceVariants.map(v => ({
            campaign_id: insertedCampaign.id,
            platform: v.platform,
            variant_name: v.variant_name,
            headline: v.headline,
            body: v.body,
            cta: v.cta,
            creative_idea: v.creative_idea,
            hypothesis: v.hypothesis,
            status: v.status || 'draft',
            metrics: v.metrics || {}
          }))
          const { error: varErr, data: varData } = await supabase
            .from('social_ad_variants')
            .insert(rows)
            .select()
          if (varErr) throw varErr
          totalVariants += varData?.length || 0
        }

        const sourcePosts = postsByCampaign[c.id] || []
        if (sourcePosts.length) {
          const rows = sourcePosts.map(p => ({
            campaign_id: insertedCampaign.id,
            platform: p.platform,
            content: p.content,
            media_idea: p.media_idea,
            scheduled_time: p.scheduled_time ? new Date(p.scheduled_time).toISOString() : null,
            timezone: p.timezone || null,
            status: p.status || 'planned',
            metrics: p.metrics || {},
            published_at: p.published_at ? new Date(p.published_at).toISOString() : null,
            last_result: p.last_result || null,
            last_error: p.last_error || null
          }))
          const { error: postErr, data: postData } = await supabase
            .from('social_posts')
            .insert(rows)
            .select()
          if (postErr) throw postErr
          totalPosts += postData?.length || 0
        }
      }

      const msg = { campaigns: totalCampaigns, variants: totalVariants, posts: totalPosts }
      setSummary(msg)
      toast.success(`Migrated ${totalCampaigns} campaigns, ${totalVariants} variants, ${totalPosts} posts`)
    } catch (e) {
      console.error(e)
      toast.error('Migration failed: ' + (e?.message || e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Supabase Data Migration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-sm text-gray-600">
          Migrate Social campaigns, variants, and posts from Base44 entities to Supabase tables.
        </div>
        <Button disabled={busy} onClick={runMigration}>
          {busy ? 'Migrating…' : 'Run migration'}
        </Button>
        {summary && (
          <div className="text-sm text-gray-700">Done: {summary.campaigns} campaigns, {summary.variants} variants, {summary.posts} posts</div>
        )}
      </CardContent>
    </Card>
  )
}

