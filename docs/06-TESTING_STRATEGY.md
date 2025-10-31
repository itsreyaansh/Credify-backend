# Testing Strategy - Comprehensive Quality Assurance

## Overview

**Credify** uses a comprehensive testing pyramid approach:

```
        ▲
       ╱ ╲
      ╱   ╲  E2E Tests (10%)
     ╱     ╲ API Integration
    ╱───────╲
   ╱         ╲
  ╱           ╲ Integration Tests (30%)
 ╱             ╲ Database, Cache, APIs
╱───────────────╲
╱                 ╲ Unit Tests (60%)
╱                   ╲ Business Logic
╱─────────────────────╲
```

### Test Metrics

- **Coverage Target:** 80%+ code coverage
- **Fraud Detection Accuracy:** 94%+
- **API Response Time:** < 200ms (p95)
- **Zero Security Vulnerabilities:** 0 critical/high

---

## 1. Unit Tests

### Auth Service Tests

**Location:** `tests/unit/test_auth_service.py`

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.auth_service import AuthService
from app.core.security import verify_password
from sqlalchemy.ext.asyncio import AsyncSession

class TestAuthService:
    """Test authentication business logic."""

    @pytest.fixture
    async def auth_service(self):
        """Create auth service instance."""
        mock_db = Mock(spec=AsyncSession)
        mock_redis = Mock()
        return AuthService(mock_db, mock_redis)

    @pytest.mark.asyncio
    async def test_register_valid_user(self, auth_service):
        """Test successful user registration."""
        user_data = {
            "email": "user@example.com",
            "password": "SecurePass@123",
            "name": "John Doe",
            "organization_id": "org-uuid",
            "account_type": "university"
        }

        result = await auth_service.register_user(**user_data)

        assert result["user_id"] is not None
        assert result["access_token"] is not None
        assert result["refresh_token"] is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service):
        """Test registration with duplicate email."""
        # Mock database to return existing user
        auth_service.db.execute.return_value.scalar.return_value = Mock(email="user@example.com")

        with pytest.raises(ValueError, match="Email already registered"):
            await auth_service.register_user(
                email="user@example.com",
                password="SecurePass@123",
                name="John",
                organization_id="org-uuid",
                account_type="university"
            )

    @pytest.mark.asyncio
    async def test_login_valid_credentials(self, auth_service):
        """Test successful login."""
        mock_user = Mock()
        mock_user.password_hash = "$argon2id$v=19$m=65536..."
        mock_user.id = "user-uuid"
        mock_user.email = "user@example.com"

        auth_service.db.execute.return_value.scalar.return_value = mock_user

        with patch('app.core.security.verify_password', return_value=True):
            result = await auth_service.login("user@example.com", "SecurePass@123")

        assert result["access_token"] is not None
        assert result["user_id"] == "user-uuid"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, auth_service):
        """Test login with wrong password."""
        mock_user = Mock()
        auth_service.db.execute.return_value.scalar.return_value = mock_user

        with patch('app.core.security.verify_password', return_value=False):
            with pytest.raises(ValueError, match="Invalid credentials"):
                await auth_service.login("user@example.com", "WrongPassword")

    @pytest.mark.asyncio
    async def test_refresh_token_valid(self, auth_service):
        """Test token refresh."""
        with patch('app.core.security.decode_token', return_value={"sub": "user-uuid"}):
            result = await auth_service.refresh_token("valid-refresh-token")

        assert result["access_token"] is not None

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, auth_service):
        """Test refresh with expired token."""
        with patch('app.core.security.decode_token', side_effect=ValueError("Token expired")):
            with pytest.raises(ValueError):
                await auth_service.refresh_token("expired-token")

    def test_password_validation(self):
        """Test password strength validation."""
        from app.core.security import validate_password

        # Valid passwords
        assert validate_password("SecurePass@123") is True
        assert validate_password("Complex1$Pass") is True

        # Invalid passwords
        with pytest.raises(ValueError):
            validate_password("short")  # Too short

        with pytest.raises(ValueError):
            validate_password("nouppercase123")  # No uppercase

        with pytest.raises(ValueError):
            validate_password("NOLOWERCASE123")  # No lowercase

        with pytest.raises(ValueError):
            validate_password("NoDigits@Pass")  # No digits

        with pytest.raises(ValueError):
            validate_password("NoSpecial123")  # No special char
