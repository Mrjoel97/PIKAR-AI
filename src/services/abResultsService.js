import { supabase } from '@/lib/supabase'

export const abResultsService = {
  async recordExposure(test_id, variant_name, inc = 1) {
    await this._upsert(test_id, variant_name, { exposures: inc }, 'increment')
  },
  async recordClick(test_id, variant_name, inc = 1) {
    await this._upsert(test_id, variant_name, { clicks: inc }, 'increment')
  },
  async recordConversion(test_id, variant_name, inc = 1) {
    await this._upsert(test_id, variant_name, { conversions: inc }, 'increment')
  },
  async getResults(test_id) {
    const { data, error } = await supabase.from('ab_variant_results').select('*').eq('test_id', test_id)
    if (error) throw error
    return data
  },
  async _upsert(test_id, variant_name, deltas, mode = 'set') {
    const { data, error } = await supabase
      .from('ab_variant_results')
      .select('*')
      .eq('test_id', test_id)
      .eq('variant_name', variant_name)
      .maybeSingle()
    if (error) throw error
    if (!data) {
      const row = { test_id, variant_name, exposures: 0, clicks: 0, conversions: 0, metrics: {} }
      Object.keys(deltas).forEach(k => { row[k] += deltas[k] })
      const { error: insErr } = await supabase.from('ab_variant_results').insert(row)
      if (insErr) throw insErr
    } else {
      const updates = {}
      Object.keys(deltas).forEach(k => { updates[k] = (data[k] || 0) + deltas[k] })
      updates.ctr = updates.exposures ? updates.clicks / updates.exposures : 0
      updates.cvr = updates.clicks ? updates.conversions / updates.clicks : 0
      const { error: updErr } = await supabase
        .from('ab_variant_results')
        .update(updates)
        .eq('id', data.id)
      if (updErr) throw updErr
    }
  }
}

export default abResultsService

