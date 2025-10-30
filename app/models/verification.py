"""
Verification result data model and Pydantic schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence level enum."""
    VERIFIED = "verified"
    SUSPICIOUS = "suspicious"
    FRAUD = "fraud"


class ManualReviewStatus(str, Enum):
    """Manual review status enum."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class FraudScores(BaseModel):
    """Schema for individual fraud layer scores."""
    exif_score: float = Field(..., ge=0, le=20)
    ela_score: float = Field(..., ge=0, le=20)
    gemini_score: float = Field(..., ge=0, le=20)
    db_score: float = Field(..., ge=0, le=20)
    blockchain_score: float = Field(..., ge=0, le=10)
    geo_score: float = Field(..., ge=0, le=10)


class VerificationRequest(BaseModel):
    """Schema for verification request."""
    certificate_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "certificate_id": "507f1f77bcf86cd799439011"
            }
        }


class LayerAnalysisResult(BaseModel):
    """Schema for individual layer analysis result."""
    layer_name: str
    score: float
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str
    metadata: Dict[str, Any]
    risk_flags: List[str] = []


class VerificationResponse(BaseModel):
    """Schema for verification response."""
    id: str = Field(..., alias="_id")
    certificate_id: str
    verifier_id: str
    fraud_scores: FraudScores
    total_score: int = Field(..., ge=0, le=100)
    confidence_level: ConfidenceLevel
    verification_details: Dict[str, Any]
    manual_review_required: bool = False
    manual_review_status: Optional[ManualReviewStatus] = None
    manual_reviewer_id: Optional[str] = None
    manual_review_notes: Optional[str] = None
    processing_time_ms: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "certificate_id": "507f1f77bcf86cd799439012",
                "total_score": 85,
                "confidence_level": "verified",
                "processing_time_ms": 3200,
                "manual_review_required": False
            }
        }


class ManualReviewRequest(BaseModel):
    """Schema for requesting manual review."""
    reason: str = Field(..., min_length=10, max_length=500)


class ManualReviewAction(BaseModel):
    """Schema for manual review action."""
    notes: str = Field(..., min_length=10, max_length=1000)


class VerificationListResponse(BaseModel):
    """Schema for list of verifications."""
    verifications: List[VerificationResponse]
    total: int
    skip: int
    limit: int


class VerificationStats(BaseModel):
    """Schema for verification statistics."""
    total_verifications: int
    verified_count: int
    suspicious_count: int
    fraud_count: int
    pending_review_count: int
    avg_processing_time_ms: float
