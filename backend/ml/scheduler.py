"""
ML Model Retraining Scheduler for PulseTrakAI™

Schedules automatic model retraining:
- Every 7 days on a fixed schedule
- On demand when anomaly detection rate exceeds threshold
- Uses APScheduler for background job scheduling

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class RetrainingScheduler:
    """Scheduler for automated ML model retraining."""
    
    def __init__(self, 
                 training_func: Callable,
                 anomaly_threshold: float = 0.15,
                 retrain_interval_days: int = 7):
        """
        Initialize the retraining scheduler.
        
        Args:
            training_func: Callable that executes the training pipeline
            anomaly_threshold: Trigger retraining if anomaly rate > this (0.0-1.0)
            retrain_interval_days: Days between scheduled retraining (default 7)
        """
        self.scheduler = BackgroundScheduler()
        self.training_func = training_func
        self.anomaly_threshold = anomaly_threshold
        self.retrain_interval_days = retrain_interval_days
        self.last_training_time = None
        self.current_anomaly_rate = 0.0
    
    def get_anomaly_rate(self) -> float:
        """
        Fetch current anomaly detection rate from database.
        
        Returns:
            Anomaly detection rate (0.0-1.0)
        """
        # In production, query metric_events table to calculate:
        # anomaly_rate = count(is_anomaly=True) / total count in last 24h
        # This is a stub for scheduling purposes
        return self.current_anomaly_rate
    
    def check_and_retrain_on_anomaly(self):
        """Check anomaly rate and trigger retraining if threshold exceeded."""
        anomaly_rate = self.get_anomaly_rate()
        
        if anomaly_rate > self.anomaly_threshold:
            logger.warning(
                f"Anomaly rate {anomaly_rate:.2%} exceeds threshold "
                f"{self.anomaly_threshold:.2%}. Triggering retraining."
            )
            self._execute_training("anomaly_threshold_triggered")
        else:
            logger.debug(f"Anomaly rate {anomaly_rate:.2%} within acceptable range")
    
    def _execute_training(self, reason: str = "scheduled"):
        """Execute the training pipeline."""
        logger.info(f"Starting model retraining ({reason}) at {datetime.utcnow()}")
        
        try:
            result = self.training_func()
            self.last_training_time = datetime.utcnow()
            logger.info(f"Retraining completed successfully. Result: {result}")
            
            return {
                "status": "success",
                "timestamp": self.last_training_time.isoformat(),
                "reason": reason,
                "result": result
            }
        except Exception as e:
            logger.error(f"Retraining failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason,
                "error": str(e)
            }
    
    def start_scheduler(self):
        """Start the background scheduler with jobs."""
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        # Scheduled retraining: every 7 days at 2 AM UTC
        self.scheduler.add_job(
            self._execute_training,
            CronTrigger(hour=2, day_of_week=0),  # Monday 2 AM UTC
            args=("scheduled_weekly",),
            id="weekly_retrain",
            name="Weekly Model Retraining"
        )
        logger.info(
            f"Added job: Weekly retraining (every {self.retrain_interval_days} days at 2 AM UTC)"
        )
        
        # Anomaly-triggered retraining: check every 6 hours
        self.scheduler.add_job(
            self.check_and_retrain_on_anomaly,
            CronTrigger(hour="*/6"),
            id="anomaly_check",
            name="Anomaly-triggered Retraining Check"
        )
        logger.info("Added job: Anomaly check (every 6 hours)")
        
        self.scheduler.start()
        logger.info("Retraining scheduler started")
    
    def stop_scheduler(self):
        """Stop the background scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Retraining scheduler stopped")
    
    def get_job_status(self) -> dict:
        """Return status of all scheduled jobs."""
        jobs_info = {}
        
        for job in self.scheduler.get_jobs():
            jobs_info[job.id] = {
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
        
        return {
            "scheduler_running": self.scheduler.running,
            "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
            "current_anomaly_rate": self.current_anomaly_rate,
            "anomaly_threshold": self.anomaly_threshold,
            "jobs": jobs_info
        }


# Global scheduler instance (for use in FastAPI app)
_scheduler_instance: Optional[RetrainingScheduler] = None


def init_scheduler(training_func: Callable, anomaly_threshold: float = 0.15):
    """Initialize global scheduler instance."""
    global _scheduler_instance
    _scheduler_instance = RetrainingScheduler(
        training_func=training_func,
        anomaly_threshold=anomaly_threshold
    )
    _scheduler_instance.start_scheduler()
    return _scheduler_instance


def get_scheduler() -> Optional[RetrainingScheduler]:
    """Get global scheduler instance."""
    return _scheduler_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    def mock_training():
        return {"status": "mock training executed"}
    
    scheduler = RetrainingScheduler(training_func=mock_training)
    scheduler.start_scheduler()
    
    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop_scheduler()
