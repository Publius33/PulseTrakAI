import React from 'react'

export default function RiskGauge({ score = 0.12 }) {
  const pct = Math.round(Math.min(1, Math.max(0, score)) * 100)
  const color = pct > 70 ? '#ff4d4f' : pct > 30 ? '#ffb020' : '#34c759'
  return (
    <div style={{ marginTop: 18 }}>
      <h3>72h Stability Score</h3>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 90, height: 90, borderRadius: '50%', background: '#fff', boxShadow: '0 4px 12px rgba(0,0,0,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, color }}>{pct}%</div>
        <div style={{ color: '#666' }}>Lower is better. Animated gauge placeholder.</div>
      </div>
    </div>
  )
}
