// Supabase Edge Function: Stripe Webhooks (Test Mode Ready)
// Deploy: supabase functions deploy stripe-webhooks
// Set secrets: supabase secrets set STRIPE_WEBHOOK_SECRET=... STRIPE_SECRET_KEY=...
// Connect endpoint in Stripe Dashboard to: <your-supabase-functions-url>/stripe-webhooks

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import Stripe from 'https://esm.sh/stripe@14.11.0?target=deno'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.45.4'

const STRIPE_SECRET = Deno.env.get('STRIPE_SECRET_KEY')
const WEBHOOK_SECRET = Deno.env.get('STRIPE_WEBHOOK_SECRET')
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!

const stripe = new Stripe(STRIPE_SECRET || '', { apiVersion: '2024-06-20' })
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

async function upsertUserSubscription(payload: {
  user_id: string
  stripe_customer_id?: string
  stripe_subscription_id?: string
  stripe_price_id?: string
  status?: string
  current_period_end?: number | null
  tier?: string | null
}) {
  const data: any = {
    user_id: payload.user_id,
    stripe_customer_id: payload.stripe_customer_id ?? null,
    stripe_subscription_id: payload.stripe_subscription_id ?? null,
    stripe_price_id: payload.stripe_price_id ?? null,
    status: payload.status ?? null,
    tier: payload.tier ?? null,
  }
  if (payload.current_period_end) {
    data.current_period_end = new Date(payload.current_period_end * 1000).toISOString()
  }
  const { data: row, error } = await supabase
    .from('user_subscriptions')
    .upsert(data, { onConflict: 'user_id' })
    .select('*')
    .single()
  if (error) throw error
  return row
}

async function mapPriceToTier(stripe_price_id?: string | null): Promise<string | null> {
  if (!stripe_price_id) return null
  const { data, error } = await supabase
    .from('billing_prices')
    .select('stripe_price_id, product:billing_products(name)')
    .eq('stripe_price_id', stripe_price_id)
    .maybeSingle()
  if (error) throw error
  // Infer tier from product name
  const name = data?.product?.name?.toLowerCase() || ''
  if (name.includes('solo')) return 'solopreneur'
  if (name.includes('startup')) return 'startup'
  if (name.includes('sme')) return 'sme'
  if (name.includes('enterprise')) return 'enterprise'
  return null
}

serve(async (req) => {
  if (req.method !== 'POST') return new Response('Method not allowed', { status: 405 })
  const body = await req.text()

  if (!WEBHOOK_SECRET) return new Response('Missing webhook secret', { status: 500 })

  let event: Stripe.Event
  try {
    const sig = req.headers.get('stripe-signature')!
    event = stripe.webhooks.constructEvent(body, sig, WEBHOOK_SECRET)
  } catch (err) {
    console.error('Webhook signature verification failed', err)
    return new Response('Bad signature', { status: 400 })
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session
        const subscriptionId = session.subscription as string | undefined
        const customerId = session.customer as string | undefined
        const priceId = (session?.line_items?.data?.[0]?.price?.id as string) || (session?.metadata?.price_id as string) || undefined

        // We expect you to pass user_id in metadata when creating Checkout (if used)
        const user_id = (session.metadata && session.metadata.user_id) || ''
        const tier = await mapPriceToTier(priceId)

        if (user_id) {
          await upsertUserSubscription({
            user_id,
            stripe_customer_id: customerId,
            stripe_subscription_id: subscriptionId,
            stripe_price_id: priceId,
            status: 'active',
            current_period_end: null,
            tier,
          })
        }
        break
      }
      case 'customer.subscription.updated':
      case 'customer.subscription.created': {
        const sub = event.data.object as Stripe.Subscription
        const priceId = (sub.items.data[0]?.price?.id as string) || undefined
        const customerId = sub.customer as string | undefined
        // Map customer to user via your own mapping; if not available, you can store it
        // Here we try to find by existing user_subscriptions row with same customer
        const { data: existing } = await supabase
          .from('user_subscriptions')
          .select('user_id')
          .eq('stripe_customer_id', customerId)
          .maybeSingle()
        const user_id = existing?.user_id || ''
        const tier = await mapPriceToTier(priceId)
        if (user_id) {
          await upsertUserSubscription({
            user_id,
            stripe_customer_id: customerId,
            stripe_subscription_id: sub.id,
            stripe_price_id: priceId,
            status: sub.status,
            current_period_end: sub.current_period_end || null,
            tier,
          })
        }
        break
      }
      case 'customer.subscription.deleted': {
        const sub = event.data.object as Stripe.Subscription
        const customerId = sub.customer as string | undefined
        const { data: existing } = await supabase
          .from('user_subscriptions')
          .select('user_id')
          .eq('stripe_customer_id', customerId)
          .maybeSingle()
        const user_id = existing?.user_id || ''
        if (user_id) {
          await upsertUserSubscription({
            user_id,
            stripe_customer_id: customerId,
            stripe_subscription_id: sub.id,
            stripe_price_id: (sub.items.data[0]?.price?.id as string) || undefined,
            status: 'canceled',
            current_period_end: sub.current_period_end || null,
            tier: null,
          })
        }
        break
      }
      default:
        // Ignore other events for now
        break
    }
    return new Response(JSON.stringify({ received: true }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  } catch (err) {
    console.error('Webhook processing error', err)
    return new Response('Webhook error', { status: 500 })
  }
})

