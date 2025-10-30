"""Layer 1: EXIF Metadata Analysis (0-20 points)."""
from app.fraud_detection.base import FraudDetectionLayer
from PIL import Image
from PIL.ExifTags import TAGS
from typing import Dict, Any
import io
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EXIFLayer(FraudDetectionLayer):
    """EXIF metadata analysis layer."""

    def __init__(self):
        super().__init__(max_score=20.0)

    async def analyze(self, image_data: bytes) -> Dict[str, Any]:
        """
        Analyze image EXIF metadata.
        Baseline: 20 points. Subtract for suspicious indicators.
        """
        try:
            image = self._load_image(image_data)
            score = self._get_base_score()
            flags = []
            details = {}

            # Extract EXIF data
            exif_data = self._extract_exif(image)

            # Check for EXIF data presence
            if not exif_data:
                score -= 5
                flags.append("No EXIF data found")

            # Analyze EXIF fields
            software = exif_data.get("Software", "")
            if software:
                details["software"] = software
                # Check for editing software
                suspicious_software = ["photoshop", "gimp", "paint", "pixlr"]
                if any(soft in software.lower() for soft in suspicious_software):
                    score -= 10
                    flags.append(f"Suspicious software detected: {software}")

            # Check GPS data
            gps_info = exif_data.get("GPSInfo", {})
            if gps_info:
                score += 2
                details["gps_present"] = True
                flags.append("GPS data found (more authentic)")

            # Check DateTime
            datetime_val = exif_data.get("DateTime")
            if datetime_val:
                score += 8
                details["datetime"] = datetime_val
                flags.append("Valid DateTime found")

            # Analyze other fields
            make = exif_data.get("Make", "")
            model = exif_data.get("Model", "")
            if make and model:
                details["camera"] = f"{make} {model}"
                flags.append("Camera info found (legitimate)")

            score = self._validate_score(score)

            return {
                "score": score,
                "has_exif": bool(exif_data),
                "software_used": software or None,
                "gps_present": bool(gps_info),
                "metadata_consistency": len(exif_data) > 5,
                "flags": flags,
                "details": details,
            }
        except Exception as e:
            logger.error(f"EXIF analysis error: {str(e)}")
            return {
                "score": 10.0,  # Neutral score on error
                "has_exif": False,
                "software_used": None,
                "gps_present": False,
                "metadata_consistency": False,
                "flags": [f"EXIF analysis error: {str(e)}"],
                "details": {},
            }

    def _extract_exif(self, image: Image.Image) -> Dict[str, Any]:
        """Extract EXIF data from image."""
        try:
            exif_data = {}
            if hasattr(image, "_getexif") and callable(image._getexif):
                exif = image._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        exif_data[tag_name] = str(value)[:100]  # Limit string length
            return exif_data
        except Exception as e:
            logger.debug(f"Error extracting EXIF: {str(e)}")
            return {}
