import React, { useEffect, useState } from 'react'
import { loadStripe } from '@stripe/stripe-js'
import { Elements } from '@stripe/react-stripe-js'
import PaymentForm from './PaymentForm'

export default function Billing({ adminToken }) {
  const [plans, setPlans] = useState([])
  const [subs, setSubs] = useState([])
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [error, setError] = useState(null)
  const [stripePub, setStripePub] = useState(null)
  const [showCard, setShowCard] = useState(false)
  const [clientSecret, setClientSecret] = useState(null)

  const authHeaders = adminToken ? { Authorization: `Bearer ${adminToken}` } : {}

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [pRes, sRes] = await Promise.all([
        fetch('/api/plans', { headers: authHeaders }),
        fetch('/api/subscriptions', { headers: authHeaders }),
      ])
      const pjson = await pRes.json().catch(() => ({}))
      const sjson = await sRes.json().catch(() => [])
      const pList = pjson.plans || []
      setPlans(Array.isArray(pList) ? pList : [])
      setSubs(Array.isArray(sjson) ? sjson : [])
      if (!selectedPlan && pList && pList[0]) setSelectedPlan(pList[0].id)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [adminToken])

  useEffect(() => {
    async function cfg() {
      try {
        const r = await fetch('/api/stripe/config')
        const j = await r.json().catch(() => ({}))
        if (j.publishable_key) setStripePub(j.publishable_key)
      } catch (e) {}
    }
    cfg()
  }, [])

  async function createCustomer() {
    setError(null)
    if (!email) return setError('Missing email')
    try {
      const r = await fetch('/api/customers', { method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders }, body: JSON.stringify({ email }) })
      if (!r.ok) throw new Error(await r.text())
      const j = await r.json()
      return j.id
    } catch (e) { setError(e.message); return null }
  }

  async function subscribe() {
    setError(null)
    try {
      const stripeId = await createCustomer()
      if (!stripeId) return
      // lookup price by plan selection
      const plan = plans.find(p => p.id === selectedPlan)
      const priceCents = plan ? (plan.price_per_user_month || 0) * 100 : 0
      // If Stripe publishable key available, create a PaymentIntent and show card flow
      if (stripePub) {
        try {
          const pi = await fetch('/api/payment/create-intent', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ amount_cents: priceCents, currency: 'usd' }) })
          const pj = await pi.json()
          if (!pj.ready) {
            setError(pj.message || 'Payment provider not ready')
            return
          }
          setClientSecret(pj.client_secret)
          setShowCard(true)
          // keep stripeId available for later subscription creation after payment
          setPendingCustomer(stripeId)
          setPendingPrice(priceCents)
          return
        } catch (e) { setError(e.message); return }
      }

      // fallback: create subscription directly and simulate webhook
      const r = await fetch('/api/subscriptions', { method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders }, body: JSON.stringify({ customer_stripe_id: stripeId, price_cents: priceCents, currency: 'usd' }) })
      if (!r.ok) throw new Error(await r.text())
      const sub = await r.json().catch(() => ({}))
      // If Stripe isn't configured, we can simulate payment by calling webhook
      try {
        await fetch('/api/webhooks/stripe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'customer.subscription.created', data: { object: { id: sub.id, status: sub.status || 'active', items: { data: [{ price: { unit_amount: priceCents } }] } } } }) })
      } catch (e) {
        // ignore
      }
      await load()
    } catch (e) { setError(e.message) }
  }

  async function cancelSub(id) {
    setError(null)
    try {
      const r = await fetch(`/api/subscriptions/${id}/cancel`, { method: 'POST', headers: authHeaders })
      if (!r.ok) throw new Error(await r.text())
      // simulate webhook update for cancellation as well
      try {
        await fetch('/api/webhooks/stripe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'customer.subscription.deleted', data: { object: { id, status: 'canceled' } } }) })
      } catch (e) {}
      await load()
    } catch (e) { setError(e.message) }
  }

  const [pendingCustomer, setPendingCustomer] = useState(null)
  const [pendingPrice, setPendingPrice] = useState(null)

  async function onPaymentSucceeded(paymentIntent) {
    // after successful PaymentIntent, create subscription server-side
    try {
      if (!pendingCustomer) return
      const r = await fetch('/api/subscriptions', { method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders }, body: JSON.stringify({ customer_stripe_id: pendingCustomer, price_cents: pendingPrice, currency: 'usd' }) })
      if (!r.ok) throw new Error(await r.text())
      await load()
      setShowCard(false)
      setClientSecret(null)
      setPendingCustomer(null)
      setPendingPrice(null)
    } catch (e) { setError(e.message) }
  }

  return (
    <div style={{ marginTop: 18 }}>
      <h3>Billing</h3>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {loading && <div>Loading billing data…</div>}

      <div>
        <h4>Plans</h4>
        {plans.length === 0 ? (
          <div>No plans found</div>
        ) : (
          <div>
            <select value={selectedPlan || ''} onChange={(e) => setSelectedPlan(e.target.value)}>
              {plans.map((pl) => (
                <option key={pl.id} value={pl.id}>{pl.name} — ${pl.price_per_user_month}/mo</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div style={{ marginTop: 12 }}>
        <h4>Create subscription</h4>
        <input placeholder="user@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <button className="btn" onClick={subscribe} style={{ marginLeft: 8 }}>Subscribe</button>
        {stripePub && clientSecret && showCard && (
          <div style={{ marginTop: 12 }}>
            <Elements stripe={loadStripe(stripePub)}>
              <PaymentForm clientSecret={clientSecret} email={email} onSucceeded={onPaymentSucceeded} />
            </Elements>
          </div>
        )}
      </div>

      <div>
        <h4 style={{ marginTop: 16 }}>Subscriptions</h4>
        {subs.length === 0 ? (
          <div>No subscriptions</div>
        ) : (
          <ul>
            {subs.map((s) => (
              <li key={s.id}>{s.customer_id || s.stripe_id || s.id} — {s.status} — {s.id} <button onClick={() => cancelSub(s.id)} style={{ marginLeft: 8 }}>Cancel</button></li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ marginTop: 8 }}>
        <button className="btn" onClick={load}>Refresh</button>
      </div>
    </div>
  )
}
