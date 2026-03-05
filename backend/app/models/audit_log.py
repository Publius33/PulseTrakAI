"""
Audit Logging Models for PulseTrakAI™

ORM models for audit_logs table:
- User actions
- Model updates
- Admin operations
- Subscription changes

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any


class AuditLog:
    """Audit log entry model."""
    
    def __init__(
        self,
        user_id: str,
        action: str,
        endpoint: str,
        status: int = 200,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """
        Create audit log entry.
        
        Args:
            user_id: User who triggered action
            action: Action type (login, reload_model, subscription_change, etc.)
            endpoint: API endpoint called
            status: HTTP status code
            metadata: Additional context
            ip_address: Client IP address
        """
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.action = action
        self.endpoint = endpoint
        self.status = status
        self.metadata = metadata or {}
        self.ip_address = ip_address
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "endpoint": self.endpoint,
            "status": self.status,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return (
            f"AuditLog(id={self.id}, user={self.user_id}, "
            f"action={self.action}, status={self.status})"
        )


# Predefined action types
class AuditAction:
    """Standard audit action types."""
    
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    
    # Model management
    RELOAD_MODEL = "reload_model"
    ROLLBACK_MODEL = "rollback_model"
    TRIGGER_RETRAINING = "trigger_retraining"
    
    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    ROLE_CHANGED = "role_changed"
    
    # Subscription
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    PAYMENT_RECEIVED = "payment_received"
    
    # Admin
    ADMIN_CONFIG_CHANGED = "admin_config_changed"
    ADMIN_ACCESS_GRANTED = "admin_access_granted"
    ADMIN_ACCESS_REVOKED = "admin_access_revoked"
    
    # API key
    API_KEY_CREATED = "api_key_created"
    API_KEY_ROTATED = "api_key_rotated"
    API_KEY_REVOKED = "api_key_revoked"
