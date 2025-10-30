"""
FastAPI dependency injection helpers.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from typing import Optional, Dict
from bson import ObjectId
from .database import get_database
from .redis_client import get_redis
from .security import decode_token
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_db() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return get_database()


async def get_redis_client() -> Redis:
    """Dependency to get Redis instance."""
    return get_redis()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Authorization credentials
        db: Database instance
        
    Returns:
        User document
        
    Raises:
        HTTPException: 401 if token invalid or user not found
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception as e:
        logger.error(f"Database error fetching user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Optional[Dict]:
    """
    Get current user if authenticated, None otherwise.
    For public endpoints that optionally use auth.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency factory to require specific user role.
    
    Args:
        required_role: Role required (admin, issuer, verifier, student)
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: Dict = Depends(get_current_user)) -> Dict:
        user_role = current_user.get("role")
        
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. {required_role} role required."
            )
        
        return current_user
    
    return role_checker


async def get_admin_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Get current user and verify admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_issuer_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Get current user and verify issuer role."""
    if current_user.get("role") != "issuer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Issuer access required"
        )
    return current_user


async def get_verifier_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Get current user and verify verifier role."""
    if current_user.get("role") != "verifier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verifier access required"
        )
    return current_user
