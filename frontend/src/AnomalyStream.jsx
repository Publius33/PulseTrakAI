import React, { useEffect, useState } from 'react'

export default function AnomalyStream() {
  const [events, setEvents] = useState([])

  useEffect(() => {
    let mounted = true
    async function load() {
      try {
        const r = await fetch('/api/metrics')
        const j = await r.json()
        if (mounted) setEvents(j)
      } catch (e) {}
    }
    load()
    const t = setInterval(load, 5000)
    return () => { mounted = false; clearInterval(t) }
  }, [])

  return (
    <div style={{ marginTop: 18 }}>
      <h3>Micro-Anomaly Stream</h3>
      <div style={{ maxHeight: 140, overflow: 'auto', border: '1px solid #eee', padding: 8 }}>
        {events.length === 0 ? <div>No recent events</div> : (
          <ul>
            {events.map((e, i) => (<li key={i}>{e.event}: {e.count} (last: {e.last_ts})</li>))}
          </ul>
        )}
      </div>
    </div>
  )
}
