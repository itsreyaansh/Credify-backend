"""Custom exceptions for Credify application."""
from fastapi import HTTPException, status


class CredifyException(Exception):
    """Base exception for Credify."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationException(CredifyException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationException(CredifyException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ValidationException(CredifyException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class ResourceNotFoundException(CredifyException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str = "Resource"):
        message = f"{resource} not found"
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class DuplicateResourceException(CredifyException):
    """Raised when trying to create a duplicate resource."""

    def __init__(self, resource: str = "Resource"):
        message = f"{resource} already exists"
        super().__init__(message, status.HTTP_409_CONFLICT)


class RateLimitException(CredifyException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS)


class DatabaseException(CredifyException):
    """Raised when database operation fails."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExternalServiceException(CredifyException):
    """Raised when external service call fails."""

    def __init__(self, service: str = "External service"):
        message = f"{service} is temporarily unavailable"
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE)


class InvalidTokenException(AuthenticationException):
    """Raised when token is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message)


class FraudDetectionException(CredifyException):
    """Raised when fraud detection fails."""

    def __init__(self, message: str = "Fraud detection failed"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)
