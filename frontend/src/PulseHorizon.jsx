import React, { useEffect, useState } from 'react'

export default function PulseHorizon({ metric = 'cpu' }) {
  const [predictions, setPredictions] = useState([])
  const [prob, setProb] = useState(0)

  useEffect(() => {
    async function load() {
      try {
        const r = await fetch(`/api/pulse-horizon?metric=${metric}&horizon=24`)
        const j = await r.json()
        setPredictions(j.predictions || [])
        setProb(j.probability || 0)
      } catch (e) {}
    }
    load()
  }, [metric])

  return (
    <div style={{ marginTop: 18 }}>
      <h3>Pulse Horizon™ — {metric}</h3>
      <div>Risk (next 24h): <strong>{Math.round((prob || 0) * 100)}%</strong></div>
      <div style={{ marginTop: 8 }}>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(predictions.slice(0, 24), null, 2)}</pre>
      </div>
    </div>
  )
}
