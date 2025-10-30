"""
Authentication service with complete business logic.
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from ..core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    create_verification_token,
    create_password_reset_token
)
from ..models.user import UserCreate, UserResponse, TokenResponse

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service handling user registration, login, and token management."""
    
    @staticmethod
    async def register_user(
        user_data: UserCreate,
        db: AsyncIOMotorDatabase
    ) -> TokenResponse:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            db: Database instance
            
        Returns:
            TokenResponse with access token, refresh token, and user info
            
        Raises:
            HTTPException: 400 if email already exists
        """
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Create user document
        user_doc = {
            "email": user_data.email,
            "password_hash": password_hash,
            "full_name": user_data.full_name,
            "role": user_data.role.value,
            "institution_id": user_data.institution_id,
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert into database
        result = await db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        
        # Generate tokens
        user_id = str(result.inserted_id)
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        # Create user response
        user_response = UserResponse(
            _id=user_id,
            email=user_doc["email"],
            full_name=user_doc["full_name"],
            role=user_doc["role"],
            institution_id=user_doc.get("institution_id"),
            is_active=user_doc["is_active"],
            is_verified=user_doc["is_verified"],
            created_at=user_doc["created_at"]
        )
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_response
        )
    
    @staticmethod
    async def login_user(
        email: str,
        password: str,
        db: AsyncIOMotorDatabase
    ) -> TokenResponse:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email
            password: User password
            db: Database instance
            
        Returns:
            TokenResponse with tokens and user info
            
        Raises:
            HTTPException: 401 if credentials invalid or user not found
        """
        # Find user by email
        user = await db.users.find_one({"email": email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Generate tokens
        user_id = str(user["_id"])
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        # Create user response
        user_response = UserResponse(
            _id=user_id,
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            institution_id=user.get("institution_id"),
            avatar_url=user.get("avatar_url"),
            is_active=user.get("is_active", True),
            is_verified=user.get("is_verified", False),
            created_at=user["created_at"]
        )
        
        logger.info(f"User logged in successfully: {email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_response
        )
    
    @staticmethod
    async def refresh_access_token(
        refresh_token: str,
        db: AsyncIOMotorDatabase
    ) -> str:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            db: Database instance
            
        Returns:
            New access token
            
        Raises:
            HTTPException: 401 if token invalid or expired
        """
        # Decode refresh token
        payload = decode_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Verify user still exists and is active
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new access token
        new_access_token = create_access_token(user_id)
        
        logger.info(f"Access token refreshed for user: {user_id}")
        
        return new_access_token
    
    @staticmethod
    async def verify_email_token(
        verification_token: str,
        db: AsyncIOMotorDatabase
    ) -> bool:
        """
        Verify email using verification token.
        
        Args:
            verification_token: Email verification token
            db: Database instance
            
        Returns:
            True if verification successful
            
        Raises:
            HTTPException: 400 if token invalid or expired
        """
        # Decode token
        payload = decode_token(verification_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        # Check token type
        if payload.get("type") != "email_verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Get email from token
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token payload"
            )
        
        # Update user verification status
        result = await db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "is_verified": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found or already verified"
            )
        
        logger.info(f"Email verified successfully: {email}")
        
        return True
    
    @staticmethod
    async def send_password_reset_email(
        email: str,
        db: AsyncIOMotorDatabase
    ) -> bool:
        """
        Generate password reset token and send email.
        
        Args:
            email: User email
            db: Database instance
            
        Returns:
            True if email sent (always returns True to prevent email enumeration)
        """
        # Check if user exists
        user = await db.users.find_one({"email": email})
        if not user:
            # Don't reveal if email exists
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return True
        
        # Generate reset token
        reset_token = create_password_reset_token(email)
        
        # In production, send email via SendGrid here
        logger.info(f"Password reset token generated for: {email}")
        logger.debug(f"Reset token (dev mode): {reset_token}")
        
        return True
    
    @staticmethod
    async def reset_password(
        reset_token: str,
        new_password: str,
        db: AsyncIOMotorDatabase
    ) -> bool:
        """
        Reset user password using reset token.
        
        Args:
            reset_token: Password reset token
            new_password: New password
            db: Database instance
            
        Returns:
            True if password reset successful
            
        Raises:
            HTTPException: 400 if token invalid or expired
        """
        # Decode token
        payload = decode_token(reset_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Check token type
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Get email from token
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token payload"
            )
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update user password
        result = await db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "password_hash": password_hash,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )
        
        logger.info(f"Password reset successfully for: {email}")
        
        return True
