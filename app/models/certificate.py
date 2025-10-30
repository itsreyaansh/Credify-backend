"""Certificate model and schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId


class CertificateMetadata(BaseModel):
    """Certificate metadata."""
    degree_type: Optional[str] = None
    field_of_study: Optional[str] = None
    gpa: Optional[float] = None
    credits: Optional[int] = None
    location: Optional[str] = None


class CertificateCreate(BaseModel):
    """Certificate creation schema."""
    certificate_name: str = Field(..., min_length=1, max_length=200)
    holder_name: str = Field(..., min_length=2, max_length=100)
    issue_date: datetime
    expiry_date: Optional[datetime] = None
    metadata: Optional[CertificateMetadata] = None


class CertificateUpdate(BaseModel):
    """Certificate update schema."""
    certificate_name: Optional[str] = None
    metadata: Optional[CertificateMetadata] = None


class CertificateRevoke(BaseModel):
    """Certificate revocation schema."""
    reason: str = Field(..., min_length=5, max_length=500)


class CertificateShare(BaseModel):
    """Certificate sharing schema."""
    emails: list[str] = Field(..., min_items=1, max_items=50)


class CertificateResponse(BaseModel):
    """Certificate response schema."""
    id: str = Field(alias="_id")
    certificate_id: str
    certificate_name: str
    holder_name: str
    issue_date: datetime
    expiry_date: Optional[datetime] = None
    certificate_image: Optional[str] = None
    certificate_pdf_url: Optional[str] = None
    qr_code_data: Optional[str] = None
    blockchain_hash: Optional[str] = None
    blockchain_tx: Optional[str] = None
    is_revoked: bool
    revocation_reason: Optional[str] = None
    metadata: Optional[CertificateMetadata] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
        }


class CertificateListResponse(BaseModel):
    """Certificate list response schema."""
    certificates: list[CertificateResponse]
    total: int
    page: int
    limit: int


# MongoDB document template
CERTIFICATE_TEMPLATE = {
    "_id": ObjectId,
    "certificate_id": str,  # UUID, unique
    "student_id": ObjectId,  # Reference to User
    "issuer_id": ObjectId,  # Reference to User
    "institution_id": ObjectId,  # Reference to Institution
    "certificate_name": str,
    "holder_name": str,
    "issue_date": datetime,
    "expiry_date": Optional[datetime],
    "certificate_image": str,  # S3 URL or Base64
    "certificate_pdf_url": str,
    "qr_code_data": str,  # JWT-signed
    "blockchain_hash": str,  # SHA-256
    "blockchain_tx": str,  # Transaction hash
    "is_revoked": bool,
    "revocation_reason": Optional[str],
    "created_at": datetime,
    "updated_at": datetime,
    "metadata": {
        "degree_type": Optional[str],
        "field_of_study": Optional[str],
        "gpa": Optional[float],
        "credits": Optional[int],
        "location": Optional[str],
    },
}
