"""
Security utilities: password hashing, JWT tokens, permissions.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from passlib.hash import argon2
from jose import JWTError, jwt
from .config import settings
import logging

logger = logging.getLogger(__name__)


# Password Hashing
def hash_password(password: str) -> str:
    """
    Hash password using Argon2id.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return argon2.using(
        time_cost=2,
        memory_cost=65536,
        parallelism=1,
        salt_len=16
    ).hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        password: Plain text password to verify
        hashed: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return argon2.verify(password, hashed)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# JWT Token Management
def create_access_token(user_id: str, additional_claims: Optional[Dict] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        user_id: User ID to encode in token
        additional_claims: Optional additional claims to include
        
    Returns:
        JWT access token string
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """
    Create JWT refresh token.
    
    Args:
        user_id: User ID to encode in token
        
    Returns:
        JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict]:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def create_verification_token(email: str, expire_hours: int = 24) -> str:
    """
    Create email verification token.
    
    Args:
        email: Email address to verify
        expire_hours: Token expiration in hours
        
    Returns:
        Verification token string
    """
    expire = datetime.utcnow() + timedelta(hours=expire_hours)
    
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "email_verification"
    }
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )


def create_password_reset_token(email: str, expire_hours: int = 1) -> str:
    """
    Create password reset token.
    
    Args:
        email: Email address for password reset
        expire_hours: Token expiration in hours
        
    Returns:
        Password reset token string
    """
    expire = datetime.utcnow() + timedelta(hours=expire_hours)
    
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "password_reset"
    }
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
