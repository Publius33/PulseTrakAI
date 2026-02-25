import React, { useEffect, useState } from 'react'
import PulseLogo from './pulsetrak-logo.svg'
import Billing from './Billing'
import Alerts from './Alerts'

export default function App() {
  const [backendError, setBackendError] = useState('')
  const [consent, setConsent] = useState(() => {
    try { return localStorage.getItem('pulsetrak_consent') === '1' } catch (e) { return false }
  })
  const [plans, setPlans] = useState([])
  const [subscriptions, setSubscriptions] = useState([])
  const [statusData, setStatusData] = useState(null)
  const [users, setUsers] = useState([])
  const [metrics, setMetrics] = useState([])
  const [apiKey, setApiKey] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  const [adminToken, setAdminToken] = useState('')

  useEffect(() => { refresh() }, [])

  useEffect(() => {
    if (!consent) return
    fetch('/api/analytics/track', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event: 'page_view' }) }).catch(() => {})
  }, [consent])

  function toggleConsent() {
    const next = !consent
    setConsent(next)
    try { localStorage.setItem('pulsetrak_consent', next ? '1' : '0') } catch (e) {}
  }

  async function refresh() {
    setBackendError('')
    try {
      const [pRes, sRes, stRes] = await Promise.all([
        fetch('/api/plans'),
        fetch('/api/subscriptions'),
        fetch('/api/status')
      ])
      if (!stRes.ok) {
        const j = await stRes.json().catch(() => ({}))
        const detail = j.detail || j.message || stRes.statusText
        setBackendError(detail)
      } else {
        const st = await stRes.json().catch(() => ({}))
        setStatusData(st)
      }
      const p = await pRes.json().catch(() => [])
      const s = await sRes.json().catch(() => [])
      setPlans(Array.isArray(p) ? p : [])
      setSubscriptions(Array.isArray(s) ? s : [])
    } catch (e) {
      setBackendError(e.message)
    }
  }

  async function getToken() {
    try {
      const r = await fetch('/api/admin/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: adminPassword }) })
      const j = await r.json().catch(() => ({}))
      // admin login returns { access_token: "..." }
      const token = j.access_token || j.token || j.accessToken
      if (r.ok && token) setAdminToken(token)
      else setBackendError(j.detail || j.message || 'failed to get token')
    } catch (e) { setBackendError(e.message) }
  }

  async function loadAdmin() {
    try {
      const headers = apiKey ? { 'X-API-Key': apiKey } : {}
      const [sRes, uRes, mRes] = await Promise.all([
        fetch('/api/status'),
        fetch('/api/users', { headers: { ...headers, 'X-Admin-Token': adminToken } }),
        fetch('/api/metrics', { headers: { 'X-Admin-Token': adminToken } }),
      ])
      const s = await sRes.json().catch(() => ({}))
      const u = await uRes.json().catch(() => [])
      const m = await mRes.json().catch(() => [])
      setStatusData(s)
      setUsers(u)
      setMetrics(m)
    } catch (e) { setBackendError(e.message) }
  }

  return (
    <div style={{
      maxWidth: 900,
      margin: '40px auto',
      padding: 30,
      fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      background: '#ffffff',
      borderRadius: 18,
      border: '1px solid #e6e6e6',
      boxShadow: '0 10px 28px rgba(0,0,0,0.06)'
    }}>

      <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 10 }}>
        <img src={PulseLogo} width={130} alt="PulseTrakAI Logo" />
        <div>
          <h1 style={{ margin: 0, fontSize: 34, fontWeight: 700, color: '#222' }}>PulseTrakAI™</h1>
          <p style={{ margin: 0, fontSize: 16, color: '#555' }}>AI-powered uptime, health & anonymous analytics</p>
        </div>
      </div>

      <div style={{ margin: '20px 0', padding: 12, background: '#fff5f5', borderLeft: '4px solid #ff5a5a', color: '#b30000', fontSize: 14 }}>
        <strong>Backend error:</strong> <span>{backendError || (statusData && statusData.error) || 'None'}</span>
      </div>

      <div style={{ marginBottom: 25 }}>
        <label style={{ fontSize: 15 }}>
          <input type="checkbox" checked={consent} onChange={() => toggleConsent()} /> Opt-in to anonymous analytics (page views)
        </label>
        <p style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
          Your consent is stored locally. This app never captures keystrokes — only anonymous, opt-in metrics.
        </p>
      </div>

      <Billing adminToken={adminToken} />
      <Alerts adminToken={adminToken} />

      <div style={{ marginTop: 40, padding: 20, border: '1px solid #ddd', borderRadius: 12, background: '#fafafa' }}>
        <h2 style={{ fontSize: 20 }}>Admin Panel</h2>

        <p style={{ fontSize: 14 }}>API Key (required for protected write endpoints):</p>
        <input id="apiKey" value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="text" style={{ width: '60%', padding: 8, borderRadius: 6, border: '1px solid #ccc', marginBottom: 10 }} placeholder="Enter API Key" />

        <p style={{ marginTop: 10, fontSize: 14 }}>Admin Password (to get JWT):</p>
        <input id="adminPassword" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} type="password" style={{ width: '60%', padding: 8, borderRadius: 6, border: '1px solid #ccc', marginBottom: 10 }} placeholder="Enter admin password" />

        <br />

        <button onClick={getToken} style={{ padding: '8px 12px', borderRadius: 6, border: 'none', background: '#007aff', color: '#fff', fontWeight: 600, marginRight: 10, cursor: 'pointer' }}>Get Token</button>
        <button onClick={loadAdmin} style={{ padding: '8px 12px', borderRadius: 6, border: 'none', background: '#444', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>Load</button>

        <h3 style={{ marginTop: 25 }}>Status</h3>
        <div id="status" style={{ color: '#777' }}>{statusData ? `${statusData.name || ''} — ${statusData.health || ''}` : 'Not loaded'}</div>

        <h3 style={{ marginTop: 20 }}>Users ({users.length})</h3>

        <h3 style={{ marginTop: 20 }}>Metrics ({metrics.length})</h3>

        <button onClick={async () => {
          try {
            const headers = adminToken ? { Authorization: `Bearer ${adminToken}` } : {}
            const res = await fetch('/api/billing/report', { headers })
            if (!res.ok) return
            const txt = await res.text()
            const blob = new Blob([txt], { type: 'text/csv' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'billing_report.csv'
            a.click()
            URL.revokeObjectURL(url)
          } catch (e) { setBackendError(e.message) }
        }} style={{ marginTop: 15, padding: '8px 14px', background: '#34c759', borderRadius: 8, border: 'none', color: 'white', cursor: 'pointer' }}>Download Billing CSV</button>

      </div>

      <div style={{ marginTop: 40, textAlign: 'center', fontSize: 12, color: '#888' }}>PulseTrakAI™ © {new Date().getFullYear()} PUBLIUS33 • All Rights Reserved.</div>

    </div>
  )
}
