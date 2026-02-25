import React, { useState } from 'react'

export default function AdminPanel({ onClose }) {
  const [apiKey, setApiKey] = useState('')
  const [adminToken, setAdminToken] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  const [status, setStatus] = useState(null)
  const [users, setUsers] = useState([])
  const [metrics, setMetrics] = useState([])

  async function loadAll() {
    setStatus('loading')
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
      setStatus(s)
      setUsers(u)
      setMetrics(m)
    } catch (err) {
      setStatus({ error: err.message })
    }
  }

  return (
    <div style={{ border: '1px solid #ddd', padding: 12, marginTop: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <strong>Admin Panel</strong>
        <button onClick={onClose}>Close</button>
      </div>

      <div style={{ marginTop: 8 }}>
        <label>
          API Key (required for protected write endpoints):{' '}
          <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
        </label>
        <label style={{ marginLeft: 8 }}>
          Admin Password (to get JWT):{' '}
          <input value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} />
        </label>
        <button style={{ marginLeft: 8 }} onClick={async () => {
          // request JWT from backend
          try {
            const r = await fetch('/api/admin/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: adminPassword }) })
            const j = await r.json()
            if (r.ok && j.token) {
              setAdminToken(j.token)
              alert('Admin token received')
            } else {
              alert('Failed to get token: ' + (j.detail || j.message || JSON.stringify(j)))
            }
          } catch (e) { alert('Login failed') }
        }}>Get Token</button>
        <button style={{ marginLeft: 8 }} onClick={loadAll}>
          Load
        </button>
      </div>

      <div style={{ marginTop: 12 }}>
        <h4>Status</h4>
        <pre>{status ? JSON.stringify(status, null, 2) : 'Not loaded'}</pre>
      </div>

      <div>
        <h4>Users ({users.length})</h4>
        <ul>
          {users.map((u) => (
            <li key={u.id}>{u.username} — {u.id}</li>
          ))}
        </ul>
      </div>

      <div>
        <h4>Metrics ({metrics.length})</h4>
        <button onClick={async () => {
          // download billing report
          const res = await fetch('/api/billing/report', { headers: { 'X-Admin-Token': adminToken } })
          if (!res.ok) return
          const txt = await res.text()
          const blob = new Blob([txt], { type: 'text/csv' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = 'billing_report.csv'
          a.click()
          URL.revokeObjectURL(url)
        }}>Download Billing CSV</button>
        <ul>
          {metrics.map((m) => (
            <li key={m.event}>{m.event}: {m.count} (last: {m.last_ts})</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
