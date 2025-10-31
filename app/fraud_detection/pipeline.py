"""Fraud Detection Pipeline - orchestrates all 6 layers."""
from motor.motor_asyncio import AsyncDatabase
from app.fraud_detection.layers import (
    EXIFLayer,
    ELALayer,
    GeminiLayer,
    DatabaseLayer,
    BlockchainLayer,
    RedisGeoLayer,
)
from typing import Dict, Any, Optional
import time
import asyncio
import logging

logger = logging.getLogger(__name__)


class FraudDetectionPipeline:
    """Main fraud detection pipeline orchestrating all 6 layers."""

    # Maximum points for each layer
    MAX_EXIF = 20.0
    MAX_ELA = 20.0
    MAX_GEMINI = 20.0
    MAX_DATABASE = 20.0
    MAX_BLOCKCHAIN = 10.0
    MAX_GEO = 10.0
    TOTAL_MAX = 100.0

    def __init__(self, db: AsyncDatabase):
        """Initialize pipeline with database connection."""
        self.db = db
        self.exif_layer = EXIFLayer()
        self.ela_layer = ELALayer()
        self.gemini_layer = GeminiLayer()
        self.database_layer = DatabaseLayer(db)
        self.blockchain_layer = BlockchainLayer()
        self.geo_layer = RedisGeoLayer()

    async def verify(
        self,
        image_data: bytes,
        certificate_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        geolocation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run complete fraud detection pipeline.
        Executes all 6 layers and calculates final verdict.
        """
        start_time = time.time()

        try:
            logger.info(f"Starting fraud detection for certificate {certificate_id}")

            # Layer 1 & 2 & 4 & 6: Fast layers (can run in parallel)
            layer1_task = asyncio.create_task(self.exif_layer.analyze(image_data))
            layer2_task = asyncio.create_task(self.ela_layer.analyze(image_data))
            layer4_task = asyncio.create_task(
                self.database_layer.analyze(image_data)
            )
            layer6_task = asyncio.create_task(
                self.geo_layer.analyze(image_data, ip_address, geolocation)
            )

            # Run fast layers in parallel
            layer1_result, layer2_result, layer4_result, layer6_result = await asyncio.gather(
                layer1_task,
                layer2_task,
                layer4_task,
                layer6_task,
            )

            # Layer 3: Gemini (slow but important, run in parallel)
            layer3_task = asyncio.create_task(
                self.gemini_layer.analyze(image_data)
            )

            # Layer 5: Blockchain (slow)
            layer5_task = asyncio.create_task(
                self.blockchain_layer.analyze(image_data, certificate_id)
            )

            # Wait for remaining layers
            layer3_result, layer5_result = await asyncio.gather(
                layer3_task,
                layer5_task,
            )

            # Calculate total score
            total_score = (
                layer1_result.get("score", 0) +
                layer2_result.get("score", 0) +
                layer3_result.get("score", 0) +
                layer4_result.get("score", 0) +
                layer5_result.get("score", 0) +
                layer6_result.get("score", 0)
            )

            # Determine verdict
            verdict = self._get_verdict(total_score)

            processing_time = (time.time() - start_time) * 1000  # milliseconds

            result = {
                "confidence_score": total_score,
                "verdict": verdict,
                "processing_time_ms": int(processing_time),
                "fraud_layers_result": {
                    "exif_score": layer1_result.get("score", 0),
                    "ela_score": layer2_result.get("score", 0),
                    "gemini_score": layer3_result.get("score", 0),
                    "database_score": layer4_result.get("score", 0),
                    "blockchain_score": layer5_result.get("score", 0),
                    "geo_fraud_score": layer6_result.get("score", 0),
                    "breakdown": {
                        "exif": layer1_result,
                        "ela": layer2_result,
                        "gemini": layer3_result,
                        "database": layer4_result,
                        "blockchain": layer5_result,
                        "geo": layer6_result,
                    },
                },
                "layer_details": {
                    "exif": layer1_result,
                    "ela": layer2_result,
                    "gemini": layer3_result,
                    "database": layer4_result,
                    "blockchain": layer5_result,
                    "geo_fraud": layer6_result,
                },
            }

            logger.info(
                f"Fraud detection complete: {verdict} "
                f"(score: {total_score:.1f}, time: {processing_time:.0f}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"Error in fraud detection pipeline: {str(e)}", exc_info=True)
            return {
                "confidence_score": 50,  # Neutral score on error
                "verdict": "suspicious",
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
                "fraud_layers_result": {
                    "exif_score": 0,
                    "ela_score": 0,
                    "gemini_score": 0,
                    "database_score": 0,
                    "blockchain_score": 0,
                    "geo_fraud_score": 0,
                    "breakdown": {},
                },
                "layer_details": {},
            }

    def _get_verdict(self, score: float) -> str:
        """Determine verdict based on confidence score."""
        if score >= 80:
            return "verified"
        elif score >= 40:
            return "suspicious"
        else:
            return "fraud"

    def _get_layer_effectiveness(self) -> Dict[str, float]:
        """Calculate effectiveness of each layer."""
        return {
            "exif": 0.8,
            "ela": 0.85,
            "gemini": 0.92,
            "database": 0.75,
            "blockchain": 0.95,
            "geo": 0.70,
        }
