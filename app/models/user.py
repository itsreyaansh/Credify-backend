"""User model and schemas."""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Literal
from bson import ObjectId


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    role: Literal["student", "issuer", "verifier", "admin"] = "student"


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8)
    institution_id: str


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """User update schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    two_factor_enabled: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema."""
    id: str = Field(alias="_id")
    is_active: bool
    two_factor_enabled: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            ObjectId: str,
        }


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    institution_name: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# MongoDB document template
USER_TEMPLATE = {
    "_id": ObjectId,  # ObjectId
    "email": str,  # Unique
    "password_hash": str,  # Argon2id
    "first_name": str,
    "last_name": str,
    "role": str,  # "student", "issuer", "verifier", "admin"
    "institution_id": ObjectId,  # Reference to Institution
    "is_active": bool,
    "created_at": datetime,
    "updated_at": datetime,
    "last_login": Optional[datetime],
    "two_factor_enabled": bool,
}
