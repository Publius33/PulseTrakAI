"""
Token Rotation Manager for PulseTrakAI™

Implements secure token rotation strategy:
- Invalidate old refresh tokens
- Track token rotation history
- Detect suspicious rotation patterns

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import uuid

logger = logging.getLogger(__name__)


class TokenRotationManager:
    """Manages token rotation and invalidation."""
    
    def __init__(self, db_conn=None):
        """
        Initialize token rotation manager.
        
        Args:
            db_conn: Database connection for persistence
        """
        self.db_conn = db_conn
        # In-memory store for dev (use Redis/DB in production)
        self._revoked_tokens: Dict[str, datetime] = {}
        self._rotation_history: Dict[str, List[Dict]] = {}
    
    def create_rotation_id(self) -> str:
        """Generate unique rotation identifier."""
        return str(uuid.uuid4())
    
    def record_rotation(self, user_id: str, old_token_jti: str, new_token_jti: str):
        """
        Record a token rotation event.
        
        Args:
            user_id: User performing rotation
            old_token_jti: JTI (JWT ID) of old token
            new_token_jti: JTI of new token
        """
        if user_id not in self._rotation_history:
            self._rotation_history[user_id] = []
        
        self._rotation_history[user_id].append({
            "timestamp": datetime.utcnow(),
            "old_jti": old_token_jti,
            "new_jti": new_token_jti,
            "rotation_id": self.create_rotation_id()
        })
        
        logger.info(f"Token rotation recorded for user {user_id}")
    
    def revoke_token(self, token_jti: str, expiry: datetime):
        """
        Add token to revocation list.
        
        Args:
            token_jti: JWT ID to revoke
            expiry: When token expires (don't need to store after this)
        """
        self._revoked_tokens[token_jti] = expiry
        logger.info(f"Token revoked: {token_jti}")
    
    def is_token_revoked(self, token_jti: str) -> bool:
        """Check if token is in revocation list."""
        if token_jti not in self._revoked_tokens:
            return False
        
        # Remove if expiry passed
        if datetime.utcnow() > self._revoked_tokens[token_jti]:
            del self._revoked_tokens[token_jti]
            return False
        
        return True
    
    def cleanup_expired_revocations(self):
        """Remove expired tokens from revocation list."""
        expired = [
            jti for jti, expiry in self._revoked_tokens.items()
            if datetime.utcnow() > expiry
        ]
        
        for jti in expired:
            del self._revoked_tokens[jti]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired revocations")
    
    def detect_suspicious_rotation(self, user_id: str, window_minutes: int = 5) -> bool:
        """
        Detect suspicious rotation patterns (multiple rotations in short time).
        
        Args:
            user_id: User to check
            window_minutes: Time window to check
        
        Returns:
            True if suspicious pattern detected
        """
        if user_id not in self._rotation_history:
            return False
        
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_rotations = [
            r for r in self._rotation_history[user_id]
            if r["timestamp"] > cutoff
        ]
        
        # Suspicious if > 3 rotations in 5 minutes
        if len(recent_rotations) > 3:
            logger.warning(f"Suspicious rotation pattern detected for user {user_id}")
            return True
        
        return False
    
    def get_rotation_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get token rotation history for user."""
        if user_id not in self._rotation_history:
            return []
        
        return self._rotation_history[user_id][-limit:]


# Global instance
_rotation_manager: Optional[TokenRotationManager] = None


def get_rotation_manager() -> TokenRotationManager:
    """Get or create global token rotation manager."""
    global _rotation_manager
    if not _rotation_manager:
        _rotation_manager = TokenRotationManager()
    return _rotation_manager
