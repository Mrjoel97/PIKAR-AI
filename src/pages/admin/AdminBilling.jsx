import React, { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function AdminBilling() {
  const [products, setProducts] = useState([])
  const [prices, setPrices] = useState([])
  const [subs, setSubs] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    const { data: prods } = await supabase.from('billing_products').select('*').order('created_at')
    const { data: prcs } = await supabase.from('billing_prices').select('*, product:billing_products(name)').order('unit_amount')
    const { data: s } = await supabase.from('user_subscriptions').select('*').order('created_at', { ascending: false })
    setProducts(prods || [])
    setPrices(prcs || [])
    setSubs(s || [])
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const setPaymentLink = async (id, url) => {
    await supabase.from('billing_prices').update({ payment_link_url: url }).eq('id', id)
    load()
  }

  if (loading) return <div className="p-6">Loading...</div>

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Products</h2>
        <table className="min-w-full text-sm">
          <thead><tr className="bg-gray-50 text-left"><th className="p-2">Name</th><th className="p-2">Stripe Product ID</th></tr></thead>
          <tbody>
            {products.map(p => (
              <tr key={p.id} className="border-t"><td className="p-2">{p.name}</td><td className="p-2"><code>{p.stripe_product_id}</code></td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-2">Prices</h2>
        <table className="min-w-full text-sm">
          <thead><tr className="bg-gray-50 text-left"><th className="p-2">Product</th><th className="p-2">Amount</th><th className="p-2">Interval</th><th className="p-2">Stripe Price ID</th><th className="p-2">Payment Link</th></tr></thead>
          <tbody>
            {prices.map(p => (
              <tr key={p.id} className="border-t">
                <td className="p-2">{p.product?.name}</td>
                <td className="p-2">${(p.unit_amount/100).toFixed(2)}</td>
                <td className="p-2">{p.interval}</td>
                <td className="p-2"><code>{p.stripe_price_id}</code></td>
                <td className="p-2">
                  <input defaultValue={p.payment_link_url || ''} onBlur={(e)=>setPaymentLink(p.id, e.target.value)} placeholder="https://buy.stripe.com/..." className="border rounded px-2 py-1 w-80" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-2">User Subscriptions</h2>
        <table className="min-w-full text-sm">
          <thead><tr className="bg-gray-50 text-left"><th className="p-2">User</th><th className="p-2">Tier</th><th className="p-2">Status</th><th className="p-2">Period End</th><th className="p-2">Stripe Subscription ID</th></tr></thead>
          <tbody>
            {subs.map(s => (
              <tr key={s.id} className="border-t">
                <td className="p-2"><code>{s.user_id}</code></td>
                <td className="p-2">{s.tier}</td>
                <td className="p-2">{s.status}</td>
                <td className="p-2">{s.current_period_end ? new Date(s.current_period_end).toLocaleDateString() : '—'}</td>
                <td className="p-2"><code>{s.stripe_subscription_id || '—'}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

