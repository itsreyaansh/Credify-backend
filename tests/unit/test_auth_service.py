"""Unit tests for authentication service."""
import pytest
from datetime import datetime
from bson import ObjectId
from pydantic import ValidationError

from app.services.auth_service import AuthService
from app.core.security import verify_password, hash_password
from app.models.user import UserCreate, UserLogin


@pytest.mark.asyncio
@pytest.mark.unit
async def test_register_user_success(auth_service_fixture):
    """Test successful user registration."""
    auth_service = auth_service_fixture

    user_data = UserCreate(
        email="newuser@example.com",
        password="SecurePass123!",
        first_name="John",
        last_name="Doe",
        role="student",
        institution_id=str(ObjectId()),
    )

    result = await auth_service.register_user(user_data)

    assert result["user_id"] is not None
    assert result["access_token"] is not None
    assert result["refresh_token"] is not None
    assert result["user"]["email"] == "newuser@example.com"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_register_user_duplicate_email(auth_service_fixture, test_user):
    """Test registration with duplicate email fails."""
    auth_service = auth_service_fixture

    user_data = UserCreate(
        email=test_user["email"],
        password="SecurePass123!",
        first_name="John",
        last_name="Doe",
        role="student",
        institution_id=str(ObjectId()),
    )

    with pytest.raises(ValueError, match="Email already exists"):
        await auth_service.register_user(user_data)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_user_success(auth_service_fixture, test_user):
    """Test successful login."""
    auth_service = auth_service_fixture

    login_data = UserLogin(
        email=test_user["email"],
        password="SecurePass123!",
    )

    result = await auth_service.login_user(login_data)

    assert result["user_id"] is not None
    assert result["access_token"] is not None
    assert result["refresh_token"] is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_user_wrong_password(auth_service_fixture, test_user):
    """Test login with wrong password fails."""
    auth_service = auth_service_fixture

    login_data = UserLogin(
        email=test_user["email"],
        password="WrongPassword123!",
    )

    with pytest.raises(ValueError, match="Invalid credentials"):
        await auth_service.login_user(login_data)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_user_nonexistent(auth_service_fixture):
    """Test login with non-existent user fails."""
    auth_service = auth_service_fixture

    login_data = UserLogin(
        email="nonexistent@example.com",
        password="SecurePass123!",
    )

    with pytest.raises(ValueError, match="Invalid credentials"):
        await auth_service.login_user(login_data)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_verify_password():
    """Test password verification."""
    password = "SecurePass123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_refresh_token(auth_service_fixture, test_user):
    """Test token refresh."""
    auth_service = auth_service_fixture

    # First login to get refresh token
    login_data = UserLogin(
        email=test_user["email"],
        password="SecurePass123!",
    )
    result = await auth_service.login_user(login_data)
    refresh_token = result["refresh_token"]

    # Refresh the token
    new_tokens = await auth_service.refresh_token(refresh_token)

    assert new_tokens["access_token"] is not None
    assert new_tokens["refresh_token"] is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_invalid_email_registration():
    """Test registration with invalid email."""
    user_data = UserCreate(
        email="invalid-email",
        password="SecurePass123!",
        first_name="John",
        last_name="Doe",
        role="student",
        institution_id=str(ObjectId()),
    )

    with pytest.raises(ValidationError):
        user_data.validate()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_weak_password_registration():
    """Test registration with weak password."""
    user_data = UserCreate(
        email="test@example.com",
        password="weak",  # Too short
        first_name="John",
        last_name="Doe",
        role="student",
        institution_id=str(ObjectId()),
    )

    with pytest.raises(ValidationError):
        user_data.validate()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_current_user(auth_service_fixture, test_user):
    """Test getting current user."""
    auth_service = auth_service_fixture

    user = await auth_service.get_user(str(test_user["_id"]))

    assert user is not None
    assert user["email"] == test_user["email"]
    assert user["_id"] == test_user["_id"]
