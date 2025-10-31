"""Verification model and schemas."""
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, Literal, Dict, Any
from bson import ObjectId


class FraudLayerResult(BaseModel):
    """Fraud layer result schema."""
    exif_score: float = Field(..., ge=0, le=20)
    ela_score: float = Field(..., ge=0, le=20)
    gemini_score: float = Field(..., ge=0, le=20)
    database_score: float = Field(..., ge=0, le=20)
    blockchain_score: float = Field(..., ge=0, le=10)
    geo_fraud_score: float = Field(..., ge=0, le=10)
    breakdown: Dict[str, Any] = {}


class VerificationRequest(BaseModel):
    """Verification request schema."""
    certificate_id: Optional[str] = None  # Either this or certificate_image
    verifier_email: Optional[EmailStr] = None


class VerificationResponse(BaseModel):
    """Verification response schema."""
    verification_id: str
    certificate_id: Optional[str] = None
    status: Literal["processing", "complete"]
    confidence_score: float = Field(..., ge=0, le=100)
    verdict: Literal["verified", "suspicious", "fraud"]
    fraud_layers_result: Optional[FraudLayerResult] = None
    report_url: Optional[str] = None
    processing_time_ms: int = 0
    layer_details: Dict[str, Any] = {}
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat() if v else None,
        }


class VerificationHistoryResponse(BaseModel):
    """Verification history response schema."""
    verifications: list[VerificationResponse]
    total: int
    page: int
    limit: int


class VerificationStatusRequest(BaseModel):
    """Request to check verification status."""
    verification_id: str


# MongoDB document template
VERIFICATION_TEMPLATE = {
    "_id": ObjectId,
    "verification_id": str,  # UUID, unique
    "certificate_id": str,
    "verifier_email": str,
    "verified_by_id": Optional[ObjectId],  # Reference to User
    "verification_timestamp": datetime,
    "confidence_score": float,  # 0-100
    "verdict": str,  # "verified", "suspicious", "fraud"
    "fraud_layers_result": {
        "exif_score": float,  # 0-20
        "ela_score": float,  # 0-20
        "gemini_score": float,  # 0-20
        "database_score": float,  # 0-20
        "blockchain_score": float,  # 0-10
        "geo_fraud_score": float,  # 0-10
        "breakdown": Dict,
    },
    "layer_details": {
        "exif": Dict,
        "ela": Dict,
        "gemini": Dict,
        "database": Dict,
        "blockchain": Dict,
        "geo_fraud": Dict,
    },
    "report_url": str,
    "created_at": datetime,
}
