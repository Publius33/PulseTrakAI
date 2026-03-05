"""
recommendation_engine.py
Generate human-readable recommendations given anomalies and predictions.

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""
from typing import List, Dict

TEMPLATES = [
    (lambda m: 'memory' in m.lower(), "Memory pressure trend indicates a possible GC leak; consider scaling or investigating memory retention."),
    (lambda m: 'cpu' in m.lower(), "CPU utilization trending upward; consider scaling service or optimizing hot paths."),
    (lambda m: 'network' in m.lower(), "Network variance detected; check upstream dependencies and circuit breakers."),
]

def generate_recommendations(metrics: List[Dict]) -> List[Dict]:
    out = []
    for m in metrics:
        name = m.get('metric', '')
        rec = None
        for cond, text in TEMPLATES:
            if cond(name):
                rec = text
                break
        if not rec:
            rec = f"Investigate {name} — unusual pattern detected."
        out.append({'metric': name, 'recommendation': rec, 'severity': m.get('severity', 'medium')})
    return out
