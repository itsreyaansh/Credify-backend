"""
EXIF Metadata Analysis Layer - Analyzes image metadata for fraud indicators.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime
from PIL import Image
import exifread
from pathlib import Path

from ..base import FraudDetectionLayer, LayerResult

logger = logging.getLogger(__name__)


class ExifLayer(FraudDetectionLayer):
    """
    Fraud detection layer that analyzes EXIF metadata.
    
    Checks for:
    - Missing EXIF data (common in forged documents)
    - Suspicious software in Software tag (Photoshop, GIMP, etc.)
    - Impossible or suspicious dates
    - GPS data inconsistencies
    - Recent modifications after issue date
    
    Max Score: 20 points
    """
    
    # Suspicious software names
    SUSPICIOUS_SOFTWARE = [
        "photoshop", "gimp", "paint.net", "pixlr", "affinity",
        "photoscape", "krita", "paintshop", "corel"
    ]
    
    def __init__(self):
        super().__init__(name="EXIF Metadata Analysis", max_score=20.0)
    
    async def analyze(
        self,
        certificate_path: str,
        metadata: Dict[str, Any]
    ) -> LayerResult:
        """
        Analyze EXIF metadata of certificate image.
        
        Args:
            certificate_path: Path to certificate image
            metadata: Certificate metadata (issue_date, etc.)
            
        Returns:
            LayerResult with EXIF analysis
        """
        score = 20.0  # Start with perfect score, deduct for issues
        confidence = 1.0
        risk_flags: List[str] = []
        exif_data: Dict[str, Any] = {}
        reasoning_parts: List[str] = []
        
        try:
            # Open image and extract EXIF
            with open(certificate_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            
            # Convert tags to dict
            exif_data = {
                tag: str(value) for tag, value in tags.items()
                if not tag.startswith('JPEGThumbnail')
            }
            
            # Check 1: Missing EXIF data
            if not exif_data or len(exif_data) < 5:
                score -= 5
                risk_flags.append("MISSING_EXIF")
                reasoning_parts.append("Missing or minimal EXIF data (common in forged documents)")
                confidence = 0.7
            else:
                reasoning_parts.append(f"EXIF data present ({len(exif_data)} fields)")
            
            # Check 2: Software tag analysis
            software = self._get_tag_value(tags, 'Image Software')
            if software:
                software_lower = software.lower()
                suspicious = [s for s in self.SUSPICIOUS_SOFTWARE if s in software_lower]
                if suspicious:
                    score -= 3 * len(suspicious)
                    risk_flags.append(f"SUSPICIOUS_SOFTWARE:{suspicious[0].upper()}")
                    reasoning_parts.append(f"Edited with suspicious software: {software}")
                else:
                    reasoning_parts.append(f"Software: {software} (acceptable)")
            
            # Check 3: DateTime analysis
            datetime_original = self._get_tag_value(tags, 'EXIF DateTimeOriginal')
            datetime_digitized = self._get_tag_value(tags, 'EXIF DateTimeDigitized')
            datetime_modified = self._get_tag_value(tags, 'Image DateTime')
            
            if datetime_original:
                try:
                    dt_original = datetime.strptime(datetime_original, '%Y:%m:%d %H:%M:%S')
                    
                    # Check if date is in the future
                    if dt_original > datetime.now():
                        score -= 5
                        risk_flags.append("FUTURE_DATE")
                        reasoning_parts.append("Image date is in the future (impossible)")
                    
                    # Check if date is too old (before 2000)
                    elif dt_original.year < 2000:
                        score -= 2
                        risk_flags.append("VERY_OLD_DATE")
                        reasoning_parts.append("Image date is suspiciously old")
                    
                    # Check against certificate issue date if available
                    if 'issue_date' in metadata:
                        issue_date = metadata['issue_date']
                        if isinstance(issue_date, str):
                            issue_date = datetime.fromisoformat(issue_date.replace('Z', '+00:00'))
                        
                        # Image should not be created significantly after issue date
                        days_diff = (dt_original - issue_date).days
                        if days_diff > 180:  # More than 6 months after
                            score -= 3
                            risk_flags.append("LATE_CREATION")
                            reasoning_parts.append(
                                f"Image created {days_diff} days after issue date (suspicious)"
                            )
                
                except ValueError:
                    risk_flags.append("INVALID_DATE_FORMAT")
                    reasoning_parts.append("Invalid date format in EXIF")
            
            # Check 4: GPS data analysis
            gps_lat = self._get_tag_value(tags, 'GPS GPSLatitude')
            gps_lon = self._get_tag_value(tags, 'GPS GPSLongitude')
            
            if gps_lat and gps_lon:
                # Check if GPS location is in India (for Indian certificates)
                if metadata.get('country') == 'India':
                    # Rough India bounds: lat 8-37, lon 68-97
                    try:
                        lat = self._parse_gps_coord(gps_lat)
                        lon = self._parse_gps_coord(gps_lon)
                        
                        if not (8 <= lat <= 37 and 68 <= lon <= 97):
                            score -= 2
                            risk_flags.append("GPS_LOCATION_MISMATCH")
                            reasoning_parts.append("GPS location outside India (suspicious for Indian certificate)")
                    except:
                        pass
            
            # Check 5: Modification time vs creation time
            if datetime_modified and datetime_original:
                try:
                    dt_modified = datetime.strptime(datetime_modified, '%Y:%m:%d %H:%M:%S')
                    dt_original = datetime.strptime(datetime_original, '%Y:%m:%d %H:%M:%S')
                    
                    # If modified significantly after original, could be edited
                    diff_days = (dt_modified - dt_original).days
                    if diff_days > 1:
                        score -= 1
                        risk_flags.append("MODIFIED_AFTER_CREATION")
                        reasoning_parts.append(f"Image modified {diff_days} days after creation")
                except:
                    pass
            
            # Check 6: Camera/Device information
            camera_make = self._get_tag_value(tags, 'Image Make')
            camera_model = self._get_tag_value(tags, 'Image Model')
            
            if camera_make or camera_model:
                exif_data['camera'] = f"{camera_make or ''} {camera_model or ''}".strip()
                reasoning_parts.append(f"Camera: {exif_data['camera']}")
            
            # Check 7: Image resolution
            width = self._get_tag_value(tags, 'EXIF ExifImageWidth')
            height = self._get_tag_value(tags, 'EXIF ExifImageLength')
            
            if width and height:
                try:
                    w = int(width)
                    h = int(height)
                    
                    # Very low resolution could indicate screenshot or scan quality issue
                    if w < 800 or h < 600:
                        score -= 1
                        risk_flags.append("LOW_RESOLUTION")
                        reasoning_parts.append(f"Low resolution image: {w}x{h}")
                except:
                    pass
            
            # Bonus: All checks passed
            if not risk_flags:
                score = 20.0
                reasoning_parts.append("All EXIF checks passed successfully")
            
            # Ensure score is within bounds
            score = max(0, min(20, score))
            
            # Build final reasoning
            reasoning = "; ".join(reasoning_parts)
            
            logger.info(f"EXIF Analysis complete: Score={score}, Flags={len(risk_flags)}")
            
            return LayerResult(
                score=score,
                confidence=confidence,
                reasoning=reasoning,
                metadata={
                    "exif_fields_count": len(exif_data),
                    "exif_data": exif_data,
                    "software": software,
                    "datetime_original": datetime_original,
                    "gps_location": {"lat": gps_lat, "lon": gps_lon} if gps_lat else None
                },
                risk_flags=risk_flags
            )
            
        except Exception as e:
            logger.error(f"EXIF analysis failed: {e}")
            return LayerResult(
                score=0.0,
                confidence=0.0,
                reasoning=f"EXIF analysis error: {str(e)}",
                metadata={"error": str(e)},
                risk_flags=["EXIF_ANALYSIS_ERROR"]
            )
    
    def _get_tag_value(self, tags: Dict, tag_name: str) -> str:
        """Get EXIF tag value safely."""
        tag = tags.get(tag_name)
        return str(tag) if tag else None
    
    def _parse_gps_coord(self, coord_str: str) -> float:
        """Parse GPS coordinate from EXIF format."""
        # Format: [degrees, minutes, seconds]
        parts = coord_str.strip('[]').split(',')
        if len(parts) >= 2:
            degrees = float(parts[0])
            minutes = float(parts[1]) if len(parts) > 1 else 0
            return degrees + minutes / 60.0
        return 0.0
