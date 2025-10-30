"""
Certificate data model and Pydantic schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, date
from enum import Enum


class CertificateType(str, Enum):
    """Certificate type enum."""
    DEGREE = "Degree"
    DIPLOMA = "Diploma"
    CERTIFICATE = "Certificate"
    OTHER = "Other"


class CertificateStatus(str, Enum):
    """Certificate verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPICIOUS = "suspicious"
    FRAUD = "fraud"


class CertificateUpload(BaseModel):
    """Schema for certificate upload."""
    certificate_name: str = Field(..., min_length=3, max_length=200)
    issue_date: date
    certificate_type: CertificateType
    expiry_date: Optional[date] = None
    issuer_id: Optional[str] = None  # Institution ID
    
    class Config:
        json_schema_extra = {
            "example": {
                "certificate_name": "Bachelor of Technology in Computer Science",
                "issue_date": "2024-06-15",
                "certificate_type": "Degree",
                "issuer_id": "507f1f77bcf86cd799439011"
            }
        }


class CertificateResponse(BaseModel):
    """Schema for certificate response."""
    id: str = Field(..., alias="_id")
    user_id: str
    issuer_id: str
    certificate_name: str
    certificate_hash: str
    image_url: str
    issue_date: date
    expiry_date: Optional[date] = None
    certificate_type: CertificateType
    metadata: Optional[Dict[str, Any]] = None
    blockchain_tx: Optional[str] = None
    blockchain_recorded_at: Optional[datetime] = None
    status: CertificateStatus = CertificateStatus.PENDING
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "certificate_name": "Bachelor of Technology",
                "status": "verified",
                "issue_date": "2024-06-15",
                "certificate_type": "Degree"
            }
        }


class CertificateUpdate(BaseModel):
    """Schema for updating certificate."""
    certificate_name: Optional[str] = Field(None, min_length=3, max_length=200)
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    certificate_type: Optional[CertificateType] = None


class CertificateStatusUpdate(BaseModel):
    """Schema for updating certificate status."""
    status: CertificateStatus


class BulkUploadResult(BaseModel):
    """Schema for bulk upload result."""
    success_count: int
    error_count: int
    errors: list[Dict[str, Any]]
    processed_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "success_count": 45,
                "error_count": 5,
                "processed_count": 50,
                "errors": [
                    {"row": 3, "error": "Invalid issue date format"}
                ]
            }
        }
