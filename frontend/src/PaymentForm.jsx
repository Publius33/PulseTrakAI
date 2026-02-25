import React, { useState } from 'react'
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js'

export default function PaymentForm({ clientSecret, email, onSucceeded }) {
  const stripe = useStripe()
  const elements = useElements()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      if (!stripe || !elements) throw new Error('Stripe not loaded')
      const card = elements.getElement(CardElement)
      const res = await stripe.confirmCardPayment(clientSecret, {
        payment_method: { card, billing_details: { email } }
      })
      if (res.error) {
        setError(res.error.message)
      } else if (res.paymentIntent && res.paymentIntent.status === 'succeeded') {
        onSucceeded(res.paymentIntent)
      } else {
        setError('Payment did not succeed')
      }
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  return (
    <form onSubmit={handleSubmit} style={{ marginTop: 12 }}>
      <div style={{ padding: 12, border: '1px solid #ddd', borderRadius: 8 }}>
        <CardElement />
      </div>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <button className="btn" type="submit" disabled={loading} style={{ marginTop: 10 }}>{loading ? 'Processing…' : 'Pay'}</button>
    </form>
  )
}
