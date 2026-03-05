"""
service.py
Minimal HTTP wrapper placeholder for the pulsetrakai ml-engine.

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""

from flask import Flask, request, jsonify
from .forecast_engine import forecast

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/forecast', methods=['POST'])
def do_forecast():
    payload = request.get_json() or {}
    series = payload.get('series', [])
    return jsonify({'forecast': forecast(series)})
