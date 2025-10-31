"""Security tests for injection attacks prevention."""
import pytest
from fastapi.testclient import TestClient
from bson import ObjectId

from app.main import app


client = TestClient(app)


@pytest.mark.asyncio
@pytest.mark.security
async def test_no_nosql_injection():
    """Test NoSQL injection prevention."""
    # Attempt MongoDB injection
    injection_payload = {"$ne": ""}

    response = client.post(
        "/api/auth/login",
        json={
            "email": injection_payload,
            "password": injection_payload,
        },
    )

    # Should return 400 or 422, not bypass authentication
    assert response.status_code in [400, 422, 401]


@pytest.mark.asyncio
@pytest.mark.security
async def test_sql_injection_prevention():
    """Test SQL injection prevention (if any SQL is used)."""
    # MongoDB doesn't use SQL, but we test string injection
    injection_payload = "'; drop database credify; --"

    response = client.post(
        "/api/auth/signup",
        json={
            "email": injection_payload,
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
            "role": "student",
            "institution_id": str(ObjectId()),
        },
    )

    # Should validate email format
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
@pytest.mark.security
async def test_xss_prevention():
    """Test XSS prevention in responses."""
    xss_payload = "<script>alert('XSS')</script>"

    response = client.post(
        "/api/auth/signup",
        json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": xss_payload,
            "last_name": "User",
            "role": "student",
            "institution_id": str(ObjectId()),
        },
    )

    # Should either reject or safely encode
    if response.status_code == 201:
        data = response.json()
        # Should not contain unescaped script tags
        assert "<script>" not in str(data)


@pytest.mark.asyncio
@pytest.mark.security
async def test_path_traversal_prevention():
    """Test path traversal prevention."""
    # Attempt to access parent directories
    response = client.get("/api/certificates/../../../../etc/passwd")

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.security
async def test_command_injection_prevention():
    """Test command injection prevention."""
    # Attempt command injection
    injection_payload = "test@example.com; rm -rf /"

    response = client.post(
        "/api/auth/signup",
        json={
            "email": injection_payload,
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
            "role": "student",
            "institution_id": str(ObjectId()),
        },
    )

    # Should validate email format
    assert response.status_code in [400, 422]
