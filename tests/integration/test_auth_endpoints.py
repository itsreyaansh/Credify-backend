"""Integration tests for authentication endpoints."""
import pytest
from fastapi.testclient import TestClient
from bson import ObjectId

from app.main import app
from app.core.security import hash_password


client = TestClient(app)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_signup_endpoint(test_db):
    """Test signup endpoint."""
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "newuser@test.com",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
            "role": "student",
            "institution_id": str(ObjectId()),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "newuser@test.com"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_signup_duplicate_email(test_db, test_user):
    """Test signup with duplicate email."""
    response = client.post(
        "/api/auth/signup",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
            "role": "student",
            "institution_id": str(ObjectId()),
        },
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_login_endpoint(test_user):
    """Test login endpoint."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@test.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_profile_endpoint(test_user):
    """Test getting user profile."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    access_token = login_response.json()["access_token"]

    # Get profile
    response = client.get(
        "/api/auth/profile",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == test_user["email"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_profile_endpoint(test_user):
    """Test updating user profile."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    access_token = login_response.json()["access_token"]

    # Update profile
    response = client.put(
        "/api/auth/profile",
        json={
            "first_name": "Updated",
            "last_name": "Name",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_refresh_token_endpoint(test_user):
    """Test token refresh endpoint."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_logout_endpoint(test_user):
    """Test logout endpoint."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    access_token = login_response.json()["access_token"]

    # Logout
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unauthorized_access():
    """Test accessing protected endpoint without token."""
    response = client.get("/api/auth/profile")

    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalid_token():
    """Test accessing protected endpoint with invalid token."""
    response = client.get(
        "/api/auth/profile",
        headers={"Authorization": "Bearer invalid.token.here"},
    )

    assert response.status_code == 401
