"""FastAPI dependencies for authentication and authorization."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from app.core.security import get_token_from_header, decode_token
from app.core.redis_client import is_token_blacklisted
from app.core.database import get_db
from motor.motor_asyncio import AsyncDatabase
from typing import Optional, Dict, Any
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.
    Raises HTTPException if token is invalid or blacklisted.
    """
    token = credentials.credentials

    # Check if token is blacklisted
    if await is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    token_type = payload.get("type", "access")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role"),
        "token": token,
    }


async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get current user and verify they have admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_current_issuer(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get current user and verify they have issuer role."""
    role = current_user.get("role")
    if role not in ["issuer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Issuer access required",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, otherwise return None.
    Used for endpoints that support both authenticated and unauthenticated access.
    """
    if not credentials:
        return None

    token = credentials.credentials

    # Check if token is blacklisted
    if await is_token_blacklisted(token):
        return None

    # Decode token
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role"),
        "token": token,
    }


async def verify_user_exists(
    user_id: str,
    db: AsyncDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Verify that a user exists in the database."""
    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    users_col = db["users"]
    user = await users_col.find_one({"_id": user_obj_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_db_dependency() -> AsyncDatabase:
    """Get database connection for dependency injection."""
    return get_db()


class RateLimitDependency:
    """Rate limiting dependency."""

    async def __call__(
        self,
        request,
    ) -> None:
        """Check rate limit (implementation in middleware)."""
        pass  # Rate limiting is handled in middleware