```

### Fraud Detection Tests

**Location:** `tests/unit/test_fraud_detection.py`

```python
import pytest
from app.fraud_detection.layers.layer_1_exif import EXIFAnalyzer
from app.fraud_detection.layers.layer_2_ela import ELAAnalyzer
from app.fraud_detection.pipeline import FraudDetectionPipeline
import os

class TestFraudDetection:
    """Test fraud detection layers."""

    @pytest.fixture
    def test_image_path(self):
        """Get path to test certificate image."""
        return "tests/fixtures/sample_certificate.jpg"

    def test_exif_analysis_complete(self, test_image_path):
        """Test EXIF analysis with complete metadata."""
        analyzer = EXIFAnalyzer(test_image_path)
        result = analyzer.analyze()

        assert result["score"] >= 0 and result["score"] <= 20
        assert "has_exif" in result
        assert "flags" in result

    def test_exif_analysis_no_metadata(self):
        """Test EXIF analysis with no metadata (screenshot)."""
        # Create test image without EXIF
        from PIL import Image
        img = Image.new('RGB', (640, 480), color='white')
        path = "/tmp/no_exif.jpg"
        img.save(path)

        analyzer = EXIFAnalyzer(path)
        result = analyzer.analyze()

        assert result["has_exif"] is False
        assert "missing_exif_data" in result["flags"]

        os.remove(path)

    def test_ela_analysis_authentic(self, test_image_path):
        """Test ELA analysis with authentic certificate."""
        analyzer = ELAAnalyzer(test_image_path)
        result = analyzer.analyze()

        assert result["score"] >= 0 and result["score"] <= 20
        assert "heatmap_base64" in result
        assert "cloning_detected" in result
        assert "splicing_detected" in result

    @pytest.mark.asyncio
    async def test_fraud_pipeline_authentic(self):
        """Test complete fraud detection pipeline with authentic cert."""
        pipeline = FraudDetectionPipeline(
            db=Mock(),
            redis=Mock(),
            image_path="tests/fixtures/authentic_cert.jpg",
            config={
                "GEMINI_API_KEY": "test-key",
                "POLYGON_RPC_URL": "http://localhost",
                "CONTRACT_ADDRESS": "0x..."
            }
        )

        result = await pipeline.run(ip_address="127.0.0.1")

        assert result["verdict"] == "verified"
        assert result["confidence_score"] >= 80
        assert "layer_details" in result

    @pytest.mark.asyncio
    async def test_fraud_pipeline_forged(self):
        """Test pipeline with obviously forged certificate."""
        # Create forged certificate (manipulated image)
        pipeline = FraudDetectionPipeline(
            db=Mock(),
            redis=Mock(),
            image_path="tests/fixtures/forged_cert.jpg",
            config={"GEMINI_API_KEY": "test-key", "POLYGON_RPC_URL": "http://localhost"}
        )

        result = await pipeline.run(ip_address="127.0.0.1")

        assert result["verdict"] == "fraud"
        assert result["confidence_score"] < 40

    @pytest.mark.asyncio
    async def test_fraud_pipeline_processing_time(self):
        """Test pipeline completes within time budget."""
        pipeline = FraudDetectionPipeline(
            db=Mock(),
            redis=Mock(),
            image_path="tests/fixtures/cert.jpg",
            config={}
        )

        import time
        start = time.time()
        result = await pipeline.run()
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert elapsed < 5000  # Must complete in under 5 seconds
```

---

## 2. Integration Tests

### Certificate API Tests

**Location:** `tests/integration/test_certificate_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db():
    """Create in-memory test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield

    await engine.dispose()

@pytest.fixture
def client(test_db):
    """Create test client."""
    return TestClient(app)

class TestCertificateAPI:
    """Test certificate endpoints."""

    def test_upload_certificate_success(self, client):
        """Test successful certificate upload."""
        with open("tests/fixtures/sample_cert.jpg", "rb") as f:
            response = client.post(
                "/api/v1/certificates/upload",
                files={"certificate_image": f},
                data={
                    "certificate_name": "Bachelor of Science",
                    "holder_name": "John Doe",
                    "issue_date": "2024-05-15"
                },
                headers={"Authorization": f"Bearer {valid_token}"}
            )

        assert response.status_code == 201
        assert "certificate_id" in response.json()["data"]

    def test_upload_certificate_invalid_format(self, client):
        """Test upload with invalid file format."""
        response = client.post(
            "/api/v1/certificates/upload",
            files={"certificate_image": ("test.txt", b"invalid", "text/plain")},
            headers={"Authorization": f"Bearer {valid_token}"}
        )

        assert response.status_code == 400
        assert response.json()["error"] == "FILE_INVALID_FORMAT"

    def test_upload_certificate_file_too_large(self, client):
        """Test upload with oversized file."""
        large_file = b"x" * (6 * 1024 * 1024)  # 6MB

        response = client.post(
            "/api/v1/certificates/upload",
            files={"certificate_image": ("large.jpg", large_file, "image/jpeg")},
            headers={"Authorization": f"Bearer {valid_token}"}
        )

        assert response.status_code == 413

    def test_list_certificates_paginated(self, client):
        """Test listing certificates with pagination."""
        response = client.get(
            "/api/v1/certificates?page=1&limit=10&role=issuer",
            headers={"Authorization": f"Bearer {valid_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "certificates" in data
        assert "total" in data
        assert "page" in data

    def test_verify_certificate_success(self, client):
        """Test successful certificate verification."""
        with open("tests/fixtures/authentic_cert.jpg", "rb") as f:
            response = client.post(
                "/api/v1/verification/verify",
                files={"certificate_image": f}
            )

        assert response.status_code in [200, 202]  # Could be immediate or async
        data = response.json()["data"]
        assert "verification_id" in data
        assert "verdict" in data
        assert "confidence_score" in data
```

---

## 3. Security Tests

### Authentication Security Tests

**Location:** `tests/security/test_auth_security.py`

```python
import pytest
from fastapi.testclient import TestClient

class TestAuthSecurity:
    """Test authentication security."""

    def test_sql_injection_protection(self, client):
        """Test SQL injection protection."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "' OR '1'='1",
                "password": "password"
            }
        )

        # Should not return user data
        assert response.status_code == 401

    def test_password_not_in_response(self, client):
        """Test password never returned in response."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@example.com",
                "password": "SecurePass@123"
            }
        )

        response_body = response.json()
        assert "password" not in str(response_body)
        assert "password_hash" not in str(response_body)

    def test_rate_limiting_login(self, client):
        """Test rate limiting on login endpoint."""
        # Attempt 10 failed logins
        for i in range(10):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "attacker@example.com",
                    "password": f"attempt{i}"
                }
            )

        # Should be rate limited
        assert response.status_code == 429

    def test_jwt_token_validation(self, client):
        """Test JWT token validation."""
        # Try with invalid token
        response = client.get(
            "/api/v1/certificates",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401

    def test_expired_token_rejection(self, client):
        """Test expired tokens are rejected."""
        # Create expired token
        import jwt
        from datetime import datetime, timedelta

        payload = {
            "sub": "user-id",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt.encode(payload, "secret", algorithm="HS256")

        response = client.get(
            "/api/v1/certificates",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
```

---

## 4. Performance Tests

### Load Testing

**Location:** `tests/performance/load_test.py`

```python
from locust import HttpUser, task, between
import random

class CredifyUser(HttpUser):
    """Simulate Credify user behavior."""

    wait_time = between(1, 3)

    def on_start(self):
        """Login before tests."""
        self.token = self._login()

    def _login(self):
        """Login and get token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": f"user{random.randint(1, 100)}@example.com",
                "password": "Password@123"
            }
        )
        return response.json()["data"]["access_token"]

    @task(3)
    def list_certificates(self):
        """List user's certificates."""
        self.client.get(
            "/api/v1/certificates?page=1&limit=10",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(2)
    def verify_certificate(self):
        """Verify a certificate."""
        with open("tests/fixtures/cert.jpg", "rb") as f:
            self.client.post(
                "/api/v1/verification/verify",
                files={"certificate_image": f}
            )

    @task(1)
    def upload_certificate(self):
        """Upload new certificate."""
        with open("tests/fixtures/cert.jpg", "rb") as f:
            self.client.post(
                "/api/v1/certificates/upload",
                files={"certificate_image": f},
                data={
                    "certificate_name": "Test",
                    "holder_name": "Test User",
                    "issue_date": "2024-05-15"
                },
                headers={"Authorization": f"Bearer {self.token}"}
            )

# Run with: locust -f load_test.py --users 500 --spawn-rate 50 -H http://localhost:8000
```

---

## 5. Fraud Accuracy Tests

### Fraud Detection Accuracy

**Location:** `tests/fraud/test_fraud_accuracy.py`

```python
import pytest
from app.fraud_detection.pipeline import FraudDetectionPipeline

class TestFraudAccuracy:
    """Test fraud detection accuracy across different scenarios."""

    @pytest.mark.parametrize("cert_path,expected_verdict,min_score", [
        ("tests/fixtures/authentic_cert_1.jpg", "verified", 80),
        ("tests/fixtures/authentic_cert_2.jpg", "verified", 80),
        ("tests/fixtures/forged_cert_1.jpg", "fraud", 40),
        ("tests/fixtures/forged_cert_2.jpg", "fraud", 40),
        ("tests/fixtures/suspicious_cert_1.jpg", "suspicious", 40),
        ("tests/fixtures/suspicious_cert_2.jpg", "suspicious", 80),
    ])
    @pytest.mark.asyncio
    async def test_fraud_detection_accuracy(self, cert_path, expected_verdict, min_score, max_score=None):
        """Test fraud detection on various certificates."""
        pipeline = FraudDetectionPipeline(
            db=Mock(),
            redis=Mock(),
            image_path=cert_path,
            config={}
        )

        result = await pipeline.run()

        if expected_verdict == "verified":
            assert result["verdict"] == "verified"
            assert result["confidence_score"] >= min_score
        elif expected_verdict == "fraud":
            assert result["verdict"] == "fraud"
            assert result["confidence_score"] < min_score
        else:
            assert result["verdict"] == "suspicious"
            assert min_score <= result["confidence_score"] < max_score or max_score is None
```

---

## Running Tests

### All Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth_service.py -v

# Run with markers
pytest tests/ -m "not slow" -v

# Run in parallel
pytest tests/ -n auto
```

### Test Configuration

**Location:** `pytest.ini`

```ini
[pytest]
minversion = 7.0
addopts = --strict-markers -ra --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    security: Security tests
    performance: Performance tests
    fraud: Fraud detection tests
    slow: Slow tests
```

---

## Test Fixtures

**Location:** `tests/conftest.py`

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db():
    """Test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
def mock_redis(mocker):
    """Mock Redis client."""
    return mocker.MagicMock()

@pytest.fixture
def mock_gemini(mocker):
    """Mock Gemini API."""
    return mocker.patch("anthropic.Anthropic")

@pytest.fixture
def valid_token():
    """Generate valid JWT token."""
    from app.core.security import create_tokens
    tokens = create_tokens({"sub": "test-user-id"})
    return tokens["access_token"]
```

---

## Related Documentation

- [04-FRAUD_DETECTION_GUIDE.md](04-FRAUD_DETECTION_GUIDE.md) - Fraud detection details
- [07-SECURITY_HARDENING.md](07-SECURITY_HARDENING.md) - Security practices

---

**Last Updated:** 2024-10-31
**Version:** 1.0
**Status:** Production Ready
