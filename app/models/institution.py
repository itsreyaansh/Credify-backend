"""
Institution data model and Pydantic schemas.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class InstitutionCreate(BaseModel):
    """Schema for creating institution."""
    name: str = Field(..., min_length=3, max_length=200)
    registration_number: str = Field(..., min_length=3, max_length=100)
    address: str = Field(..., min_length=10, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    website_url: Optional[str] = None
    contact_email: EmailStr
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Indian Institute of Technology Delhi",
                "registration_number": "IIT-DEL-2024",
                "address": "Hauz Khas, New Delhi",
                "city": "New Delhi",
                "state": "Delhi",
                "latitude": 28.5450,
                "longitude": 77.1930,
                "website_url": "https://home.iitd.ac.in",
                "contact_email": "registrar@admin.iitd.ac.in"
            }
        }


class InstitutionUpdate(BaseModel):
    """Schema for updating institution."""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    address: Optional[str] = Field(None, min_length=10, max_length=500)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    website_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None


class InstitutionResponse(BaseModel):
    """Schema for institution response."""
    id: str = Field(..., alias="_id")
    name: str
    registration_number: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    website_url: Optional[str] = None
    contact_email: EmailStr
    is_verified: bool = False
    certificates_issued: int = 0
    certificates_verified: int = 0
    fraud_rate: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "IIT Delhi",
                "city": "New Delhi",
                "state": "Delhi",
                "is_verified": True,
                "certificates_issued": 1200,
                "fraud_rate": 0.02
            }
        }


class InstitutionVerificationStatus(BaseModel):
    """Schema for updating institution verification status."""
    verified: bool


class InstitutionStats(BaseModel):
    """Schema for institution statistics."""
    total_institutions: int
    verified_institutions: int
    pending_verification: int
    top_fraud_institutions: list[Dict[str, Any]]
    fraud_by_state: Dict[str, int]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_institutions": 150,
                "verified_institutions": 120,
                "pending_verification": 30,
                "top_fraud_institutions": [
                    {"name": "Fake University", "fraud_count": 45}
                ],
                "fraud_by_state": {
                    "Delhi": 23,
                    "Maharashtra": 18
                }
            }
        }


from typing import Dict, Any
