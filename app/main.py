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

    Manages application lifecycle:
    - Startup: Connect to MongoDB and Redis
    - Shutdown: Clean disconnect

    Args:
        app: FastAPI application instance

    Raises:
        Exception: If critical services fail to connect
    """
    # ==================== STARTUP ====================

    logger.info("=" * 60)
    logger.info("Starting Credify application...")
    logger.info(f"Environment: {get_settings().ENVIRONMENT}")
    logger.info(f"Debug Mode: {get_settings().DEBUG}")
    logger.info("=" * 60)

    settings = get_settings()

    # Validate production settings if needed
    if settings.ENVIRONMENT == "production":
        try:
            validate_production_settings()
            logger.info("✓ Production settings validated")
        except ValueError as e:
            logger.error(f"✗ Production settings validation failed: {str(e)}")
            raise

    # Connect to MongoDB
    try:
        await connect_db()
        logger.info("✓ Connected to MongoDB")
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        logger.error("  Make sure MongoDB is running and MONGODB_URL is correct")
        raise

    # Connect to Redis
    redis_available = False
    try:
        await connect_redis()
        logger.info("✓ Connected to Redis")
        redis_available = True
    except Exception as e:
        logger.warning(f"⚠ Failed to connect to Redis: {str(e)}")
        logger.warning("  Continuing without Redis (caching and rate limiting disabled)")

    logger.info("-" * 60)
    logger.info("Credify application started successfully")
    logger.info("-" * 60)

    yield

    # ==================== SHUTDOWN ====================

    logger.info("=" * 60)
    logger.info("Shutting down Credify application...")
    logger.info("=" * 60)

    # Disconnect from MongoDB
    try:
        await disconnect_db()
        logger.info("✓ Disconnected from MongoDB")
    except Exception as e:
        logger.error(f"✗ Error disconnecting MongoDB: {str(e)}")

    # Disconnect from Redis
    if redis_available:
        try:
            await disconnect_redis()
            logger.info("✓ Disconnected from Redis")
        except Exception as e:
            logger.error(f"✗ Error disconnecting Redis: {str(e)}")

    logger.info("-" * 60)
    logger.info("Credify application shut down successfully")
    logger.info("=" * 60)


# ==================== APPLICATION INITIALIZATION ====================

# Load settings once at startup
settings = get_settings()

# Create FastAPI application instance
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered fraud detection for academic certificates",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Hide docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

logger.info(f"✓ FastAPI application initialized")

# ==================== MIDDLEWARE SETUP ====================

# Setup middleware (CORS, error handling, logging)
try:
    setup_middleware(app)
    logger.info("✓ Middleware setup completed")
except Exception as e:
    logger.error(f"✗ Failed to setup middleware: {str(e)}")
    raise

# ==================== ROUTE REGISTRATION ====================

# Health check routes (should be first for monitoring)
app.include_router(
    health.router,
    prefix=f"{settings.API_PREFIX}/health",
    tags=["Health"],
)
logger.debug("✓ Health routes registered")

# Authentication routes
app.include_router(
    auth.router,
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["Authentication"],
)
logger.debug("✓ Authentication routes registered")

# Certificate routes
app.include_router(
    certificates.router,
    prefix=f"{settings.API_PREFIX}/certificates",
    tags=["Certificates"],
)
logger.debug("✓ Certificate routes registered")

# Verification routes (fraud detection)
app.include_router(
    verification.router,
    prefix=f"{settings.API_PREFIX}/verification",
    tags=["Verification"],
)
logger.debug("✓ Verification routes registered")

# Admin routes (requires admin role)
app.include_router(
    admin.router,
    prefix=f"{settings.API_PREFIX}/admin",
    tags=["Admin"],
)
logger.debug("✓ Admin routes registered")

logger.info("✓ All routes registered successfully")

# ==================== ERROR HANDLERS ====================


@app.exception_handler(CredifyException)
async def credify_exception_handler(request: Request, exc: CredifyException):
    """
    Handle custom Credify exceptions.

    Args:
        request: Request object
        exc: CredifyException instance

    Returns:
        JSONResponse with error details
    """
    logger.warning(f"Credify exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.__class__.__name__,
                "message": exc.message,
            }
        }
    )


# ==================== ENDPOINTS ====================


@app.get("/")
async def root():
    """
    Root endpoint - welcome message.

    Returns:
        dict: Welcome information and API endpoints

    Example:
        >>> GET http://localhost:8000/
        {
            "message": "Welcome to Credify API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/health"
        }
    """
    return {
        "message": "Welcome to Credify API",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "API Documentation available on production",
        "health": f"{settings.API_PREFIX}/health",
    }


# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    """
    Main execution block for running the application.

    Usage:
        # Development mode with auto-reload
        python -m uvicorn app.main:app --reload

        # Production mode with 4 workers
        python -m uvicorn app.main:app --workers 4

        # Or run this file directly
        python app/main.py
    """
    import uvicorn

    # Configure Uvicorn
    config = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": settings.DEBUG,
        "workers": 1 if settings.DEBUG else 4,
        "log_level": "debug" if settings.DEBUG else "info",
    }

    logger.info(f"Starting Uvicorn with config: {config}")

    uvicorn.run(**config)
