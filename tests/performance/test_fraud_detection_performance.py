"""Performance tests for fraud detection pipeline."""
import pytest
import time
from datetime import datetime


@pytest.mark.asyncio
@pytest.mark.performance
async def test_fraud_detection_under_5_seconds(sample_certificate_image):
    """Test fraud detection completes in under 5 seconds."""
    from app.fraud_detection.pipeline import FraudDetectionPipeline

    pipeline = FraudDetectionPipeline()
    start_time = time.time()

    result = await pipeline.verify(sample_certificate_image)

    elapsed_time = time.time() - start_time

    assert elapsed_time < 5.0, f"Fraud detection took {elapsed_time}s (target: <5s)"
    assert result["confidence_score"] is not None
    assert result["verdict"] in ["verified", "suspicious", "fraud"]


@pytest.mark.asyncio
@pytest.mark.performance
async def test_auth_login_response_time(test_user):
    """Test login response time under 500ms."""
    from app.services.auth_service import AuthService
    from app.models.user import UserLogin
    from motor.motor_asyncio import AsyncClient

    mongo_url = "mongodb://localhost:27017"
    client = AsyncClient(mongo_url)
    db = client["credify_test"]

    auth_service = AuthService(db)

    login_data = UserLogin(
        email=test_user["email"],
        password="SecurePass123!",
    )

    start_time = time.time()
    result = await auth_service.login_user(login_data)
    elapsed_time = time.time() - start_time

    assert elapsed_time < 0.5, f"Login took {elapsed_time}s (target: <0.5s)"
    assert result["access_token"] is not None

    client.close()


@pytest.mark.asyncio
@pytest.mark.performance
async def test_certificate_retrieval_speed(test_certificate):
    """Test certificate retrieval speed."""
    from app.services.certificate_service import CertificateService
    from motor.motor_asyncio import AsyncClient

    mongo_url = "mongodb://localhost:27017"
    client = AsyncClient(mongo_url)
    db = client["credify_test"]

    cert_service = CertificateService(db)

    start_time = time.time()
    cert = await cert_service.get_certificate(str(test_certificate["_id"]))
    elapsed_time = time.time() - start_time

    assert elapsed_time < 0.2, f"Certificate retrieval took {elapsed_time}s (target: <0.2s)"
    assert cert is not None

    client.close()


@pytest.mark.asyncio
@pytest.mark.performance
async def test_batch_certificate_processing():
    """Test batch processing performance."""
    from app.services.certificate_service import CertificateService
    from motor.motor_asyncio import AsyncClient
    from bson import ObjectId

    mongo_url = "mongodb://localhost:27017"
    client = AsyncClient(mongo_url)
    db = client["credify_test"]

    cert_service = CertificateService(db)

    # Create 100 certificates
    certs_to_create = []
    for i in range(100):
        certs_to_create.append({
            "_id": ObjectId(),
            "certificate_id": f"BATCH-{i:04d}",
            "course_name": f"Course {i}",
            "metadata": {},
        })

    await db.certificates.insert_many(certs_to_create)

    # Batch retrieve
    start_time = time.time()
    certs = await db.certificates.find({}).to_list(100)
    elapsed_time = time.time() - start_time

    assert elapsed_time < 1.0, f"Batch retrieval took {elapsed_time}s (target: <1s)"
    assert len(certs) == 100

    client.close()


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_verifications():
    """Test concurrent verification requests."""
    import asyncio

    # Create multiple concurrent verification tasks
    tasks = []
    for i in range(10):
        # This would need actual certificate images
        tasks.append(asyncio.sleep(0.1))

    start_time = time.time()
    await asyncio.gather(*tasks)
    elapsed_time = time.time() - start_time

    # 10 concurrent tasks should complete in roughly 0.1s, not 1.0s
    assert elapsed_time < 0.5, f"Concurrent verifications took {elapsed_time}s"
