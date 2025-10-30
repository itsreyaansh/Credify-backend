"""Unit tests for certificate service."""
import pytest
from datetime import datetime, timedelta
from bson import ObjectId

from app.services.certificate_service import CertificateService
from app.models.certificate import CertificateCreate


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_certificate(certificate_service_fixture, test_user, test_institution):
    """Test creating a new certificate."""
    cert_service = certificate_service_fixture

    cert_data = CertificateCreate(
        certificate_id="CERT-2024-001",
        course_name="Advanced Python Programming",
        issue_date=datetime(2024, 1, 15),
        expiry_date=datetime(2025, 1, 15),
        course_code="PYTH-401",
        grade="A",
        duration="6 months",
    )

    result = await cert_service.create_certificate(
        cert_data,
        student_id=str(test_user["_id"]),
        issuer_id=str(test_institution["_id"]),
        document_url="https://example.com/cert.pdf",
    )

    assert result["_id"] is not None
    assert result["certificate_id"] == "CERT-2024-001"
    assert result["course_name"] == "Advanced Python Programming"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_certificate(certificate_service_fixture, test_certificate):
    """Test retrieving a certificate."""
    cert_service = certificate_service_fixture

    cert = await cert_service.get_certificate(str(test_certificate["_id"]))

    assert cert is not None
    assert cert["certificate_id"] == "CERT-2024-001"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_user_certificates(certificate_service_fixture, test_user, test_certificate):
    """Test getting all certificates for a user."""
    cert_service = certificate_service_fixture

    certs = await cert_service.get_user_certificates(str(test_user["_id"]))

    assert len(certs) > 0
    assert any(c["_id"] == test_certificate["_id"] for c in certs)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_certificate(certificate_service_fixture, test_certificate):
    """Test updating a certificate."""
    cert_service = certificate_service_fixture

    update_data = {
        "course_name": "Updated Course Name",
        "metadata": {"grade": "A+"},
    }

    result = await cert_service.update_certificate(
        str(test_certificate["_id"]), update_data
    )

    assert result["course_name"] == "Updated Course Name"
    assert result["metadata"]["grade"] == "A+"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_certificate_expiry_check(certificate_service_fixture, test_db):
    """Test certificate expiry check."""
    cert_service = certificate_service_fixture

    # Create an expired certificate
    expired_cert = {
        "_id": ObjectId(),
        "certificate_id": "EXPIRED-001",
        "issue_date": datetime.utcnow() - timedelta(days=400),
        "expiry_date": datetime.utcnow() - timedelta(days=30),
        "course_name": "Old Course",
        "metadata": {},
    }

    await test_db.certificates.insert_one(expired_cert)

    is_expired = await cert_service.is_certificate_expired(str(expired_cert["_id"]))

    assert is_expired is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_certificate_duplicate_check(certificate_service_fixture, test_certificate):
    """Test duplicate certificate detection."""
    cert_service = certificate_service_fixture

    is_duplicate = await cert_service.check_duplicate(
        test_certificate["certificate_id"],
        test_certificate["student_id"],
    )

    assert is_duplicate is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_certificate_hash(certificate_service_fixture, test_certificate):
    """Test certificate hash generation."""
    cert_service = certificate_service_fixture

    cert_hash = await cert_service.generate_certificate_hash(
        test_certificate["certificate_id"],
        test_certificate["student_id"],
    )

    assert cert_hash is not None
    assert len(cert_hash) > 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_certificate(certificate_service_fixture, test_db):
    """Test deleting a certificate."""
    cert_service = certificate_service_fixture

    # Create a certificate to delete
    cert_to_delete = {
        "_id": ObjectId(),
        "certificate_id": "DELETE-001",
        "course_name": "Course to Delete",
        "metadata": {},
    }

    await test_db.certificates.insert_one(cert_to_delete)

    result = await cert_service.delete_certificate(str(cert_to_delete["_id"]))

    assert result is True

    # Verify it's deleted
    deleted_cert = await test_db.certificates.find_one(
        {"_id": cert_to_delete["_id"]}
    )

    assert deleted_cert is None
