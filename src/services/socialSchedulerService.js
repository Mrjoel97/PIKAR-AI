// Social Scheduler Service
// Schedules and publishes social posts across platforms using existing function wrappers

// import { SocialPost } from '@/api/entities'
import { auditService } from '@/services/auditService'
import { toast } from 'sonner'
import { supabase } from '@/lib/supabase'

// Lazy import of platform functions from src/api/functions barrel
async function getFunction(name) {
  const fns = await import('@/api/functions')
  return fns[name]
}

function selectPlatformPublisher(platform) {
  switch ((platform || '').toLowerCase()) {
    case 'facebook':
    case 'meta':
      return async ({ page_id, message }) => {
        const metaPostPage = await getFunction('metaPostPage')
        return metaPostPage({ page_id, message })
      }
    case 'instagram':
      return async ({ caption, media_url }) => {
        const metaPublishInstagram = await getFunction('metaPublishInstagram')
        return metaPublishInstagram({ caption, media_url })
      }
    case 'twitter':
    case 'x':
    case 'x/twitter':
      return async ({ text }) => {
        const twitterPostTweet = await getFunction('twitterPostTweet')
        return twitterPostTweet({ text })
      }
    case 'linkedin':
      return async ({ text, visibility = 'PUBLIC', media_url }) => {
        const linkedinPostShare = await getFunction('linkedinPostShare')
        return linkedinPostShare({ text, visibility, media_url })
      }
    case 'youtube':
      return async ({ title, description, video_url }) => {
        const youtubeUploadVideo = await getFunction('youtubeUploadVideo')
        return youtubeUploadVideo({ title, description, video_url })
      }
    case 'tiktok':
      return async ({ title, description, video_url }) => {
        const tiktokUploadVideo = await getFunction('tiktokUploadVideo')
        return tiktokUploadVideo({ title, description, video_file_url: video_url })
      }
    default:
      return null
  }
}

function extractPublishPayload(post) {
  // Normalize the SocialPost content to platform-specific payload
  const platform = (post.platform || '').toLowerCase()
  const content = post.content || post.content_markdown || post.content_text || post.content_html || ''
  const mediaUrl = post.video_url || post.image_url || (post.content?.video) || (post.content?.images?.[0])
  const title = post.title || (post.campaign_name ? `${post.campaign_name} Update` : 'New Post')

  if (platform === 'facebook' || platform === 'meta') {
    return { message: typeof content === 'string' ? content : content?.text, page_id: post.page_id }
  }
  if (platform === 'instagram') {
    return { caption: typeof content === 'string' ? content : content?.text, media_url: mediaUrl }
  }
  if (platform === 'twitter' || platform === 'x' || platform === 'x/twitter') {
    return { text: typeof content === 'string' ? content : content?.text }
  }
  if (platform === 'linkedin') {
    return { text: typeof content === 'string' ? content : content?.text, media_url: mediaUrl }
  }
  if (platform === 'youtube') {
    return { title, description: typeof content === 'string' ? content : content?.text, video_url: mediaUrl }
  }
  if (platform === 'tiktok') {
    return { title, description: typeof content === 'string' ? content : content?.text, video_url: mediaUrl }
  }
  return {}
}

export const socialSchedulerService = {
  // Publish a single SocialPost entity by id
  async publishPostById(postId) {
    const [post] = await SocialPost.filter({ id: postId })
    if (!post) throw new Error('Post not found')
    return this.publishPost(post)
  },

  // Publish a SocialPost record
  async publishPost(post) {
    const platform = (post.platform || '').toLowerCase()
    const publisher = selectPlatformPublisher(platform)
    if (!publisher) throw new Error(`Unsupported platform: ${post.platform}`)

    const payload = extractPublishPayload(post)

    try {
      const { data, status } = await publisher(payload)
      if (status === 200 && (data?.ok || data?.success)) {
        // Increment simple exposure metric
        const nextMetrics = { ...(post.metrics || {}), impressions: (post.metrics?.impressions || 0) + 1 }
        await SocialPost.update(post.id, {
          status: 'published',
          published_at: new Date().toISOString(),
          last_result: data,
          metrics: nextMetrics
        })
        await auditService.logAccess.marketing('social_post_published', {
          postId: post.id,
          platform: post.platform
        })
        return { ok: true, data }
      } else {
        await SocialPost.update(post.id, {
          status: 'failed',
          last_error: data?.error || data?.message || 'Publish failed'
        })
        return { ok: false, error: data?.error || 'Publish failed' }
      }
    } catch (error) {
      await SocialPost.update(post.id, { status: 'failed', last_error: String(error?.message || error) })
      await auditService.logSystem.error(error, 'social_post_publish_failed', { postId: post.id, platform })
      throw error
    }
  },

  // Publish all due posts up to now (optionally filtered by campaign)
  async runDuePosts({ campaignId = null } = {}) {
    const nowIso = new Date().toISOString()
    if (campaignId) {
      // Client-side filter then publish
      const { data: posts, error } = await supabase
        .from('social_posts')
        .select('*')
        .eq('campaign_id', campaignId)
      if (error) throw error
      const due = (posts || []).filter(p => (p.status === 'planned' || p.status === 'scheduled') && p.scheduled_time && p.scheduled_time <= nowIso)
      const results = []
      for (const post of due) {
        try {
          const res = await this.publishPost(post)
          results.push({ id: post.id, ok: true, res })
        } catch (e) {
          results.push({ id: post.id, ok: false, error: String(e?.message || e) })
        }
      }
      return results
    }
    // Use server-side function to publish all due posts
    const { data, error } = await supabase.rpc('publish_due_posts', { now_ts: nowIso })
    if (error) throw error
    return data || []
  }
}

export default socialSchedulerService

