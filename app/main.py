"""
Credify FastAPI Application - Main Entry Point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import time
import uuid

from .core.config import settings
from .core.database import connect_to_mongo, close_mongo_connection
from .core.redis_client import connect_to_redis, close_redis_connection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Credify Backend API...")
    try:
        await connect_to_mongo()
        await connect_to_redis()
        logger.info("All services connected successfully")
    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Credify Backend API...")
    await close_mongo_connection()
    await close_redis_connection()
    logger.info("All services shut down successfully")


# Create FastAPI app
app = FastAPI(
    title="Credify API",
    description="AI-Powered Certificate Verification System with 6-Layer Fraud Detection",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID and Process Time Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add custom headers for request tracking and performance monitoring."""
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Track process time
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate process time
    process_time = time.time() - start_time
    
    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.4f}s | "
        f"ID: {request_id}"
    )
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled exception | Request ID: {request_id} | Error: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns system status and timestamp.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Credify API",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Credify API - AI-Powered Certificate Verification",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Import and include routers (will be added as routes are created)
# from .api.routes import auth, certificates, verification, admin, health
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(certificates.router, prefix="/api/certificates", tags=["Certificates"])
# app.include_router(verification.router, prefix="/api/verification", tags=["Verification"])
# app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
