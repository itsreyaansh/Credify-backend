"""
Configuration management using environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "credify_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT Settings
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    
    # Blockchain (Polygon Mumbai)
    POLYGON_RPC_URL: str = "https://rpc-mumbai.maticvigil.com"
    POLYGON_PRIVATE_KEY: Optional[str] = None
    POLYGON_CONTRACT_ADDRESS: Optional[str] = None
    
    # Payment (Razorpay)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    
    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: str = "noreply@credify.ai"
    
    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "debug"
    CORS_ORIGINS: list = ["http://localhost:5173"]
    
    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = 100
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "./uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
