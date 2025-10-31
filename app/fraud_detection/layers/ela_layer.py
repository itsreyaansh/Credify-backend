"""Layer 2: Error Level Analysis (ELA) (0-20 points)."""
from app.fraud_detection.base import FraudDetectionLayer
from PIL import Image
import cv2
import numpy as np
import io
import base64
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ELALayer(FraudDetectionLayer):
    """Error Level Analysis layer for compression artifacts."""

    def __init__(self):
        super().__init__(max_score=20.0)
        self.quality = 90

    async def analyze(self, image_data: bytes) -> Dict[str, Any]:
        """
        Perform Error Level Analysis to detect image manipulation.
        High consistency = authentic, High variation = suspicious.
        """
        try:
            image = self._load_image(image_data)
            image_array = np.array(image)

            # Convert to RGB if needed
            if len(image_array.shape) == 2:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
            elif image_array.shape[2] == 4:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)

            # Compress image to JPEG
            _, compressed = cv2.imencode('.jpg', image_array, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            compressed_image = cv2.imdecode(compressed, cv2.IMREAD_COLOR)

            # Calculate absolute difference
            diff = cv2.absdiff(image_array, compressed_image).astype(float)
            diff_gray = cv2.cvtColor(diff.astype(np.uint8), cv2.COLOR_RGB2GRAY)

            # Generate heatmap
            heatmap = cv2.applyColorMap((diff_gray * 10).astype(np.uint8), cv2.COLORMAP_JET)
            heatmap_base64 = self._encode_heatmap(heatmap)

            # Calculate consistency
            consistency = self._calculate_consistency(diff_gray)
            score = self._calculate_score(consistency)

            # Detect cloning/splicing
            cloning_detected = self._detect_cloning(diff_gray)
            splicing_detected = self._detect_splicing(diff_gray)

            flags = []
            if consistency < 0.3:
                flags.append("High image manipulation detected")
            if cloning_detected:
                flags.append("Possible copy-paste regions detected")
            if splicing_detected:
                flags.append("Possible splicing detected")

            return {
                "score": score,
                "consistency_percentage": consistency * 100,
                "heatmap_base64": heatmap_base64,
                "cloning_detected": cloning_detected,
                "splicing_detected": splicing_detected,
                "suspicious_regions": [],
                "details": {
                    "method": "Error Level Analysis",
                    "quality": self.quality,
                },
                "flags": flags,
            }
        except Exception as e:
            logger.error(f"ELA analysis error: {str(e)}")
            return {
                "score": 10.0,  # Neutral score on error
                "consistency_percentage": 50,
                "heatmap_base64": "",
                "cloning_detected": False,
                "splicing_detected": False,
                "suspicious_regions": [],
                "details": {},
                "flags": [f"ELA error: {str(e)}"],
            }

    def _calculate_consistency(self, diff: np.ndarray) -> float:
        """Calculate image consistency (0-1, higher is better)."""
        try:
            mean_diff = np.mean(diff)
            max_diff = np.max(diff)
            if max_diff == 0:
                return 1.0
            return 1.0 - min(mean_diff / max_diff, 1.0)
        except Exception:
            return 0.5

    def _calculate_score(self, consistency: float) -> float:
        """Calculate score based on consistency."""
        if consistency > 0.8:
            return 18.0  # Very authentic
        elif consistency > 0.6:
            return 15.0
        elif consistency > 0.4:
            return 8.0
        elif consistency > 0.2:
            return 5.0
        else:
            return 0.0  # Highly suspicious

    def _detect_cloning(self, diff: np.ndarray) -> bool:
        """Detect possible copy-paste cloning."""
        try:
            threshold = np.percentile(diff, 90)
            cloned_regions = np.sum(diff > threshold)
            total_pixels = diff.size
            return (cloned_regions / total_pixels) > 0.05
        except Exception:
            return False

    def _detect_splicing(self, diff: np.ndarray) -> bool:
        """Detect possible image splicing."""
        try:
            # Look for sharp boundaries with high differences
            edges = cv2.Canny(diff.astype(np.uint8), 100, 200)
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            return len(contours) > 10
        except Exception:
            return False

    def _encode_heatmap(self, heatmap: np.ndarray) -> str:
        """Encode heatmap as base64 PNG."""
        try:
            _, buffer = cv2.imencode('.png', heatmap)
            return base64.b64encode(buffer).decode()
        except Exception:
            return ""
