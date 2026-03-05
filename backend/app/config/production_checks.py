"""
Production Configuration Validation for PulseTrakAI™

Validates critical configuration on startup.
Fails immediately if production safety checks fail.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import logging
import sys

logger = logging.getLogger(__name__)


class ProductionChecks:
    """Production environment validation."""
    
    @staticmethod
    def is_production() -> bool:
        """Detect if running in production."""
        env = os.environ.get("ENVIRONMENT", "development").lower()
        return env in ["production", "prod"]
    
    @staticmethod
    def validate_stripe_config() -> bool:
        """Ensure Stripe keys are configured."""
        if not (os.environ.get("STRIPE_SECRET") or os.environ.get("STRIPE_SECRET_KEY")):
            logger.error("STRIPE_SECRET or STRIPE_SECRET_KEY not set in environment")
            return False
        
        if not os.environ.get("STRIPE_PUBLISHABLE_KEY"):
            logger.error("STRIPE_PUBLISHABLE_KEY not set in environment")
            return False
        
        if not os.environ.get("STRIPE_WEBHOOK_SECRET"):
            logger.warning("STRIPE_WEBHOOK_SECRET not set - webhooks will fail")
        
        logger.info("✓ Stripe configuration validated")
        return True
    
    @staticmethod
    def validate_database_config() -> bool:
        """Ensure database is not sqlite in production."""
        db_url = os.environ.get("DATABASE_URL", "")
        db_path = os.environ.get("DB_PATH", "")
        is_prod = ProductionChecks.is_production()
        
        if is_prod:
            if not db_url:
                logger.error(
                    "DATABASE_URL not set in production. "
                    "Must use PostgreSQL (not SQLite)"
                )
                return False
            
            if "sqlite" in db_url.lower():
                logger.error("SQLite database detected in production - must use PostgreSQL")
                return False
            
            if "postgres" not in db_url.lower():
                logger.warning(f"Non-PostgreSQL database detected: {db_url}")
        
        logger.info("✓ Database configuration validated")
        return True
    
    @staticmethod
    def validate_secret_key() -> bool:
        """Ensure JWT secret key is strong."""
        secret = os.environ.get("JWT_SECRET_KEY", "")
        
        if not secret:
            logger.error("JWT_SECRET_KEY not set in environment")
            return False
        
        if secret == "replace-with-strong-random-key-in-production":
            logger.error("JWT_SECRET_KEY has default value - must change")
            return False
        
        if len(secret) < 32:
            logger.warning(f"JWT_SECRET_KEY is very short ({len(secret)} chars) - recommend 64+ chars")
        
        logger.info("✓ Secret key validated")
        return True
    
    @staticmethod
    def validate_admin_token() -> bool:
        """Ensure admin token is configured."""
        token = os.environ.get("ADMIN_TOKEN", "")
        
        if not token or token == "admintoken":
            logger.error(
                "ADMIN_TOKEN not configured or using default value. "
                "Must set strong random token in production"
            )
            return False
        
        logger.info("✓ Admin token validated")
        return True
    
    @staticmethod
    def validate_rate_limiting() -> bool:
        """Ensure rate limiting enabled in production."""
        is_prod = ProductionChecks.is_production()
        
        if is_prod:
            rate_limit_enabled = os.environ.get("ENABLE_RATE_LIMIT", "1") == "1"
            
            if not rate_limit_enabled:
                logger.error("Rate limiting disabled in production - security risk")
                return False
        
        logger.info("✓ Rate limiting configuration validated")
        return True
    
    @staticmethod
    def validate_redis_config() -> bool:
        """Ensure Redis is available if using queues."""
        queue_backend = os.environ.get("QUEUE_BACKEND", "").lower()
        
        if queue_backend not in ["rq", "celery", ""]:
            return True  # Not using queues
        
        if queue_backend:
            redis_url = os.environ.get("REDIS_URL", "")
            
            if not redis_url and queue_backend == "rq":
                logger.warning("REDIS_URL not set - will fall back to in-process queue")
        
        logger.info("✓ Redis configuration validated")
        return True
    
    @staticmethod
    def validate_ssl_certificates() -> bool:
        """Ensure SSL is enforced in production."""
        is_prod = ProductionChecks.is_production()
        
        if is_prod:
            ssl_redirect = os.environ.get("SSL_REDIRECT", "1") == "1"
            
            if not ssl_redirect:
                logger.error("SSL redirect disabled in production")
                return False
        
        logger.info("✓ SSL configuration validated")
        return True
    
    @staticmethod
    def validate_debug_mode() -> bool:
        """Ensure DEBUG mode is off in production."""
        is_prod = ProductionChecks.is_production()
        
        if is_prod:
            debug = os.environ.get("DEBUG", "").lower() == "true"
            
            if debug:
                logger.error("DEBUG mode enabled in production - SECURITY RISK")
                return False
        
        logger.info("✓ Debug mode configuration validated")
        return True
    
    @staticmethod
    def validate_logging_config() -> bool:
        """Ensure structured logging is configured."""
        log_format = os.environ.get("LOG_FORMAT", "json")
        
        if log_format not in ["json", "text"]:
            logger.warning(f"Unknown log format: {log_format}")
        
        logger.info("✓ Logging configuration validated")
        return True
    
    @staticmethod
    def run_all_checks() -> bool:
        """Run all production validation checks."""
        logger.info("Running production safety checks...")
        
        checks = [
            ("Stripe Config", ProductionChecks.validate_stripe_config),
            ("Database Config", ProductionChecks.validate_database_config),
            ("Secret Key", ProductionChecks.validate_secret_key),
            ("Admin Token", ProductionChecks.validate_admin_token),
            ("Rate Limiting", ProductionChecks.validate_rate_limiting),
            ("Redis Config", ProductionChecks.validate_redis_config),
            ("SSL Config", ProductionChecks.validate_ssl_certificates),
            ("Debug Mode", ProductionChecks.validate_debug_mode),
            ("Logging Config", ProductionChecks.validate_logging_config),
        ]
        
        failed = []
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                if not result:
                    failed.append(check_name)
            except Exception as e:
                logger.error(f"Check {check_name} failed with exception: {e}")
                failed.append(check_name)
        
        if failed:
            logger.error(f"❌ {len(failed)} production checks failed: {', '.join(failed)}")
            
            if ProductionChecks.is_production():
                logger.critical("FAILING STARTUP - Production safety checks failed")
                sys.exit(1)
            else:
                logger.warning("Production checks failed but not in production mode - continuing")
                return False
        
        logger.info("✅ All production safety checks passed")
        return True


def validate_production_config():
    """Validate production configuration on startup."""
    return ProductionChecks.run_all_checks()
