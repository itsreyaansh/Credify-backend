"""Integration tests for certificate endpoints."""
import pytest
from fastapi.testclient import TestClient
from bson import ObjectId

from app.main import app


client = TestClient(app)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_certificates_endpoint(test_user, test_certificate):
    """Test getting user's certificates."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    access_token = login_response.json()["access_token"]

    # Get certificates
    response = client.get(
        "/api/certificates",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert "certificates" in response.json()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_certificate_endpoint(test_user, test_certificate):
    """Test getting a specific certificate."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    access_token = login_response.json()["access_token"]

    # Get certificate
    response = client.get(
        f"/api/certificates/{str(test_certificate['_id'])}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["_id"] is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_upload_certificate_endpoint(test_user, sample_certificate_image):
    """Test uploading a certificate."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    access_token = login_response.json()["access_token"]

    # Upload certificate
    files = {"file": ("certificate.pdf", sample_certificate_image, "application/pdf")}

    response = client.post(
        "/api/certificates/upload",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code in [200, 201]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_certificate_endpoint(test_user, test_certificate):
    """Test updating a certificate."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    access_token = login_response.json()["access_token"]

    # Update certificate
    response = client.put(
        f"/api/certificates/{str(test_certificate['_id'])}",
        json={"course_name": "Updated Course Name"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["course_name"] == "Updated Course Name"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_certificate_endpoint(test_user, test_certificate):
    """Test deleting a certificate."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user["email"],
            "password": "SecurePass123!",
        },
    )

    access_token = login_response.json()["access_token"]

    # Delete certificate
    response = client.delete(
        f"/api/certificates/{str(test_certificate['_id'])}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code in [200, 204]
