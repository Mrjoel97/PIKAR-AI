import { supabase } from '@/lib/supabase'

export type BillingProduct = {
  id: string
  stripe_product_id: string
  name: string
  description?: string
  metadata?: any
}

export type BillingPrice = {
  id: string
  stripe_price_id: string
  product_id: string
  currency: string
  unit_amount: number
  interval?: string
  interval_count?: number
  payment_link_url?: string
  active: boolean
}

export type UserSubscription = {
  id: string
  user_id: string
  stripe_customer_id?: string
  stripe_subscription_id?: string
  stripe_price_id?: string
  current_period_end?: string
  status?: string
  tier?: string
}

export const billing = {
  async listProducts(): Promise<BillingProduct[]> {
    const { data, error } = await supabase.from('billing_products').select('*').order('created_at', { ascending: true })
    if (error) throw error
    return data || []
  },
  async listPricesForProduct(product_id: string): Promise<BillingPrice[]> {
    const { data, error } = await supabase.from('billing_prices').select('*').eq('product_id', product_id).eq('active', true).order('unit_amount')
    if (error) throw error
    return data || []
  },
  async listActivePrices(): Promise<(BillingPrice & { product: BillingProduct })[]> {
    const { data, error } = await supabase
      .from('billing_prices')
      .select('*, product:billing_products(*)')
      .eq('active', true)
      .order('unit_amount')
    if (error) throw error
    return (data as any) || []
  },
  async getMySubscription(): Promise<UserSubscription | null> {
    const { data: sess } = await supabase.auth.getUser()
    const user_id = sess?.user?.id
    if (!user_id) return null
    const { data, error } = await supabase.from('user_subscriptions').select('*').eq('user_id', user_id).order('created_at', { ascending: false }).limit(1).maybeSingle()
    if (error) throw error
    return data
  },
  async upsertMySubscription(updates: Partial<UserSubscription>) {
    const { data: sess } = await supabase.auth.getUser()
    const user_id = sess?.user?.id
    if (!user_id) throw new Error('Not signed in')
    const { data, error } = await supabase.from('user_subscriptions').upsert({ user_id, ...updates }).select().single()
    if (error) throw error
    return data
  }
}

export default billing

