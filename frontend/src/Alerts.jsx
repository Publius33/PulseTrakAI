import React, { useEffect, useState } from 'react'

export default function Alerts({ adminToken }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function load() {
    setLoading(true); setError(null)
    try {
      const headers = adminToken ? { Authorization: `Bearer ${adminToken}` } : {}
      const r = await fetch('/api/alerts', { headers })
      if (!r.ok) throw new Error(await r.text())
      const j = await r.json()
      setAlerts(j.alerts || [])
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [adminToken])

  function acknowledge(id) {
    setAlerts((a) => a.filter(x => x.id !== id))
  }

  return (
    <div style={{ marginTop: 18 }}>
      <h3>Alerts</h3>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {loading && <div>Loading alerts…</div>}
      {alerts.length === 0 ? <div>No alerts</div> : (
        <ul>
          {alerts.map(al => (
            <li key={al.id}>{al.metric} — {new Date(al.created_ts * 1000).toLocaleString()} <button onClick={() => acknowledge(al.id)} style={{ marginLeft: 8 }}>Acknowledge</button></li>
          ))}
        </ul>
      )}
    </div>
  )
}
