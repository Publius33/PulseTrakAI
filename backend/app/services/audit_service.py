"""
Audit Service for PulseTrakAI™

Service for creating and querying audit logs.
Stores to database and logs to structured logging system.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from backend.app.models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit logging operations."""
    
    def __init__(self, db_conn=None):
        """
        Initialize audit service.
        
        Args:
            db_conn: Database connection
        """
        self.db_conn = db_conn
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create audit_logs table if it doesn't exist."""
        if not self.db_conn:
            return
        
        cur = self.db_conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                endpoint TEXT,
                status INTEGER DEFAULT 200,
                metadata TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.db_conn.commit()
    
    def log_action(
        self,
        user_id: str,
        action: str,
        endpoint: str,
        status: int = 200,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            user_id: User performing action
            action: Action type (use AuditAction constants)
            endpoint: API endpoint
            status: HTTP status code
            metadata: Additional context
            ip_address: Client IP
        
        Returns:
            Created AuditLog object
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            endpoint=endpoint,
            status=status,
            metadata=metadata,
            ip_address=ip_address
        )
        
        # Store to database
        self._store_to_db(audit_log)
        
        # Log to structured logging
        self._log_to_logger(audit_log)
        
        return audit_log
    
    def _store_to_db(self, audit_log: AuditLog):
        """Store audit log to database."""
        if not self.db_conn:
            return
        
        try:
            import json
            
            cur = self.db_conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_logs 
                (id, user_id, action, endpoint, status, metadata, ip_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_log.id,
                    audit_log.user_id,
                    audit_log.action,
                    audit_log.endpoint,
                    audit_log.status,
                    json.dumps(audit_log.metadata),
                    audit_log.ip_address,
                    audit_log.created_at.isoformat()
                )
            )
            self.db_conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to store audit log: {e}")
    
    def _log_to_logger(self, audit_log: AuditLog):
        """Log audit event to structured logger."""
        log_level = "warning" if audit_log.status >= 400 else "info"
        
        log_message = (
            f"AUDIT | "
            f"user_id={audit_log.user_id} | "
            f"action={audit_log.action} | "
            f"endpoint={audit_log.endpoint} | "
            f"status={audit_log.status} | "
            f"ip={audit_log.ip_address}"
        )
        
        if log_level == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def get_user_actions(
        self,
        user_id: str,
        limit: int = 100,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a user.
        
        Args:
            user_id: User ID
            limit: Max results
            days: Look back N days
        
        Returns:
            List of audit log dicts
        """
        if not self.db_conn:
            return []
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        cur = self.db_conn.cursor()
        cur.execute(
            """
            SELECT * FROM audit_logs
            WHERE user_id = ? AND created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, cutoff.isoformat(), limit)
        )
        
        rows = cur.fetchall()
        return [dict(row) for row in rows] if rows else []
    
    def get_action_logs(
        self,
        action: str,
        limit: int = 100,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get logs for a specific action type."""
        if not self.db_conn:
            return []
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        cur = self.db_conn.cursor()
        cur.execute(
            """
            SELECT * FROM audit_logs
            WHERE action = ? AND created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (action, cutoff.isoformat(), limit)
        )
        
        rows = cur.fetchall()
        return [dict(row) for row in rows] if rows else []
    
    def get_failed_actions(
        self,
        limit: int = 100,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get all failed actions (status >= 400)."""
        if not self.db_conn:
            return []
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        cur = self.db_conn.cursor()
        cur.execute(
            """
            SELECT * FROM audit_logs
            WHERE status >= 400 AND created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (cutoff.isoformat(), limit)
        )
        
        rows = cur.fetchall()
        return [dict(row) for row in rows] if rows else []
    
    def get_admin_actions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all admin action logs."""
        if not self.db_conn:
            return []
        
        cur = self.db_conn.cursor()
        cur.execute(
            """
            SELECT * FROM audit_logs
            WHERE action IN (?, ?, ?, ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (
                AuditAction.RELOAD_MODEL,
                AuditAction.TRIGGER_RETRAINING,
                AuditAction.ADMIN_CONFIG_CHANGED,
                AuditAction.ADMIN_ACCESS_GRANTED,
                limit
            )
        )
        
        rows = cur.fetchall()
        return [dict(row) for row in rows] if rows else []


# Global instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get or create global audit service."""
    global _audit_service
    if not _audit_service:
        _audit_service = AuditService()
    return _audit_service
