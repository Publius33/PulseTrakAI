"""
forecast_engine.py
TPPM forecasting engine: FFT/STFT feature extraction and an LSTM-based forecaster.

This module provides a lightweight TensorFlow LSTM model for time-series
forecasting and helper functions to predict multiple horizons and produce
probability scores suitable for the Pulse Horizon API.

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""
from typing import List, Dict, Optional
import os
import numpy as np
import pandas as pd
from scipy.signal import stft

try:
    import tensorflow as tf
    from tensorflow.keras import layers, models
except Exception:
    tf = None

MODEL_DIR = os.environ.get('ML_MODEL_DIR', '/tmp/pulsetrak_ml_models')
os.makedirs(MODEL_DIR, exist_ok=True)


def extract_fft_features(series: pd.Series, n_features: int = 16) -> np.ndarray:
    x = np.asarray(series.fillna(method='ffill').fillna(0.0))
    # compute FFT magnitude and keep top coefficients
    fft = np.fft.rfft(x)
    mags = np.abs(fft)
    # take first n_features (low-frequency components)
    feats = np.zeros(n_features)
    take = min(len(mags), n_features)
    feats[:take] = mags[:take]
    return feats


def extract_stft_features(series: pd.Series, n_freqs: int = 8) -> np.ndarray:
    x = np.asarray(series.fillna(method='ffill').fillna(0.0))
    if len(x) < 8:
        return np.zeros(n_freqs)
    f, t, Zxx = stft(x, nperseg=min(64, len(x)))
    mags = np.abs(Zxx).mean(axis=1)
    feats = np.zeros(n_freqs)
    take = min(len(mags), n_freqs)
    feats[:take] = mags[:take]
    return feats


class LSTMForecaster:
    """Train and predict simple LSTM models per-metric.

    Models are persisted under `MODEL_DIR/{metric}.h5`.
    """
    def __init__(self, metric: str, lookback: int = 48):
        self.metric = metric
        self.lookback = lookback
        self.model_path = os.path.join(MODEL_DIR, f"{metric}.h5")
        self.model = None
        if tf is not None and os.path.exists(self.model_path):
            try:
                self.model = models.load_model(self.model_path)
            except Exception:
                self.model = None

    def _build_model(self):
        if tf is None:
            raise RuntimeError('TensorFlow not available')
        m = models.Sequential()
        m.add(layers.Input(shape=(self.lookback, 1)))
        m.add(layers.LSTM(64, return_sequences=False))
        m.add(layers.Dense(32, activation='relu'))
        m.add(layers.Dense(1))
        m.compile(optimizer='adam', loss='mse')
        return m

    def train(self, series: pd.Series, epochs: int = 10, batch_size: int = 32):
        if tf is None:
            raise RuntimeError('TensorFlow not available')
        x = np.asarray(series.ffill().fillna(0.0))
        if len(x) < self.lookback + 1:
            raise ValueError('Not enough data to train')
        X, Y = [], []
        for i in range(len(x) - self.lookback):
            X.append(x[i:i + self.lookback])
            Y.append(x[i + self.lookback])
        X = np.array(X).reshape(-1, self.lookback, 1)
        Y = np.array(Y).reshape(-1, 1)
        self.model = self._build_model()
        self.model.fit(X, Y, epochs=epochs, batch_size=batch_size, verbose=0)
        try:
            self.model.save(self.model_path)
        except Exception:
            pass

    def predict_continuation(self, series: pd.Series, horizon: int = 24) -> List[float]:
        x = np.asarray(series.ffill().fillna(0.0))
        if self.model is None:
            # fallback: repeat last value
            last = float(x[-1]) if len(x) > 0 else 0.0
            return [last for _ in range(horizon)]
        seq = x[-self.lookback:]
        preds = []
        for h in range(horizon):
            inp = np.array(seq[-self.lookback:]).reshape(1, self.lookback, 1)
            p = float(self.model.predict(inp, verbose=0).reshape(-1)[0])
            preds.append(p)
            seq = np.append(seq, p)
        return preds


def predict_horizons(series: pd.Series, metric: str, horizons: Optional[List[int]] = None) -> List[Dict]:
    """Predict multiple horizons and return list of {horizon, probability, explanation}.

    Probability mapping is heuristic: if predicted values trend away from recent baseline,
    map the magnitude to a probability via logistic scaling.
    """
    horizons = horizons or [1, 6, 24, 48, 72]
    # compute baseline stats
    recent = series.dropna()
    if recent.empty:
        return [{'horizon': h, 'probability': 0.0, 'explanation': 'no data'} for h in horizons]
    mean = float(recent.mean())
    std = float(recent.std()) if recent.std() else 0.0

    forecaster = LSTMForecaster(metric)
    results = []
    for h in horizons:
        preds = forecaster.predict_continuation(series, horizon=h)
        # look at max predicted point as risk proxy
        max_pred = float(np.max(preds)) if preds else mean
        delta = abs(max_pred - mean)
        # z-like score
        z = (delta / std) if std > 0 else (delta / max(1.0, abs(mean)))
        # map z to probability with logistic-ish function
        prob = 1.0 / (1.0 + np.exp(-0.8 * (z - 1.0)))
        explanation = f'Predicted max {max_pred:.3f} vs recent mean {mean:.3f} (z={z:.2f})'
        results.append({'horizon': h, 'probability': float(prob), 'explanation': explanation})
    return results
