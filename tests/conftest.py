"""Pytest configuration and fixtures for Credify tests."""
import pytest
import asyncio
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncClient, AsyncDatabase
from typing import AsyncGenerator, Generator
import os
from dotenv import load_dotenv

# Load test environment variables
load_dotenv()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncDatabase, None]:
    """Create a test database connection."""
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncClient(mongo_url)
    db = client["credify_test"]

    # Clean up before test
    await client.drop_database("credify_test")

    yield db

    # Clean up after test
    await client.drop_database("credify_test")
    client.close()


@pytest.fixture
async def test_user(test_db: AsyncDatabase) -> dict:
    """Create a test user in the database."""
    from app.core.security import hash_password

    user_data = {
        "_id": ObjectId(),
        "email": "test@example.com",
        "password_hash": hash_password("SecurePass123!"),
        "first_name": "Test",
        "last_name": "User",
        "role": "student",
        "institution_id": ObjectId(),
        "is_active": True,
        "two_factor_enabled": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await test_db.users.insert_one(user_data)
    return user_data


@pytest.fixture
async def test_institution(test_db: AsyncDatabase) -> dict:
    """Create a test institution in the database."""
    institution_data = {
        "_id": ObjectId(),
        "name": "Test University",
        "code": "TU001",
        "email_domain": "testuniversity.edu",
        "location": {
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        "is_verified": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await test_db.institutions.insert_one(institution_data)
    return institution_data


@pytest.fixture
async def test_certificate(test_db: AsyncDatabase, test_user: dict, test_institution: dict) -> dict:
    """Create a test certificate in the database."""
    cert_data = {
        "_id": ObjectId(),
        "certificate_id": "CERT-2024-001",
        "student_id": test_user["_id"],
        "issuer_id": test_institution["_id"],
        "course_name": "Advanced Python Programming",
        "issue_date": datetime(2024, 1, 15),
        "expiry_date": datetime(2025, 1, 15),
        "certificate_hash": "abc123def456",
        "document_url": "https://example.com/cert.pdf",
        "metadata": {
            "grade": "A",
            "duration": "6 months",
            "course_code": "PYTH-401",
        },
        "is_verified": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await test_db.certificates.insert_one(cert_data)
    return cert_data


@pytest.fixture
async def sample_certificate_image() -> bytes:
    """Load sample certificate image for testing."""
    # This would load an actual test image in production
    # For now, return dummy bytes
    return b"fake_image_data_for_testing"


@pytest.fixture
async def sample_images() -> dict:
    """Return various sample test images."""
    return {
        "valid": b"valid_certificate_image",
        "edited": b"photoshopped_image",
        "no_exif": b"screenshot_no_exif",
        "fake": b"fake_certificate_image",
    }


@pytest.fixture
async def auth_service_fixture(test_db: AsyncDatabase):
    """Create an auth service instance with test database."""
    from app.services.auth_service import AuthService

    return AuthService(test_db)


@pytest.fixture
async def certificate_service_fixture(test_db: AsyncDatabase):
    """Create a certificate service instance with test database."""
    from app.services.certificate_service import CertificateService

    return CertificateService(test_db)


@pytest.fixture
async def verification_service_fixture(test_db: AsyncDatabase):
    """Create a verification service instance with test database."""
    from app.services.verification_service import VerificationService

    return VerificationService(test_db)


@pytest.fixture
def mock_gemini_response() -> dict:
    """Mock response from Gemini API."""
    return {
        "tampering_detected": False,
        "confidence": 0.95,
        "details": "Certificate appears authentic",
        "red_flags": [],
    }


@pytest.fixture
def mock_blockchain_response() -> dict:
    """Mock blockchain verification response."""
    return {
        "verified": True,
        "transaction_hash": "0x123abc",
        "timestamp": datetime.utcnow().isoformat(),
        "network": "mumbai_testnet",
    }


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "fraud: mark test as fraud detection test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
