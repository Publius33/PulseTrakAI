import React, { useEffect, useState } from 'react'
import AdminPanel from './Admin'
import PulseLogo from './pulse.svg'

export default function App() {
  const [status, setStatus] = useState({ loading: true, text: 'Loading...' })
  const [consent, setConsent] = useState(() => {
    try {
      return localStorage.getItem('pulsetrak_consent') === '1'
    } catch (e) { return false }
  })
  const [showAdmin, setShowAdmin] = useState(false)

  useEffect(() => {
    fetch('/api/status')
      .then(async (r) => {
        const json = await r.json().catch(() => ({}))
        if (!r.ok) {
          // show backend detail when available
          const detail = json.detail || json.message || r.statusText
          throw new Error(detail)
        }
        return json
      })
      .then((data) => setStatus({ loading: false, text: `Name: ${data.name} — Health: ${data.health} — Uptime: ${data.uptime_seconds}s` }))
      .catch((err) => setStatus({ loading: false, text: `Backend error: ${err.message}` }))
  }, [])

  useEffect(() => {
    if (!consent) return
    // track a page_view event when consent is given
    fetch('/api/analytics/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event: 'page_view' }),
    }).catch(() => {})
  }, [consent])

  function toggleConsent() {
    const next = !consent
    setConsent(next)
    try { localStorage.setItem('pulsetrak_consent', next ? '1' : '0') } catch (e) {}
  }

  return (
    <div className="container">
      <div className="header">
        <img src={PulseLogo} className="logo" alt="PulseTrakAI" />
        <div>
          <h1 style={{ margin: 0 }}>PulseTrakAI</h1>
          <div className="muted">AI-powered uptime, health & anonymous analytics</div>
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <p>{status.loading ? 'Checking backend...' : status.text}</p>
      </div>

      <div style={{ marginTop: 12 }}>
        <label>
          <input type="checkbox" checked={consent} onChange={toggleConsent} /> Opt-in to anonymous analytics (page views)
        </label>
        <span style={{ marginLeft: 12, color: '#666' }}>Your consent is stored locally.</span>
      </div>

      <p style={{ color: '#666', marginTop: 12 }}>
        Note: This app does NOT capture keystrokes. We will only collect anonymous, opt-in metrics.
      </p>

      <div style={{ marginTop: 12 }}>
        <button onClick={() => setShowAdmin((s) => !s)}>{showAdmin ? 'Hide' : 'Show'} Admin Panel</button>
      </div>

      {showAdmin && <AdminPanel onClose={() => setShowAdmin(false)} />}
    </div>
  )
}
