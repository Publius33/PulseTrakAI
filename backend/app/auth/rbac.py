
"""
Role-Based Access Control (RBAC) for PulseTrakAI™

Manages:
- Role definitions (user, admin, system)
- Permission mapping
- Endpoint protection
- API key hashing

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import logging
from enum import Enum
from typing import Optional, Set
from functools import wraps
from fastacdcd /workspaces/PulseTrakAI/frontendrt HTTPException, Depends, Header
from .jwt_manager import get_jwt_manager


logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles."""
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class Permission(str, Enum):
    """Granular permissions."""
    # User permissions
    VIEW_METRICS = "view_metrics"
    CREATE_PREDICTION = "create_prediction"
    VIEW_PREDICTIONS = "view_predictions"
    # Admin permissions
    MANAGE_USERS = "manage_users"
    RELOAD_MODEL = "reload_model"
    TRIGGER_RETRAINING = "trigger_retraining"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_BILLING = "manage_billing"
    # System permissions
    SYSTEM_ADMIN = "system_admin"


# Role to permissions mapping
ROLE_PERMISSIONS: dict = {
    Role.USER: {
        Permission.VIEW_METRICS,
        Permission.CREATE_PREDICTION,
        Permission.VIEW_PREDICTIONS,
    },
    Role.ADMIN: {
        Permission.VIEW_METRICS,
        Permission.CREATE_PREDICTION,
        Permission.VIEW_PREDICTIONS,
        Permission.MANAGE_USERS,
        Permission.RELOAD_MODEL,
        Permission.TRIGGER_RETRAINING,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_BILLING,
    },
    Role.SYSTEM: {
        Permission.SYSTEM_ADMIN,  # All permissions
    },
}


class RBAC:
    """Role-Based Access Control manager."""
    
    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        """Check if role has permission."""
        if role == Role.SYSTEM:
            return True  # System role has all permissions
        return permission in ROLE_PERMISSIONS.get(role, set())
    
    @staticmethod
    def has_role(role: str) -> bool:
        """Check if role exists."""
        return role in [r.value for r in Role]
    
    @staticmethod
    def get_role_permissions(role: str) -> Set[Permission]:
        """Get all permissions for a role."""
        if not RBAC.has_role(role):
            return set()
        return ROLE_PERMISSIONS.get(Role(role), set())



# ...existing code...


def require_role(role: Role):
    """Decorator to require specific role."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = kwargs.get("user_role", Role.USER)
            
            if Role(user_role) != role:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role {role} required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class APIKeyManager:
    """Manage API keys with secure hashing."""
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash API key for storage.
        
        Production: use argon2 or bcrypt
        """
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            return ph.hash(api_key)
        except ImportError:
            # Fallback to simple hash if argon2 not available
            import hashlib
            return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(plain_key: str, hashed_key: str) -> bool:
        """Verify plain API key against hash."""
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            ph.verify(hashed_key, plain_key)
            return True
        except Exception:
            # Fallback comparison
            import hashlib
            return hashlib.sha256(plain_key.encode()).hexdigest() == hashed_key
    
    @staticmethod
    def get_api_key_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
        """Extract API key from X-API-Key or Authorization header."""
        if authorization:
            if authorization.startswith("Bearer "):
                return authorization[7:]
            if authorization.startswith("ApiKey "):
                return authorization[7:]
            return authorization
        return None


def verify_api_key_header(x_api_key: str = Header(None)) -> str:
    """Dependency to verify API key in header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    return x_api_key


def verify_admin(x_admin_token: str = Header(None)) -> bool:
    """Dependency to verify admin token."""
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "admintoken")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized: invalid admin token")
    return True


def get_current_role(authorization: Optional[str] = Header(None)) -> str:
    """FastAPI dependency: extract role from Authorization header using JWTManager.

    Returns a string role (`user`, `admin`, `system`). Raises 401 on invalid token.
    """
    jwtm = get_jwt_manager()
    if not authorization:
        return Role.USER.value

    token = authorization
    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]

    payload = jwtm.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    role = payload.get("role", Role.USER.value)
    if not RBAC.has_role(role):
        return Role.USER.value
    return role


def permission_required(permission: Permission):
    """Return a FastAPI dependency that enforces the given permission.

    Usage: `dep=Depends(permission_required(Permission.MANAGE_USERS))`
    """
    async def _dep(authorization: Optional[str] = Header(None)) -> bool:
        role = get_current_role(authorization)
        if not RBAC.has_permission(Role(role), permission):
            raise HTTPException(status_code=403, detail=f"Insufficient permissions for {permission}")
        return True

    return Depends(_dep)
