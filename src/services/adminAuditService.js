import { supabase } from '@/lib/supabase'

export const adminAuditService = {
  async log({ action, resource, details }) {
    const { data: session } = await supabase.auth.getSession()
    const actor_id = session?.session?.user?.id || null
    await supabase.from('admin_audit_logs').insert({ actor_id, action, resource, details })
  }
}

export default adminAuditService

