"""API middleware for CORS, rate limiting, and logging."""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import get_settings
from app.core.redis_client import increment_request_count
import logging
import time
import json

logger = logging.getLogger(__name__)


def add_cors_middleware(app):
    """Add CORS middleware to the application."""
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting based on IP address."""
        settings = get_settings()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Skip rate limiting for health checks
        if request.url.path in ["/api/health", "/api/health/status"]:
            return await call_next(request)

        try:
            # Check rate limit
            request_count = await increment_request_count(client_ip)

            if request_count > settings.RATE_LIMIT_PER_HOUR:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests"},
                )
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")

        response = await call_next(request)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""

    async def dispatch(self, request: Request, call_next):
        """Log request and response."""
        # Skip logging for certain paths
        if request.url.path.startswith("/api/docs"):
            return await call_next(request)

        request_start_time = time.time()
        request_body = ""

        # Log request
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                request_body = body.decode() if body else ""
                # Recreate the body for the actual handler
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive

            logger.info(
                f"Request: {request.method} {request.url.path} - "
                f"Client: {request.client.host if request.client else 'unknown'}"
            )
        except Exception as e:
            logger.error(f"Error logging request: {str(e)}")

        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )

        # Log response
        process_time = time.time() - request_start_time
        logger.info(
            f"Response: {response.status_code} for {request.method} "
            f"{request.url.path} - Time: {process_time:.3f}s"
        )

        # Add process time header
        response.headers["X-Process-Time"] = str(process_time)
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Error handling middleware."""

    async def dispatch(self, request: Request, call_next):
        """Handle errors gracefully."""
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )


def setup_middleware(app):
    """Setup all middleware."""
    # Order matters - add in reverse order of execution
    add_cors_middleware(app)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
