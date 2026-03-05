import React, { useEffect, useState } from 'react'
import PulseLogo from './pulsetrak-logo.svg'
import Billing from './Billing'
import Alerts from './Alerts'
import PulseHorizon from './PulseHorizon'
import AnomalyStream from './AnomalyStream'
import RiskGauge from './RiskGauge'
import RecommendationsPanel from './RecommendationsPanel'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://api.pulsetrak.ai'
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === '1'

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
    fetch(`${API_BASE}/api/analytics/track`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event: 'page_view' }) }).catch(() => {})
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
        fetch(`${API_BASE}/api/plans`),
        fetch(`${API_BASE}/api/subscriptions`),
        fetch(`${API_BASE}/api/status`)
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
      const r = await fetch(`${API_BASE}/api/admin/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: adminPassword }) })
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
        fetch(`${API_BASE}/api/status`),
        fetch(`${API_BASE}/api/users`, { headers: { ...headers, 'X-Admin-Token': adminToken } }),
        fetch(`${API_BASE}/api/metrics`, { headers: { 'X-Admin-Token': adminToken } }),
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
      maxWidth: 1100,
      margin: '40px auto',
      padding: 30,
      fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      background: '#ffffff',
      borderRadius: 18,
      border: '1px solid #e6e6e6',
      boxShadow: '0 10px 28px rgba(0,0,0,0.06)'
    }}>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 18, alignItems: 'center', marginBottom: 18 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 36, fontWeight: 800, color: '#111' }}>AI-Powered Uptime & Predictive Monitoring</h1>
          <p style={{ margin: '10px 0 16px', fontSize: 18, color: '#444' }}>Temporal Pulse Prediction Model™ (TPPM™) keeps your stack healthy before incidents happen.</p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <a href="https://app.pulsetrak.ai/demo" style={{ padding: '12px 18px', background: '#007aff', color: '#fff', borderRadius: 10, fontWeight: 700, textDecoration: 'none' }}>Request Demo</a>
            <a href="https://app.pulsetrak.ai/dashboard" style={{ padding: '12px 18px', background: '#0f172a', color: '#fff', borderRadius: 10, fontWeight: 700, textDecoration: 'none' }}>View Dashboard</a>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <img src={PulseLogo} width={180} alt="PulseTrakAI Logo" style={{ filter: 'drop-shadow(0 12px 24px rgba(0,0,0,0.08))' }} />
        </div>
      </div>

      {DEMO_MODE && (
        <div style={{ margin: '10px 0 12px', padding: 12, background: '#eef2ff', borderLeft: '4px solid #4f46e5', color: '#1f2937', fontSize: 14 }}>
          Demo mode enabled: sample data is pre-seeded and write actions may be simulated.
        </div>
      )}

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

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 18 }}>
        <div>
          <PulseHorizon metric={'cpu'} />
          <AnomalyStream />
          <RecommendationsPanel metric={'cpu'} />
        </div>
        <div>
          <RiskGauge score={0.12} />
          <Billing adminToken={adminToken} />
          <Alerts adminToken={adminToken} />
        </div>
      </div>

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
            const res = await fetch(`${API_BASE}/api/billing/report`, { headers })
            if (!res.ok) return
            const 
            txt = await res.text()
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

      <div style={{ marginTop: 40, textAlign: 'center', fontSize: 12, color: '#888' }}>PulseTrakAI™ • AI uptime & anomaly intelligence • PUBLIUS33 • © {new Date().getFullYear()}</div>

    </div>
  )
}
