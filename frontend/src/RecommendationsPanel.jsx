import React, { useEffect, useState } from 'react'

export default function RecommendationsPanel({ metric = 'cpu' }) {
  const [recs, setRecs] = useState([])

  useEffect(() => {
    async function load() {
      try {
        const r = await fetch(`/api/recommendations?metric=${metric}`)
        const j = await r.json()
        setRecs(j.recommendations || [])
      } catch (e) {}
    }
    load()
  }, [metric])

  return (
    <div style={{ marginTop: 18 }}>
      <h3>AI Recommendations</h3>
      <div>
        {recs.length === 0 ? <div>No recommendations</div> : (
          recs.map(r => (
            <div key={r.metric} style={{ padding: 12, border: '1px solid #eee', borderRadius: 8, marginBottom: 8 }}>
              <strong>{r.metric}</strong>
              <div style={{ color: '#444' }}>{r.recommendation}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
