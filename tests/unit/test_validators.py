"""Unit tests for validators."""
import pytest
from bson import ObjectId

from app.utils.helpers import (
    validate_email,
    validate_password,
    validate_mongodb_id,
)


@pytest.mark.unit
def test_validate_email_valid():
    """Test valid email validation."""
    assert validate_email("test@example.com") is True
    assert validate_email("user.name+tag@example.co.uk") is True


@pytest.mark.unit
def test_validate_email_invalid():
    """Test invalid email validation."""
    assert validate_email("invalid-email") is False
    assert validate_email("test@") is False
    assert validate_email("@example.com") is False
    assert validate_email("") is False


@pytest.mark.unit
def test_validate_password_strong():
    """Test strong password validation."""
    result = validate_password("SecurePass123!")
    assert result["valid"] is True
    assert len(result["errors"]) == 0


@pytest.mark.unit
def test_validate_password_weak():
    """Test weak password validation."""
    # Too short
    result = validate_password("pass")
    assert result["valid"] is False
    assert len(result["errors"]) > 0

    # No uppercase
    result = validate_password("password123!")
    assert result["valid"] is False

    # No numbers
    result = validate_password("PasswordABC!")
    assert result["valid"] is False

    # No special characters
    result = validate_password("Password123")
    assert result["valid"] is False


@pytest.mark.unit
def test_validate_mongodb_id():
    """Test MongoDB ID validation."""
    valid_id = str(ObjectId())
    assert validate_mongodb_id(valid_id) is True

    assert validate_mongodb_id("invalid-id") is False
    assert validate_mongodb_id("") is False


@pytest.mark.unit
def test_validate_email_with_normalization():
    """Test email normalization during validation."""
    # Email should be case-insensitive
    email1 = "Test@Example.com"
    email2 = "test@example.com"

    assert validate_email(email1) is True
    assert validate_email(email2) is True
