"""
ML microservice endpoints

Provides training, prediction, and baseline update endpoints used by the backend.

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""
from flask import Flask, request, jsonify
from .forecast_engine import LSTMForecaster, predict_horizons
from .baseline_model import update_baselines_from_db, get_baseline_for, compute_hourly_baseline
from .micro_anomaly_detector import detect_micro_anomaly, detect_persistent_anomaly
from .failure_chain_predictor import detect_precursors, aggregate_failure_chain
import os
import traceback
import pandas as pd

app = Flask(__name__)


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'tppm-ml'})


@app.route('/baseline', methods=['POST'])
def baseline():
    payload = request.get_json() or {}
    events = payload.get('events', [])
    df = compute_hourly_baseline(events)
    return df.to_json(orient='records')


@app.route('/train', methods=['POST'])
def train():
    try:
        payload = request.get_json() or {}
        metric = payload.get('metric')
        series = payload.get('series', [])
        epochs = int(payload.get('epochs', 5))
        if not metric or not series:
            return jsonify({'error': 'metric and series required'}), 400
        s = pd.Series(series)
        forecaster = LSTMForecaster(metric)
        forecaster.train(s, epochs=epochs)
        return jsonify({'status': 'trained', 'metric': metric})
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/predict-horizon', methods=['POST'])
def predict_horizon():
    try:
        payload = request.get_json() or {}
        metric = payload.get('metric')
        series = payload.get('series', [])
        if not metric or not series:
            return jsonify({'error': 'metric and series required'}), 400
        # ensure series is a pandas Series and pass metric name
        s = pd.Series(series)
        preds = predict_horizons(s, metric=metric)
        precursors = detect_precursors()
        agg = aggregate_failure_chain(precursors)
        return jsonify({'metric': metric, 'predictions': preds, 'precursors': precursors, 'aggregate': agg})
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/update-baselines', methods=['POST'])
def update_baselines():
    try:
        n = int((request.get_json() or {}).get('days', 1))
        update_baselines_from_db(days=n)
        return jsonify({'status': 'baselines_updated', 'days': n})
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/forecast', methods=['POST'])
def forecast():
    payload = request.get_json() or {}
    series = payload.get('series', [])
    s = pd.Series(series)
    res = predict_horizons(s, metric=payload.get('metric', 'unknown'))
    return jsonify({'forecast': res})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('ML_SERVICE_PORT', 9000)))
