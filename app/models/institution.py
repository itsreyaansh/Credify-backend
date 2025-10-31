"""Institution model and schemas."""
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional
from bson import ObjectId


class LocationInfo(BaseModel):
    """Location information."""
    latitude: float
    longitude: float
    city: str
    state: str


class InstitutionCreate(BaseModel):
    """Institution creation schema."""
    name: str = Field(..., min_length=2, max_length=200)
    code: str = Field(..., min_length=2, max_length=20)
    email_domain: Optional[str] = None
    website: Optional[str] = None
    location: Optional[LocationInfo] = None


class InstitutionUpdate(BaseModel):
    """Institution update schema."""
    name: Optional[str] = None
    email_domain: Optional[str] = None
    website: Optional[str] = None
    location: Optional[LocationInfo] = None


class InstitutionResponse(BaseModel):
    """Institution response schema."""
    id: str = Field(alias="_id")
    name: str
    code: str
    email_domain: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    location: Optional[LocationInfo] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
        }


class InstitutionListResponse(BaseModel):
    """Institution list response schema."""
    institutions: list[InstitutionResponse]
    total: int
    page: int
    limit: int


# MongoDB document template
INSTITUTION_TEMPLATE = {
    "_id": ObjectId,
    "name": str,  # Unique
    "code": str,  # Unique
    "email_domain": Optional[str],
    "logo_url": Optional[str],
    "website": Optional[str],
    "location": {
        "latitude": float,
        "longitude": float,
        "city": str,
        "state": str,
    },
    "created_at": datetime,
    "updated_at": datetime,
}
