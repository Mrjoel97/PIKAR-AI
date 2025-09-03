import { supabase } from './supabase'

export type ProjectData = {
  user_id: string
  name: string
  description?: string
  settings?: any
}

export const api = {
  async createProject(data: ProjectData) {
    const { data: result, error } = await supabase
      .from('projects')
      .insert(data)
      .select()
      .single()
    if (error) throw error
    return result
  },

  async getProjects(userId: string) {
    const { data, error } = await supabase
      .from('projects')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
    if (error) throw error
    return data
  },

  async createSocialCampaign(payload: any) {
    const { data, error } = await supabase
      .from('social_campaigns')
      .insert(payload)
      .select()
      .single()
    if (error) throw error
    return data
  },

  async createAdVariants(variants: any[]) {
    const { data, error } = await supabase
      .from('social_ad_variants')
      .insert(variants)
      .select()
    if (error) throw error
    return data
  },

  async createSocialPosts(posts: any[]) {
    const { data, error } = await supabase
      .from('social_posts')
      .insert(posts)
      .select()
    if (error) throw error
    return data
  },

  async getSocialCampaigns(userId: string) {
    const { data, error } = await supabase
      .from('social_campaigns')
      .select('*')
      .eq('user_id', userId)
      .order('updated_at', { ascending: false })
    if (error) throw error
    return data
  },

  async getVariantsByCampaign(campaignId: string) {
    const { data, error } = await supabase
      .from('social_ad_variants')
      .select('*')
      .eq('campaign_id', campaignId)
    if (error) throw error
    return data
  },

  async getPostsByCampaign(campaignId: string) {
    const { data, error } = await supabase
      .from('social_posts')
      .select('*')
      .eq('campaign_id', campaignId)
    if (error) throw error
    return data
  },

  async getCampaignById(id: string) {
    const { data, error } = await supabase
      .from('social_campaigns')
      .select('*')
      .eq('id', id)
      .single()
    if (error) throw error
    return data
  },

  async updateAdVariant(id: string, payload: any) {
    const { data, error } = await supabase
      .from('social_ad_variants')
      .update(payload)
      .eq('id', id)
      .select()
      .single()
    if (error) throw error
    return data
  }
}

export default api

