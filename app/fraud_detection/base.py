"""
Base class for all fraud detection layers.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class LayerResult:
    """Result from a fraud detection layer."""
    score: float  # 0-20 for main layers, 0-10 for blockchain/geo
    confidence: float  # 0-1, how confident in this score
    reasoning: str  # Human-readable explanation
    metadata: Dict[str, Any]  # Detailed analysis data
    risk_flags: List[str]  # List of specific issues found
    
    def __post_init__(self):
        """Validate layer result."""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        if self.score < 0:
            raise ValueError("Score cannot be negative")


class FraudDetectionLayer(ABC):
    """
    Abstract base class for fraud detection layers.
    
    All fraud detection layers must inherit from this class
    and implement the analyze method.
    """
    
    def __init__(self, name: str, max_score: float):
        """
        Initialize fraud detection layer.
        
        Args:
            name: Layer name (e.g., "EXIF Analysis")
            max_score: Maximum score this layer can return
        """
        self.name = name
        self.max_score = max_score
    
    @abstractmethod
    async def analyze(
        self,
        certificate_path: str,
        metadata: Dict[str, Any]
    ) -> LayerResult:
        """
        Analyze certificate for fraud indicators.
        
        Args:
            certificate_path: Path to certificate image file
            metadata: Additional metadata (certificate info, institution, etc.)
            
        Returns:
            LayerResult with score, confidence, reasoning, metadata, and risk flags
            
        Raises:
            Exception: If analysis fails
        """
        pass
    
    def validate_score(self, score: float) -> float:
        """
        Validate and cap score within layer's maximum.
        
        Args:
            score: Raw score from analysis
            
        Returns:
            Validated score (0 to max_score)
        """
        if score < 0:
            return 0.0
        if score > self.max_score:
            return float(self.max_score)
        return float(score)
    
    def calculate_weighted_score(self, raw_score: float, confidence: float) -> float:
        """
        Calculate weighted score based on confidence.
        
        Args:
            raw_score: Raw score from analysis
            confidence: Confidence level (0-1)
            
        Returns:
            Weighted score
        """
        weighted = raw_score * confidence
        return self.validate_score(weighted)
    
    async def run(
        self,
        certificate_path: str,
        metadata: Dict[str, Any]
    ) -> LayerResult:
        """
        Run the fraud detection layer with error handling.
        
        Args:
            certificate_path: Path to certificate image
            metadata: Additional metadata
            
        Returns:
            LayerResult
        """
        try:
            result = await self.analyze(certificate_path, metadata)
            
            # Validate score
            result.score = self.validate_score(result.score)
            
            return result
            
        except Exception as e:
            # Return minimal score on error
            return LayerResult(
                score=0.0,
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                metadata={"error": str(e)},
                risk_flags=["ANALYSIS_ERROR"]
            )
