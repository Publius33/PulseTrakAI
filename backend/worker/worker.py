"""
Background Worker System for PulseTrakAI™

Offloads heavy tasks to async queue:
- Retraining jobs
- Model backups
- Drift detection
- Report generation

Supports: Redis + RQ (default) or Celery

Start with: python -m backend.worker.worker

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import logging
import signal
import sys
from typing import Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class BackgroundWorker:
    """Background job worker system."""
    
    def __init__(self, queue_backend: str = "rq"):
        """
        Initialize worker.
        
        Args:
            queue_backend: 'rq' (Redis Queue) or 'celery'
        """
        self.queue_backend = queue_backend
        self.queue = None
        self.running = False
        
        self._initialize_queue()
    
    def _initialize_queue(self):
        """Initialize queue backend (Redis RQ or Celery)."""
        if self.queue_backend == "rq":
            self._init_rq()
        elif self.queue_backend == "celery":
            self._init_celery()
        else:
            raise ValueError(f"Unknown queue backend: {self.queue_backend}")
    
    def _init_rq(self):
        """Initialize Redis Queue."""
        try:
            import redis
            from rq import Queue, Worker
            
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
            redis_conn = redis.from_url(redis_url)
            self.queue = Queue(connection=redis_conn)
            self.worker_class = Worker
            
            logger.info("Initialized Redis Queue backend")
        except ImportError:
            logger.warning("rq not installed, falling back to in-process queue")
            self.queue = InProcessQueue()
    
    def _init_celery(self):
        """Initialize Celery."""
        try:
            from celery import Celery
            
            broker_url = os.environ.get(
                "CELERY_BROKER_URL",
                "redis://localhost:6379"
            )
            backend_url = os.environ.get(
                "CELERY_BACKEND_URL",
                "redis://localhost:6379"
            )
            
            app = Celery(
                "pulsetrakai",
                broker=broker_url,
                backend=backend_url
            )
            self.queue = app
            
            logger.info("Initialized Celery backend")
        except ImportError:
            logger.warning("celery not installed, falling back to in-process queue")
            self.queue = InProcessQueue()
    
    def enqueue_job(
        self,
        task_func: Callable,
        task_name: str,
        *args,
        **kwargs
    ) -> Optional[str]:
        """
        Enqueue a background job.
        
        Args:
            task_func: Callable to execute
            task_name: Name of task
            *args, **kwargs: Arguments to pass
        
        Returns:
            Job ID if successful
        """
        try:
            if self.queue_backend == "rq":
                job = self.queue.enqueue(task_func, *args, **kwargs)
                logger.info(f"Enqueued {task_name} (job_id={job.id})")
                return job.id
            elif self.queue_backend == "celery":
                result = task_func.delay(*args, **kwargs)
                logger.info(f"Enqueued {task_name} (task_id={result.id})")
                return result.id
            else:
                # Fallback: in-process
                logger.warning(f"No queue backend available, running {task_name} in-process")
                return self._run_in_process(task_func, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"Failed to enqueue {task_name}: {e}")
            return None
    
    def _run_in_process(self, func: Callable, *args, **kwargs) -> str:
        """Run task synchronously (fallback)."""
        try:
            result = func(*args, **kwargs)
            logger.info(f"Task completed in-process: {result}")
            return "in-process"
        except Exception as e:
            logger.error(f"Task failed: {e}", exc_info=True)
            raise
    
    def run_worker(self):
        """Start the worker process."""
        self.running = True
        logger.info(f"Starting background worker ({self.queue_backend})...")
        
        def signal_handler(sig, frame):
            logger.info("Shutdown signal received, stopping worker...")
            self.running = False
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        if self.queue_backend == "rq":
            self._run_rq_worker()
        elif self.queue_backend == "celery":
            self._run_celery_worker()
        else:
            self._run_in_process_worker()
    
    def _run_rq_worker(self):
        """Run RQ worker loop."""
        from rq import Worker
        import redis
        
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        redis_conn = redis.from_url(redis_url)
        worker = Worker(["default"], connection=redis_conn)
        
        logger.info("RQ worker started")
        worker.work()
    
    def _run_celery_worker(self):
        """Run Celery worker loop."""
        self.queue.worker_main(argv=["worker", "--loglevel=info"])
    
    def _run_in_process_worker(self):
        """Run in-process simulation (for testing)."""
        logger.warning("Running in-process worker (no external queue)")
        while self.running:
            import time
            time.sleep(1)


class InProcessQueue:
    """Simple in-process queue (for testing/dev)."""
    
    def enqueue(self, func: Callable, *args, **kwargs) -> object:
        """Execute function synchronously."""
        logger.info(f"Running {func.__name__} in-process")
        result = func(*args, **kwargs)
        
        # Create a mock job object
        class MockJob:
            def __init__(self, result):
                self.id = "in-process"
                self.result = result
        
        return MockJob(result)


# ============================================================================
# Background Tasks (register these with your queue)
# ============================================================================

def retrain_model_task(metric_name: str) -> dict:
    """Background task: trigger model retraining."""
    from backend.ml.training_pipeline import TrainingPipeline
    
    logger.info(f"[WORKER] Starting retraining for metric: {metric_name}")
    
    try:
        pipeline = TrainingPipeline()
        result = pipeline.run_training_pipeline(metric_name)
        
        logger.info(f"[WORKER] Retraining completed: {result}")
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"[WORKER] Retraining failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


def backup_model_task(model_version: str) -> dict:
    """Background task: backup model before deployment."""
    from backend.ml.backup_manager import BackupManager
    
    logger.info(f"[WORKER] Backing up model version: {model_version}")
    
    try:
        manager = BackupManager()
        backup = manager.create_backup(f"models/model_{model_version}.pkl", reason="automated")
        
        logger.info(f"[WORKER] Backup created: {backup}")
        return {"status": "success", "backup": backup}
    
    except Exception as e:
        logger.error(f"[WORKER] Backup failed: {e}")
        return {"status": "failed", "error": str(e)}


def detect_drift_task(metric_name: str) -> dict:
    """Background task: detect model drift."""
    from backend.ml.drift_detection import DriftDetector
    
    logger.info(f"[WORKER] Checking drift for metric: {metric_name}")
    
    try:
        detector = DriftDetector()
        drift_detected = detector.check_drift(metric_name)
        
        logger.info(f"[WORKER] Drift check completed: {drift_detected}")
        return {"status": "success", "drift_detected": drift_detected}
    
    except Exception as e:
        logger.error(f"[WORKER] Drift detection failed: {e}")
        return {"status": "failed", "error": str(e)}


def generate_report_task(report_type: str, date_range: dict) -> dict:
    """Background task: generate reports."""
    logger.info(f"[WORKER] Generating {report_type} report...")
    
    try:
        # Placeholder: actual report generation logic
        report = {
            "type": report_type,
            "date_range": date_range,
            "generated_at": datetime.utcnow().isoformat(),
            "rows": 1000
        }
        
        logger.info(f"[WORKER] Report generated")
        return {"status": "success", "report": report}
    
    except Exception as e:
        logger.error(f"[WORKER] Report generation failed: {e}")
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Determine backend from environment
    backend = os.environ.get("QUEUE_BACKEND", "rq")
    
    worker = BackgroundWorker(queue_backend=backend)
    worker.run_worker()
