// Supabase Edge Function: Stripe Sync (Test Mode)
// Deploy: supabase functions deploy stripe-sync
// Secrets required: STRIPE_SECRET_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// This function syncs Stripe products, prices, and creates Payment Links for recurring prices.

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import Stripe from 'https://esm.sh/stripe@14.11.0?target=deno'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.45.4'

const STRIPE_SECRET = Deno.env.get('STRIPE_SECRET_KEY') || ''
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

const stripe = new Stripe(STRIPE_SECRET, { apiVersion: '2024-06-20' })
const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

const TIERS = [
  { key: 'solopreneur', name: 'Solopreneur', amounts: { monthly: 9900, yearly: 99000 } },
  { key: 'startup', name: 'Startup', amounts: { monthly: 29700, yearly: 297000 } },
  { key: 'sme', name: 'SME', amounts: { monthly: 59700, yearly: 597000 } }
]

async function ensureProduct(name: string, description: string) {
  const list = await stripe.products.list({ active: true, limit: 100 })
  let prod = list.data.find(p => p.name === name)
  if (!prod) prod = await stripe.products.create({ name, description })
  return prod
}

async function ensurePrice(product: string, unit_amount: number, interval: 'month' | 'year') {
  const prices = await stripe.prices.list({ active: true, product, limit: 100 })
  let price = prices.data.find(p => p.unit_amount === unit_amount && p.recurring?.interval === interval)
  if (!price) {
    price = await stripe.prices.create({ product, unit_amount, currency: 'usd', recurring: { interval } })
  }
  return price
}

async function ensurePaymentLink(priceId: string) {
  // Try to find existing payment link for the price
  const links = await stripe.paymentLinks.list({ active: true, limit: 100 })
  let link = links.data.find(l => l.line_items?.some(li => (li.price as string) === priceId))
  if (!link) {
    link = await stripe.paymentLinks.create({ line_items: [{ price: priceId, quantity: 1 }], after_completion: { type: 'redirect', redirect: { url: 'https://pikar.ai/billing' } } })
  }
  return link
}

async function upsertProductPrice(prod: Stripe.Product, price: Stripe.Price, paymentLinkUrl: string | null) {
  // Upsert product
  const { data: prodRow, error: prodErr } = await admin.from('billing_products').upsert({
    stripe_product_id: prod.id,
    name: prod.name,
    description: (prod.description as string) || null,
  }, { onConflict: 'stripe_product_id' }).select().single()
  if (prodErr) throw prodErr

  // Upsert price
  const { error: priceErr } = await admin.from('billing_prices').upsert({
    stripe_price_id: price.id,
    product_id: prodRow.id,
    currency: price.currency,
    unit_amount: price.unit_amount || 0,
    interval: price.recurring?.interval || null,
    interval_count: price.recurring?.interval_count || null,
    payment_link_url: paymentLinkUrl,
    active: price.active,
  }, { onConflict: 'stripe_price_id' })
  if (priceErr) throw priceErr
}

serve(async (req) => {
  try {
    if (!STRIPE_SECRET) return new Response('Stripe secret not set', { status: 500 })

    for (const tier of TIERS) {
      const prod = await ensureProduct(tier.name, `${tier.name} plan`)
      const monthly = await ensurePrice(prod.id, tier.amounts.monthly, 'month')
      const yearly = await ensurePrice(prod.id, tier.amounts.yearly, 'year')
      const monthlyLink = await ensurePaymentLink(monthly.id)
      const yearlyLink = await ensurePaymentLink(yearly.id)
      await upsertProductPrice(prod, monthly, monthlyLink?.url || null)
      await upsertProductPrice(prod, yearly, yearlyLink?.url || null)
    }

    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  } catch (e) {
    console.error(e)
    return new Response('Sync failed', { status: 500 })
  }
})

