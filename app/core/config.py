"""Configuration settings for the Credify application."""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Credify"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # MongoDB
    MONGODB_URL: str = "mongodb://root:password@localhost:27017"
    MONGODB_DB: str = "credify"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str = "your-secret-key-min-32-chars-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # Security
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 65536
    PASSWORD_MIN_LENGTH: int = 8

    # API
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    API_PREFIX: str = "/api"

    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = 100

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT: int = 30

    # Blockchain - Polygon Mumbai
    POLYGON_RPC_URL: str = "https://rpc-mumbai.maticvigil.com"
    CONTRACT_ADDRESS: str = ""
    WEB3_PRIVATE_KEY: str = ""

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@credify.ai"
    SMTP_FROM_NAME: str = "Credify"

    # Payment (Razorpay)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # Storage
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    LOCAL_STORAGE_PATH: str = "./storage"
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"

    # Features
    ENABLE_2FA: bool = True
    ENABLE_BULK_UPLOAD: bool = True
    DEMO_MODE: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


def get_settings_dict() -> dict:
    """Get settings as dictionary."""
    settings = get_settings()
    return settings.model_dump()
