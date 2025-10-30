"""
Main FastAPI application entry point for Credify.

This module initializes and configures the FastAPI application with:
- Database connections (MongoDB and Redis)
- Middleware setup (CORS, error handling, logging)
- Route registration
- Startup/shutdown event handlers

The application follows async/await patterns for high performance.

Example:
    Run the application with:
    >>> python -m uvicorn app.main:app --reload

Environment Variables (see .env.example):
    - ENVIRONMENT: development, staging, or production
    - DEBUG: Enable debug mode (development only)
    - MONGODB_URL: MongoDB connection string
    - REDIS_URL: Redis connection string
    - JWT_SECRET: Secret key for JWT tokens
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys

from app.core.config import get_settings, validate_production_settings
from app.core.database import connect_db, disconnect_db
from app.core.redis_client import connect_redis, disconnect_redis
from app.core.exceptions import CredifyException
from app.api.middleware import setup_middleware
from app.api.routes import auth, certificates, verification, admin, health

# ==================== LOGGING CONFIGURATION ====================

# Configure logging with appropriate level based on environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Handles connection to MongoDB and Redis.
    """
    # Startup
    logger.info("Starting Credify application...")
    try:
        await connect_db()
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise

    try:
        await connect_redis()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        # Don't raise - Redis is optional for some operations
        logger.warning("Continuing without Redis")

    logger.info("Credify application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Credify application...")
    try:
        await disconnect_db()
        logger.info("Disconnected from MongoDB")
    except Exception as e:
        logger.error(f"Error disconnecting MongoDB: {str(e)}")

    try:
        await disconnect_redis()
        logger.info("Disconnected from Redis")
    except Exception as e:
        logger.error(f"Error disconnecting Redis: {str(e)}")

    logger.info("Credify application shut down successfully")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered fraud detection for academic certificates",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Setup middleware
setup_middleware(app)

# Include API routers
app.include_router(
    health.router,
    prefix=f"{settings.API_PREFIX}/health",
    tags=["Health"],
)

app.include_router(
    auth.router,
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["Authentication"],
)

app.include_router(
    certificates.router,
    prefix=f"{settings.API_PREFIX}/certificates",
    tags=["Certificates"],
)

app.include_router(
    verification.router,
    prefix=f"{settings.API_PREFIX}/verification",
    tags=["Verification"],
)

app.include_router(
    admin.router,
    prefix=f"{settings.API_PREFIX}/admin",
    tags=["Admin"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Credify API",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
