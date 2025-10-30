"""Admin dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from app.core.database import get_db
from app.core.dependencies import get_current_admin
from motor.motor_asyncio import AsyncDatabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fraud-feed")
async def get_fraud_feed(
    limit: int = 50,
    current_user: dict = Depends(get_current_admin),
    db: AsyncDatabase = Depends(get_db),
):
    """Get recent fraud incidents."""
    return {"incidents": [], "total": 0}


@router.get("/analytics")
async def get_analytics(
    start_date: str = None,
    end_date: str = None,
    current_user: dict = Depends(get_current_admin),
    db: AsyncDatabase = Depends(get_db),
):
    """Get analytics dashboard data."""
    return {
        "total_verifications": 0,
        "verified_count": 0,
        "suspicious_count": 0,
        "fraud_count": 0,
        "average_confidence_score": 0,
    }


@router.get("/review-queue")
async def get_manual_review_queue(
    confidence_min: int = 40,
    confidence_max: int = 80,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_admin),
    db: AsyncDatabase = Depends(get_db),
):
    """Get manual review queue (suspicious verifications)."""
    return {"reviews": [], "total": 0, "page": page, "limit": limit}


@router.get("/users")
async def list_users(
    role: str = None,
    page: int = 1,
    limit: int = 10,
    current_user: dict = Depends(get_current_admin),
    db: AsyncDatabase = Depends(get_db),
):
    """List platform users."""
    return {"users": [], "total": 0, "page": page, "limit": limit}


@router.patch("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    reason: str = None,
    current_user: dict = Depends(get_current_admin),
    db: AsyncDatabase = Depends(get_db),
):
    """Disable a user account."""
    return {"message": f"User {user_id} disabled"}


@router.websocket("/fraud-stream")
async def fraud_stream(
    websocket: WebSocket,
    current_user: dict = Depends(get_current_admin),
):
    """
    WebSocket endpoint for real-time fraud detection feed.
    Admin receives live updates when fraud is detected.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # Handle messages from admin
            await websocket.send_json({
                "event": "connected",
                "message": "Connected to fraud feed"
            })
    except Exception as e:
        logger.error(f"Fraud stream error: {str(e)}")
    finally:
        await websocket.close()
