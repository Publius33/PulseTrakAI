"""
Health Check and Readiness Probe Endpoints for PulseTrakAI™

Provides liveness, readiness, and metrics endpoints for Kubernetes health checks.
Monitors database connectivity, ML model status, Redis availability, Stripe connectivity.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
import os

try:
    import redis
except ImportError:
    redis = None

try:
    import stripe
except ImportError:
    stripe = None

logger = logging.getLogger(__name__)


class HealthChecker:
    """Check health of all system components."""
    
    def __init__(self):
        """Initialize health checker with component status."""
        self.last_db_check = None
        self.last_redis_check = None
        self.last_stripe_check = None
        self.last_ml_check = None
        self.startup_time = datetime.utcnow().isoformat()
        self.component_status = {}
    
    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            # Import here to avoid circular dependency
            from backend.app.main import get_db
            
            # Attempt simple query
            db = next(get_db())
            start = time.time()
            
            # Execute simple query
            result = db.execute("SELECT 1")
            result.fetchone()
            
            latency = (time.time() - start) * 1000  # ms
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def check_redis() -> Dict[str, Any]:
        """Check Redis connectivity (if configured)."""
        redis_url = os.environ.get("REDIS_URL")
        
        if not redis_url:
            return {
                "status": "not_configured",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if not redis:
            return {
                "status": "unavailable",
                "error": "redis library not installed",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            r = redis.from_url(redis_url)
            start = time.time()
            r.ping()
            latency = (time.time() - start) * 1000  # ms
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def check_stripe() -> Dict[str, Any]:
        """Check Stripe API connectivity."""
        stripe_key = os.environ.get("STRIPE_SECRET")
        
        if not stripe_key:
            return {
                "status": "not_configured",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if not stripe:
            return {
                "status": "unavailable",
                "error": "stripe library not installed",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            stripe.api_key = stripe_key
            start = time.time()
            
            # List customers (lightweight API call)
            stripe.Customer.list(limit=1)
            
            latency = (time.time() - start) * 1000  # ms
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Stripe health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def check_ml_model() -> Dict[str, Any]:
        """Check if ML model is loaded and responding."""
        try:
            # Import here to avoid circular dependency
            from backend.ml.service import MLService
            
            ml_service = MLService.get_instance()
            
            if not ml_service.is_model_loaded():
                return {
                    "status": "unhealthy",
                    "error": "Model not loaded",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Test prediction with dummy data
            start = time.time()
            prediction = ml_service.predict(
                metric_name="test",
                features=[1.0, 2.0, 3.0],
                lookback_days=1
            )
            latency = (time.time() - start) * 1000  # ms
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "model_loaded": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"ML model health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - datetime.fromisoformat(self.startup_time)).total_seconds(),
            "components": {
                "database": self.check_database(),
                "redis": self.check_redis(),
                "stripe": self.check_stripe(),
                "ml_model": self.check_ml_model()
            }
        }


class ReadinessChecker:
    """Check if service is ready to handle traffic."""
    
    @staticmethod
    def is_ready() -> bool:
        """Determine if service is ready for traffic."""
        try:
            # All critical components must be healthy
            health = HealthChecker().check_all()
            
            # Check database (critical)
            if health["components"]["database"]["status"] != "healthy":
                logger.error("Database not healthy - service not ready")
                return False
            
            # Check ML model (critical for predictions)
            if health["components"]["ml_model"]["status"] != "healthy":
                logger.error("ML model not loaded - service not ready")
                return False
            
            logger.info("✓ Service ready for traffic")
            return True
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return False
    
    @staticmethod
    def get_readiness_details() -> Dict[str, Any]:
        """Get detailed readiness information."""
        health = HealthChecker().check_all()
        
        critical_components = ["database", "ml_model"]
        ready_components = [
            c for c in critical_components
            if health["components"][c]["status"] == "healthy"
        ]
        
        return {
            "ready": len(ready_components) == len(critical_components),
            "timestamp": health["timestamp"],
            "components": health["components"],
            "critical_components": critical_components,
            "ready_components": ready_components
        }


class MetricsCollector:
    """Collect Prometheus-format metrics."""
    
    @staticmethod
    def collect_metrics() -> str:
        """Collect metrics in Prometheus text format."""
        metrics = []
        lines = []
        
        # Uptime
        uptime = (datetime.utcnow().isoformat())
        lines.append(f"# HELP pulsetrakapi_uptime_seconds Service uptime")
        lines.append(f"# TYPE pulsetrakapi_uptime_seconds gauge")
        
        # Health status (1=healthy, 0=unhealthy)
        health = HealthChecker().check_all()
        
        for component, status_dict in health["components"].items():
            status_value = 1 if status_dict.get("status") == "healthy" else 0
            lines.append(f"pulsetrakapi_component_health{{component=\"{component}\"}} {status_value}")
            
            if "latency_ms" in status_dict:
                lines.append(
                    f"pulsetrakapi_component_latency_ms{{component=\"{component}\"}} "
                    f"{status_dict['latency_ms']}"
                )
        
        # Database connection pool (if available)
        try:
            from backend.app.main import engine
            pool = engine.pool
            lines.append(f"pulsetrakapi_db_pool_size{{}} {pool.size()}")
            lines.append(f"pulsetrakapi_db_pool_checked_in{{}} {pool.checkedin()}")
        except Exception:
            pass
        
        return "\n".join(lines)


# Global instances
_health_checker: Optional[HealthChecker] = None
_readiness_checker: Optional[ReadinessChecker] = None


def get_health_checker() -> HealthChecker:
    """Get health checker instance."""
    global _health_checker
    if not _health_checker:
        _health_checker = HealthChecker()
    return _health_checker


def get_readiness_checker() -> ReadinessChecker:
    """Get readiness checker instance."""
    global _readiness_checker
    if not _readiness_checker:
        _readiness_checker = ReadinessChecker()
    return _readiness_checker
