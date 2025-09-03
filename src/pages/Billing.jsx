import React, { useEffect, useState } from 'react'
import { billing } from '@/lib/billing'

export default function Billing() {
  const [sub, setSub] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    (async () => {
      try {
        const s = await billing.getMySubscription()
        setSub(s)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <div className="p-6">Loading...</div>
  if (!sub) return <div className="p-6">No subscription found.</div>

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-2">
      <h1 className="text-2xl font-bold">Your Subscription</h1>
      <div>Status: <b>{sub.status || '—'}</b></div>
      <div>Tier: <b>{sub.tier || '—'}</b></div>
      <div>Renews: <b>{sub.current_period_end ? new Date(sub.current_period_end).toLocaleString() : '—'}</b></div>
      <div>Stripe Subscription: <code className="text-xs">{sub.stripe_subscription_id || '—'}</code></div>
      <div>Stripe Price: <code className="text-xs">{sub.stripe_price_id || '—'}</code></div>
    </div>
  )
}

