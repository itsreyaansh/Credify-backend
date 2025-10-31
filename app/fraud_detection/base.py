"""Base class for fraud detection layers."""
from abc import ABC, abstractmethod
from typing import Dict, Any
from PIL import Image
import io


class FraudDetectionLayer(ABC):
    """Abstract base class for fraud detection layers."""

    def __init__(self, max_score: float = 20.0):
        """Initialize fraud detection layer."""
        self.max_score = max_score

    @abstractmethod
    async def analyze(self, image_data: bytes) -> Dict[str, Any]:
        """
        Analyze image for fraud indicators.

        Args:
            image_data: Raw image bytes

        Returns:
            Dictionary with score and details
        """
        pass

    def _load_image(self, image_data: bytes) -> Image.Image:
        """Load image from bytes."""
        return Image.open(io.BytesIO(image_data))

    def _get_base_score(self) -> float:
        """Get baseline score for this layer."""
        return self.max_score

    def _validate_score(self, score: float) -> float:
        """Ensure score is within valid range."""
        return max(0, min(score, self.max_score))
