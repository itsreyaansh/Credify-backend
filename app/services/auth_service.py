"""Authentication service for user management."""
from motor.motor_asyncio import AsyncDatabase
from datetime import datetime
from bson import ObjectId
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
)
from app.models.user import UserCreate, UserLogin
from typing import Optional, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncDatabase):
        """Initialize auth service with database connection."""
        self.db = db
        self.users_col = db["users"]

    async def register_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """
        Register a new user.

        Args:
            user_data: User creation data

        Returns:
            Dictionary with user_id, access_token, refresh_token

        Raises:
            ValueError: If email exists or validation fails
        """
        # Check if email already exists
        existing_user = await self.users_col.find_one({"email": user_data.email})
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")

        # Validate password strength
        is_valid, message = validate_password_strength(user_data.password)
        if not is_valid:
            raise ValueError(f"Password validation failed: {message}")

        # Verify institution exists
        institutions_col = self.db["institutions"]
        try:
            institution_id = ObjectId(user_data.institution_id)
        except Exception:
            raise ValueError("Invalid institution ID format")

        institution = await institutions_col.find_one({"_id": institution_id})
        if not institution:
            raise ValueError("Institution not found")

        # Hash password
        password_hash = hash_password(user_data.password)

        # Create user document
        user_doc = {
            "_id": ObjectId(),
            "email": user_data.email,
            "password_hash": password_hash,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "role": user_data.role,
            "institution_id": institution_id,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "two_factor_enabled": False,
        }

        # Insert user
        result = await self.users_col.insert_one(user_doc)
        user_id = str(result.inserted_id)

        # Generate tokens
        access_token = create_access_token({"sub": user_id, "email": user_data.email, "role": user_data.role})
        refresh_token = create_refresh_token({"sub": user_id, "email": user_data.email})

        logger.info(f"User registered successfully: {user_data.email}")

        return {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": user_data.role,
        }

    async def login_user(self, login_data: UserLogin) -> Dict[str, Any]:
        """
        Authenticate user and return tokens.

        Args:
            login_data: Login credentials

        Returns:
            Dictionary with access_token, refresh_token, user_id, role

        Raises:
            ValueError: If credentials are invalid
        """
        # Find user by email
        user = await self.users_col.find_one({"email": login_data.email})
        if not user:
            raise ValueError("Invalid email or password")

        # Check if user is active
        if not user.get("is_active"):
            raise ValueError("User account is inactive")

        # Verify password
        if not verify_password(login_data.password, user.get("password_hash", "")):
            raise ValueError("Invalid email or password")

        # Update last login
        user_id = str(user["_id"])
        await self.users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )

        # Get institution name
        institutions_col = self.db["institutions"]
        institution = await institutions_col.find_one({"_id": user.get("institution_id")})
        institution_name = institution.get("name") if institution else None

        # Generate tokens
        access_token = create_access_token(
            {
                "sub": user_id,
                "email": user["email"],
                "role": user.get("role", "student"),
            }
        )
        refresh_token = create_refresh_token(
            {
                "sub": user_id,
                "email": user["email"],
            }
        )

        logger.info(f"User logged in: {login_data.email}")

        return {
            "user_id": user_id,
            "email": user["email"],
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": user.get("role", "student"),
            "institution_name": institution_name,
        }

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            user_obj_id = ObjectId(user_id)
            user = await self.users_col.find_one({"_id": user_obj_id})
            if user:
                user["id"] = str(user.pop("_id"))
            return user
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            user = await self.users_col.find_one({"email": email})
            if user:
                user["id"] = str(user.pop("_id"))
            return user
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user data."""
        try:
            user_obj_id = ObjectId(user_id)
            result = await self.users_col.update_one(
                {"_id": user_obj_id},
                {
                    "$set": {
                        **update_data,
                        "updated_at": datetime.utcnow(),
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return False

    async def disable_user(self, user_id: str, reason: str = "") -> bool:
        """Disable a user account."""
        try:
            user_obj_id = ObjectId(user_id)
            result = await self.users_col.update_one(
                {"_id": user_obj_id},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow(),
                    }
                }
            )
            logger.info(f"User disabled: {user_id} - Reason: {reason}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error disabling user: {str(e)}")
            return False

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """Change user password."""
        try:
            # Get user
            user = await self.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            # Verify old password
            if not verify_password(old_password, user.get("password_hash", "")):
                raise ValueError("Current password is incorrect")

            # Validate new password
            is_valid, message = validate_password_strength(new_password)
            if not is_valid:
                raise ValueError(f"Password validation failed: {message}")

            # Hash and update new password
            new_password_hash = hash_password(new_password)
            user_obj_id = ObjectId(user_id)

            result = await self.users_col.update_one(
                {"_id": user_obj_id},
                {
                    "$set": {
                        "password_hash": new_password_hash,
                        "updated_at": datetime.utcnow(),
                    }
                }
            )

            logger.info(f"Password changed for user: {user_id}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            raise
