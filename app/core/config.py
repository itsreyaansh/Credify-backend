"""
Configuration settings for the Credify application.

This module loads and validates environment variables into a Settings object.
All configuration is centralized here for easy management and validation.

Environment variables can be set in .env file or via system environment.
For production, ensure all sensitive values are properly set.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
from functools import lru_cache
import os
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class defines all configuration parameters with default values.
    Validation is performed on initialization to catch configuration errors early.

    Example:
        >>> settings = get_settings()
        >>> print(settings.APP_NAME)
        'Credify'
    """

    # ==================== APPLICATION SETTINGS ====================
    APP_NAME: str = Field(default="Credify", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, or production"
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode (NEVER use in production)"
    )

    # ==================== DATABASE SETTINGS ====================
    MONGODB_URL: str = Field(
        default="mongodb://root:password@localhost:27017",
        description="MongoDB connection URL"
    )
    MONGODB_DB: str = Field(
        default="credify",
        description="MongoDB database name"
    )

    # ==================== CACHE SETTINGS ====================
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )

    # ==================== JWT AUTHENTICATION ====================
    JWT_SECRET: str = Field(
        default="your-secret-key-min-32-chars-change-in-production",
        description="Secret key for JWT signing (MUST be changed in production)"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm for signing"
    )
    JWT_ACCESS_EXPIRE_MINUTES: int = Field(
        default=15,
        description="Access token expiration time in minutes"
    )
    JWT_REFRESH_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )

    # ==================== SECURITY SETTINGS ====================
    ARGON2_TIME_COST: int = Field(
        default=2,
        description="Argon2 time cost parameter for password hashing"
    )
    ARGON2_MEMORY_COST: int = Field(
        default=65536,
        description="Argon2 memory cost parameter (in KB)"
    )
    PASSWORD_MIN_LENGTH: int = Field(
        default=8,
        description="Minimum password length requirement"
    )

    # ==================== API & CORS SETTINGS ====================
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="Allowed CORS origins"
    )
    API_PREFIX: str = Field(
        default="/api",
        description="API prefix for all routes"
    )

    # ==================== RATE LIMITING ====================
    RATE_LIMIT_PER_HOUR: int = Field(
        default=100,
        description="Rate limit: requests per hour per IP"
    )

    # ==================== AI & ML SERVICES ====================
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key for vision analysis"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model to use"
    )
    GEMINI_TIMEOUT: int = Field(
        default=30,
        description="Gemini API timeout in seconds"
    )

    # ==================== BLOCKCHAIN SETTINGS ====================
    POLYGON_RPC_URL: str = Field(
        default="https://rpc-mumbai.maticvigil.com",
        description="Polygon Mumbai RPC endpoint"
    )
    CONTRACT_ADDRESS: str = Field(
        default="",
        description="Smart contract address on Polygon Mumbai"
    )
    WEB3_PRIVATE_KEY: str = Field(
        default="",
        description="Private key for blockchain transactions"
    )

    # ==================== EMAIL SETTINGS ====================
    SMTP_HOST: str = Field(
        default="smtp.gmail.com",
        description="SMTP server host"
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port"
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP authentication username"
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP authentication password"
    )
    SMTP_FROM_EMAIL: str = Field(
        default="noreply@credify.ai",
        description="Email address to send from"
    )
    SMTP_FROM_NAME: str = Field(
        default="Credify",
        description="Display name for emails"
    )

    # ==================== PAYMENT SETTINGS ====================
    RAZORPAY_KEY_ID: str = Field(
        default="",
        description="Razorpay API key ID"
    )
    RAZORPAY_KEY_SECRET: str = Field(
        default="",
        description="Razorpay API secret"
    )

    # ==================== STORAGE SETTINGS ====================
    STORAGE_TYPE: str = Field(
        default="local",
        description="Storage type: 'local' or 's3'"
    )
    LOCAL_STORAGE_PATH: str = Field(
        default="./storage",
        description="Local storage directory path"
    )
    S3_BUCKET: str = Field(
        default="",
        description="AWS S3 bucket name"
    )
    S3_REGION: str = Field(
        default="us-east-1",
        description="AWS S3 region"
    )

    # ==================== FEATURE FLAGS ====================
    ENABLE_2FA: bool = Field(
        default=True,
        description="Enable two-factor authentication"
    )
    ENABLE_BULK_UPLOAD: bool = Field(
        default=True,
        description="Enable bulk certificate upload"
    )
    DEMO_MODE: bool = Field(
        default=False,
        description="Enable demo mode with sample data"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """
        Validate JWT secret is sufficiently long.

        Args:
            v: The JWT secret to validate

        Returns:
            The validated JWT secret

        Raises:
            ValueError: If secret is too short
        """
        if len(v) < 32:
            logger.warning("JWT_SECRET is less than 32 characters. This is not secure!")
            if not os.getenv("DEBUG"):
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """
        Validate environment is valid.

        Args:
            v: The environment value to validate

        Returns:
            The validated environment

        Raises:
            ValueError: If environment is invalid
        """
        valid_environments = {"development", "staging", "production"}
        if v not in valid_environments:
            raise ValueError(f"ENVIRONMENT must be one of {valid_environments}")
        return v

    @field_validator("PASSWORD_MIN_LENGTH")
    @classmethod
    def validate_password_min_length(cls, v: int) -> int:
        """
        Validate minimum password length.

        Args:
            v: The minimum password length

        Returns:
            The validated value

        Raises:
            ValueError: If too short
        """
        if v < 6:
            raise ValueError("PASSWORD_MIN_LENGTH must be at least 6")
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached).

    This function uses LRU caching to ensure settings are only loaded once.
    Subsequent calls return the cached instance.

    Returns:
        Settings: The application settings object

    Example:
        >>> settings = get_settings()
        >>> print(settings.APP_NAME)
        'Credify'
    """
    try:
        settings = Settings()
        logger.info(f"Settings loaded successfully for {settings.ENVIRONMENT} environment")
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}")
        raise


def get_settings_dict() -> dict:
    """
    Get settings as dictionary.

    Useful for debugging or passing settings to external services.
    Note: This will include all settings including sensitive ones.

    Returns:
        dict: Settings as dictionary

    WARNING:
        Do not log or expose the returned dictionary as it contains
        sensitive information like API keys and passwords.
    """
    try:
        settings = get_settings()
        return settings.model_dump()
    except Exception as e:
        logger.error(f"Failed to get settings dict: {str(e)}")
        raise


def validate_production_settings() -> bool:
    """
    Validate that critical production settings are configured.

    This function checks that all required production settings are properly set.
    Call this on application startup in production environment.

    Returns:
        bool: True if all settings are valid

    Raises:
        ValueError: If any required production settings are missing

    Example:
        >>> if settings.ENVIRONMENT == "production":
        ...     validate_production_settings()
    """
    settings = get_settings()

    if settings.ENVIRONMENT == "production":
        required_settings = {
            "JWT_SECRET": settings.JWT_SECRET,
            "GEMINI_API_KEY": settings.GEMINI_API_KEY,
            "SMTP_PASSWORD": settings.SMTP_PASSWORD,
            "CONTRACT_ADDRESS": settings.CONTRACT_ADDRESS,
        }

        missing = [key for key, value in required_settings.items() if not value]

        if missing:
            raise ValueError(
                f"Missing required production settings: {', '.join(missing)}"
            )

    return True
