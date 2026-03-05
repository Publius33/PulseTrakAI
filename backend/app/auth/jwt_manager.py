"""
JWT Manager for PulseTrakAI™

Handles:
- Access & refresh token creation
- Token validation and expiry enforcement
- Refresh token rotation
- JWT signing key rotation support

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class JWTManager:
    """Manages JWT token lifecycle and rotation."""
    
    def __init__(self):
        """Initialize JWT manager with signing key from env."""
        self.secret_key = os.environ.get(
            "JWT_SECRET_KEY", 
            "replace-with-strong-random-key-in-production"
        )
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(
            os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", "15")
        )
        self.refresh_token_expire_days = int(
            os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7")
        )
        
        if self.secret_key == "replace-with-strong-random-key-in-production":
            logger.warning(
                "JWT_SECRET_KEY not set in environment. "
                "Using default key (INSECURE for production)"
            )
    
    def create_access_token(self, user_id: str, role: str = "user") -> str:
        """
        Create a short-lived access token.
        
        Args:
            user_id: Unique user identifier
            role: User role (user, admin, system)
        
        Returns:
            JWT access token
        """
        expires = datetime.utcnow() + timedelta(
            minutes=self.access_token_expire_minutes
        )
        
        payload = {
            "sub": user_id,
            "role": role,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": expires
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Access token created for user {user_id}")
        return token
    
    def create_refresh_token(self, user_id: str, role: str = "user") -> str:
        """
        Create a long-lived refresh token.
        
        Args:
            user_id: Unique user identifier
            role: User role
        
        Returns:
            JWT refresh token
        """
        expires = datetime.utcnow() + timedelta(
            days=self.refresh_token_expire_days
        )
        
        payload = {
            "sub": user_id,
            "role": role,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": expires,
            "jti": f"{user_id}_{datetime.utcnow().timestamp()}"  # unique ID for rotation
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Refresh token created for user {user_id}")
        return token
    
    def create_token_pair(self, user_id: str, role: str = "user") -> Dict[str, str]:
        """
        Create both access and refresh tokens.
        
        Returns:
            Dict with 'access_token' and 'refresh_token'
        """
        return {
            "access_token": self.create_access_token(user_id, role),
            "refresh_token": self.create_refresh_token(user_id, role),
            "token_type": "bearer"
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded payload if valid, None if invalid/expired
        """
        try:
            # Remove "Bearer " prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        
        except jwt.ExpiredSignatureError:
            logger.warning(f"Token expired: {token[:20]}...")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Create a new access token from a refresh token.
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            New access token if valid, None if invalid
        """
        payload = self.verify_token(refresh_token)
        
        if not payload:
            logger.warning("Failed to refresh: invalid refresh token")
            return None
        
        if payload.get("type") != "refresh":
            logger.warning("Attempted to use non-refresh token for refresh")
            return None
        
        # Create new access token with same user/role
        return self.create_access_token(
            user_id=payload["sub"],
            role=payload.get("role", "user")
        )
    
    def rotate_refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Rotate refresh token (issue new pair, invalidate old refresh).
        
        Args:
            refresh_token: Current refresh token
        
        Returns:
            New token pair if valid, None if invalid
        """
        payload = self.verify_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            logger.warning("Failed to rotate: invalid refresh token")
            return None
        
        user_id = payload["sub"]
        role = payload.get("role", "user")
        
        # TODO: Invalidate old refresh token in database (jti field)
        # For now, just issue new pair
        logger.info(f"Refresh token rotated for user {user_id}")
        return self.create_token_pair(user_id, role)
    
    def get_token_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Get token claims without expiry validation (for inspection)."""
        try:
            if token.startswith("Bearer "):
                token = token[7:]
            
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload
        except Exception as e:
            logger.warning(f"Failed to get token claims: {e}")
            return None


# Global instance
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """Get or create global JWT manager."""
    global _jwt_manager
    if not _jwt_manager:
        _jwt_manager = JWTManager()
    return _jwt_manager
