import React, { useEffect, useState } from 'react'
import { billing } from '@/lib/billing'
import { useAuth } from '@/contexts/AuthContext'

export default function Pricing() {
  const [prices, setPrices] = useState([])
  const [loading, setLoading] = useState(true)
  const { isAuthenticated } = useAuth()

  useEffect(() => {
    (async () => {
      try {
        const list = await billing.listActivePrices()
        setPrices(list)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <div className="p-8">Loading...</div>

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Choose your plan</h1>
      <div className="grid md:grid-cols-3 gap-4">
        {prices.map(p => (
          <div key={p.id} className="border rounded-lg p-4 bg-white">
            <div className="text-lg font-semibold">{p.product?.name}</div>
            <div className="text-sm text-gray-500 mb-2">{p.product?.description}</div>
            <div className="text-3xl font-bold mb-4">${(p.unit_amount/100).toFixed(2)}<span className="text-base font-normal text-gray-500">/{p.interval || 'one-time'}</span></div>
            {p.payment_link_url ? (
              <a href={p.payment_link_url} className="block text-center px-4 py-2 rounded bg-emerald-600 text-white">{isAuthenticated ? 'Subscribe' : 'Sign in to Subscribe'}</a>
            ) : (
              <button disabled className="block w-full text-center px-4 py-2 rounded border">Unavailable</button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

