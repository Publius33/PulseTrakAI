"""
Model Drift Detection for PulseTrakAI™

Detects distribution shift in live predictions vs. baseline.
Triggers retraining if drift threshold exceeded.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detect model performance drift."""
    
    def __init__(
        self,
        drift_threshold: float = 0.15,
        min_samples: int = 100,
        baseline_days: int = 30
    ):
        """
        Initialize drift detector.
        
        Args:
            drift_threshold: Trigger retraining if deviation > this (0.0-1.0)
            min_samples: Minimum samples before checking drift
            baseline_days: Days to collect baseline data
        """
        self.drift_threshold = drift_threshold
        self.min_samples = min_samples
        self.baseline_days = baseline_days
        self.db_conn = None
    
    def check_drift(self, metric_name: str) -> Dict[str, any]:
        """
        Check if metric shows significant drift.
        
        Args:
            metric_name: Metric to check
        
        Returns:
            Dict with drift_detected, deviation, baseline_mean, current_mean
        """
        # Get baseline metrics (past N days)
        baseline = self._get_baseline_metrics(metric_name)
        
        if not baseline or len(baseline) < self.min_samples:
            logger.warning(f"Insufficient baseline for {metric_name}: {len(baseline) or 0} samples")
            return {
                "drift_detected": False,
                "deviation": 0.0,
                "reason": "insufficient_baseline"
            }
        
        # Get recent metrics (last 24 hours)
        current = self._get_recent_metrics(metric_name, hours=24)
        
        if not current or len(current) < 10:
            logger.warning(f"Insufficient recent data for {metric_name}: {len(current) or 0} samples")
            return {
                "drift_detected": False,
                "deviation": 0.0,
                "reason": "insufficient_recent_data"
            }
        
        # Calculate drift
        baseline_mean = statistics.mean(baseline)
        baseline_stdev = statistics.stdev(baseline) if len(baseline) > 1 else 1.0
        
        current_mean = statistics.mean(current)
        
        # Standardized deviation
        if baseline_stdev > 0:
            deviation = abs(current_mean - baseline_mean) / baseline_stdev
        else:
            deviation = 0.0
        
        # Normalize to 0-1 range
        deviation_normalized = min(1.0, deviation / 3.0)  # 3 std devs = max drift
        
        drift_detected = deviation_normalized > self.drift_threshold
        
        logger.info(
            f"Drift check for {metric_name}: "
            f"baseline_mean={baseline_mean:.4f}, "
            f"current_mean={current_mean:.4f}, "
            f"deviation={deviation_normalized:.4f}, "
            f"drift_detected={drift_detected}"
        )
        
        return {
            "metric_name": metric_name,
            "drift_detected": drift_detected,
            "deviation": round(deviation_normalized, 4),
            "baseline_mean": round(baseline_mean, 4),
            "current_mean": round(current_mean, 4),
            "baseline_samples": len(baseline),
            "current_samples": len(current),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_baseline_metrics(self, metric_name: str) -> list:
        """Get metric values from past N days."""
        if not self.db_conn:
            logger.warning("No database connection for baseline retrieval")
            return []
        
        cutoff = datetime.utcnow() - timedelta(days=self.baseline_days)
        
        try:
            cur = self.db_conn.cursor()
            cur.execute(
                """
                SELECT value FROM metric_events
                WHERE metric = ? AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10000
                """,
                (metric_name, cutoff.isoformat())
            )
            
            rows = cur.fetchall()
            values = [float(row[0]) for row in rows]
            return values
        
        except Exception as e:
            logger.error(f"Failed to fetch baseline metrics: {e}")
            return []
    
    def _get_recent_metrics(self, metric_name: str, hours: int = 24) -> list:
        """Get metric values from past N hours."""
        if not self.db_conn:
            logger.warning("No database connection for recent retrieval")
            return []
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        try:
            cur = self.db_conn.cursor()
            cur.execute(
                """
                SELECT value FROM metric_events
                WHERE metric = ? AND timestamp > ?
                ORDER BY timestamp DESC
                """,
                (metric_name, cutoff.isoformat())
            )
            
            rows = cur.fetchall()
            values = [float(row[0]) for row in rows]
            return values
        
        except Exception as e:
            logger.error(f"Failed to fetch recent metrics: {e}")
            return []
    
    def get_drift_report(self, metric_names: list) -> Dict[str, any]:
        """Generate drift report for multiple metrics."""
        results = []
        
        for metric_name in metric_names:
            drift_info = self.check_drift(metric_name)
            results.append(drift_info)
        
        # Summary
        drifting_count = sum(1 for r in results if r.get("drift_detected"))
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics_checked": len(metric_names),
            "metrics_drifting": drifting_count,
            "drift_threshold": self.drift_threshold,
            "details": results
        }


# Global instance
_drift_detector: Optional[DriftDetector] = None


def get_drift_detector() -> DriftDetector:
    """Get or create global drift detector."""
    global _drift_detector
    if not _drift_detector:
        _drift_detector = DriftDetector()
    return _drift_detector
