"""ML package for PulseTrakAI TPPM

This module exposes lightweight wrappers that lazily import heavy ML
dependencies only when the functions are invoked. This keeps `import ml`
cheap for tests that don't require full ML stack.

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""

from typing import Any, List, Dict, Optional


def compute_hourly_baseline(events: List[Dict]) -> Any:
	from .baseline_model import compute_hourly_baseline as _f

	return _f(events)


def update_baselines_from_db(days: int = 14):
	from .baseline_model import update_baselines_from_db as _f

	return _f(window_days=days)


def get_baseline_for(metric: str, ts) -> Dict:
	from .baseline_model import get_baseline_for as _f

	return _f(metric, ts)


def detect_micro_anomaly(value, baseline_row, **kwargs):
	from .micro_anomaly_detector import detect_micro_anomaly as _f

	return _f(value, baseline_row, **kwargs)


def detect_persistent_anomaly(metric: str, **kwargs):
	from .micro_anomaly_detector import detect_persistent_anomaly as _f

	return _f(metric, **kwargs)


def predict_horizons(series, metric: str, horizons: Optional[List[int]] = None):
	from .forecast_engine import predict_horizons as _f

	return _f(series, metric=metric, horizons=horizons)


def detect_precursors(metrics: List[str] = None):
	from .failure_chain_predictor import detect_precursors as _f

	return _f(metrics)


def aggregate_failure_chain(preds: List[Dict]):
	from .failure_chain_predictor import aggregate_failure_chain as _f

	return _f(preds)


def generate_recommendations(items: List[Dict]):
	from .recommendation_engine import generate_recommendations as _f

	return _f(items)
