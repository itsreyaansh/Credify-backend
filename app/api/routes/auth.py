"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_db
from app.core.redis_client import get_redis, add_token_to_blacklist
from app.core.dependencies import get_current_user
from app.services.auth_service import AuthService
from app.models.user import UserCreate, UserLogin, TokenResponse
from motor.motor_asyncio import AsyncDatabase
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserCreate,
    db: AsyncDatabase = Depends(get_db),
):
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: Min 8 chars with uppercase, lowercase, digit, special char
    - **first_name**: 2-50 characters
    - **last_name**: 2-50 characters
    - **role**: student, issuer, verifier, or admin
    - **institution_id**: Valid MongoDB ObjectId of institution
    """
    try:
        auth_service = AuthService(db)
        result = await auth_service.register_user(user_data)
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            user_id=result["user_id"],
            role=result["role"],
        )
    except ValueError as e:
        logger.warning(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed",
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: AsyncDatabase = Depends(get_db),
):
    """
    Authenticate user and return JWT tokens.

    - **email**: User's email
    - **password**: User's password

    Returns:
    - **access_token**: JWT token for API requests (15 min expiry)
    - **refresh_token**: JWT token for refreshing access (7 days expiry)
    - **user_id**: User's MongoDB ObjectId
    - **role**: User's role
    """
    try:
        auth_service = AuthService(db)
        result = await auth_service.login_user(login_data)
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            user_id=result["user_id"],
            role=result["role"],
        )
    except ValueError as e:
        logger.warning(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post("/refresh")
async def refresh_token(
    current_user: dict = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
):
    """
    Refresh the access token using a refresh token.

    Returns a new access token with 15-minute expiry.
    """
    from app.core.security import create_access_token

    try:
        user_id = current_user.get("user_id")
        email = current_user.get("email")
        role = current_user.get("role")

        # Verify user still exists and is active
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        if not user or not user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Generate new access token
        access_token = create_access_token(
            {"sub": user_id, "email": email, "role": role}
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout user by adding token to blacklist.

    The token will be invalid for future requests.
    """
    try:
        token = current_user.get("token")
        redis = get_redis()

        # Add token to blacklist (30 days expiry)
        await add_token_to_blacklist(token, 30 * 24 * 60 * 60)

        logger.info(f"User logged out: {current_user.get('email')}")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )
