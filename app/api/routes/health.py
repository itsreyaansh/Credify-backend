"""Health check routes."""
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.redis_client import get_redis
from motor.motor_asyncio import AsyncDatabase
from redis.asyncio import Redis
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok"}


@router.get("/status")
async def service_status(
    db: AsyncDatabase = Depends(lambda: get_db()),
) -> Dict[str, Any]:
    """
    Check status of all services.
    Returns: Database, Redis, Gemini API, Blockchain, and uptime status.
    """
    status_info = {
        "database": "error",
        "redis": "error",
        "gemini_api": "unavailable",
        "blockchain": "unavailable",
        "uptime_hours": 0.0,
    }

    # Check database
    try:
        admin_db = db.client.admin
        await admin_db.command("ping")
        status_info["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        status_info["database"] = "error"

    # Check Redis
    try:
        redis_client = get_redis()
        await redis_client.ping()
        status_info["redis"] = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        status_info["redis"] = "error"

    # Gemini API availability (assume available if configured)
    from app.core.config import get_settings
    settings = get_settings()
    if settings.GEMINI_API_KEY:
        status_info["gemini_api"] = "available"
    else:
        status_info["gemini_api"] = "unavailable"

    # Blockchain availability (assume available if configured)
    if settings.CONTRACT_ADDRESS and settings.WEB3_PRIVATE_KEY:
        status_info["blockchain"] = "available"
    else:
        status_info["blockchain"] = "unavailable"

    return status_info


@router.get("/ready")
async def readiness_check(
    db: AsyncDatabase = Depends(lambda: get_db()),
) -> Dict[str, bool]:
    """
    Readiness check for Kubernetes probes.
    Returns True if service is ready to accept requests.
    """
    try:
        # Verify database connection
        admin_db = db.client.admin
        await admin_db.command("ping")

        # Verify Redis connection
        try:
            redis_client = get_redis()
            await redis_client.ping()
        except Exception:
            # Redis is optional
            pass

        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {"ready": False}
