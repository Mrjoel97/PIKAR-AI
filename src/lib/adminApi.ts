import { supabase } from './supabase'

export const adminApi = {
  // Profiles
  async listProfiles({ search = '', limit = 50, offset = 0 }: { search?: string; limit?: number; offset?: number } = {}) {
    let query = supabase.from('profiles').select('*').order('created_at', { ascending: false }).range(offset, offset + limit - 1)
    if (search) {
      query = query.or(`email.ilike.%${search}%,username.ilike.%${search}%`)
    }
    const { data, error } = await query
    if (error) throw error
    return data
  },

  async getProfilesCount() {
    const { count, error } = await supabase.from('profiles').select('*', { count: 'exact', head: true })
    if (error) throw error
    return count || 0
  },

  async getProfile(id: string) {
    const { data, error } = await supabase.from('profiles').select('*').eq('id', id).single()
    if (error) throw error
    return data
  },

  async updateProfile(id: string, updates: any) {
    const { data, error } = await supabase.from('profiles').update(updates).eq('id', id).select().single()
    if (error) throw error
    return data
  },

  // Admin audit logs
  async listAuditLogs({ limit = 100, offset = 0 } = {}) {
    const { data, error } = await supabase
      .from('admin_audit_logs')
      .select('*')
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1)
    if (error) throw error
    return data
  },

  async addAuditLog({ actor_id, action, resource, details }: { actor_id: string; action: string; resource?: string; details?: any }) {
    const { data, error } = await supabase
      .from('admin_audit_logs')
      .insert({ actor_id, action, resource, details })
      .select()
      .single()
    if (error) throw error
    return data
  },

  // Feature flags
  async listFeatureFlags() {
    const { data, error } = await supabase.from('feature_flags').select('*').order('key')
    if (error) throw error
    return data
  },

  async upsertFeatureFlag(key: string, value: any, description?: string) {
    const { data, error } = await supabase
      .from('feature_flags')
      .upsert({ key, value, description })
      .select()
      .single()
    if (error) throw error
    return data
  },

  async deleteFeatureFlag(key: string) {
    const { error } = await supabase.from('feature_flags').delete().eq('key', key)
    if (error) throw error
    return true
  },

  // System config
  async getSystemConfig() {
    const { data, error } = await supabase.from('system_config').select('*').eq('id', 1).maybeSingle()
    if (error) throw error
    return data
  },

  async updateSystemConfig(config: any) {
    const { data, error } = await supabase
      .from('system_config')
      .upsert({ id: 1, config })
      .select()
      .single()
    if (error) throw error
    return data
  }
}

export default adminApi

