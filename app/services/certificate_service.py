"""Certificate service for certificate management."""
from motor.motor_asyncio import AsyncDatabase
from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for certificate operations."""

    def __init__(self, db: AsyncDatabase):
        """Initialize certificate service."""
        self.db = db
        self.certificates_col = db["certificates"]

    async def upload_certificate(
        self,
        issuer_id: str,
        certificate_name: str,
        holder_name: str,
        issue_date: datetime,
        certificate_image_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload and store a certificate."""
        cert_doc = {
            "_id": ObjectId(),
            "certificate_id": str(uuid.uuid4()),
            "issuer_id": ObjectId(issuer_id),
            "certificate_name": certificate_name,
            "holder_name": holder_name,
            "issue_date": issue_date,
            "certificate_image": certificate_image_url,
            "is_revoked": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": metadata or {},
        }

        result = await self.certificates_col.insert_one(cert_doc)
        return {"certificate_id": cert_doc["certificate_id"]}

    async def get_certificate(self, certificate_id: str) -> Optional[Dict[str, Any]]:
        """Get certificate by ID."""
        cert = await self.certificates_col.find_one({"certificate_id": certificate_id})
        return cert
