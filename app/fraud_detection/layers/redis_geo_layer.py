"""Layer 6: Geo-Fraud Pattern Detection (0-10 points)."""
from app.fraud_detection.base import FraudDetectionLayer
from app.core.redis_client import (
    get_redis,
    add_geo_fraud_cluster,
    get_geo_cluster_count,
    is_ip_blacklisted,
)
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class RedisGeoLayer(FraudDetectionLayer):
    """Redis-based geo-fraud pattern detection layer."""

    def __init__(self):
        super().__init__(max_score=10.0)

    async def analyze(
        self,
        image_data: bytes,
        ip_address: str = None,
        geolocation: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Detect fraud patterns via geolocation and IP clustering.
        Identifies fraud rings and suspicious patterns.
        """
        try:
            if not ip_address:
                ip_address = "unknown"

            # Default geolocation
            if not geolocation:
                geolocation = {
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "country": "Unknown",
                    "city": "Unknown",
                }

            # Check if IP is blacklisted
            ip_blacklisted = await is_ip_blacklisted(ip_address)
            if ip_blacklisted:
                return {
                    "score": -10.0,
                    "ip_address": ip_address,
                    "geolocation": geolocation,
                    "anomalies_detected": ["IP blacklisted for fraud"],
                    "fraud_ring_confidence": 1.0,
                    "details": {
                        "ip_status": "blacklisted",
                    },
                    "flags": ["IP address blacklisted - high fraud confidence"],
                }

            # Analyze geo patterns
            anomalies = []
            score = 10.0  # Start with perfect score

            try:
                redis = get_redis()

                # Add IP to geo cluster
                await add_geo_fraud_cluster(
                    geolocation.get("latitude", 0),
                    geolocation.get("longitude", 0),
                    ip_address,
                )

                # Get cluster count
                cluster_count = await get_geo_cluster_count(
                    geolocation.get("latitude", 0),
                    geolocation.get("longitude", 0),
                )

                # Detect patterns
                if cluster_count > 50:
                    anomalies.append("High volume of verifications from same location")
                    score -= 8
                elif cluster_count > 20:
                    anomalies.append("Moderate clustering detected")
                    score -= 3

            except Exception as e:
                logger.debug(f"Redis geo analysis error: {str(e)}")
                # Continue without Redis

            # Detect geographic impossibilities
            # (In a real implementation, would compare with previous verifications)

            score = self._validate_score(score)

            return {
                "score": score,
                "ip_address": ip_address,
                "geolocation": geolocation,
                "anomalies_detected": anomalies,
                "fraud_ring_confidence": max(0, 1.0 - (score / 10.0)),
                "details": {
                    "cluster_count": cluster_count if 'cluster_count' in locals() else 0,
                    "analysis_type": "geo_clustering",
                },
                "flags": anomalies if anomalies else ["No anomalies detected"],
            }

        except Exception as e:
            logger.error(f"Geo fraud analysis error: {str(e)}")
            return {
                "score": 10.0,  # Neutral on error
                "ip_address": ip_address or "unknown",
                "geolocation": geolocation or {},
                "anomalies_detected": [],
                "fraud_ring_confidence": 0.0,
                "details": {},
                "flags": [f"Geo analysis error: {str(e)}"],
            }
