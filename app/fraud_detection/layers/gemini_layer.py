"""Layer 3: AI Vision Analysis with Gemini Flash 2.0 (0-20 points)."""
from app.fraud_detection.base import FraudDetectionLayer
from app.core.config import get_settings
from typing import Dict, Any
import base64
import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)


class GeminiLayer(FraudDetectionLayer):
    """AI Vision analysis using Google Gemini Flash 2.0."""

    def __init__(self):
        super().__init__(max_score=20.0)
        self.settings = get_settings()
        self.timeout = self.settings.GEMINI_TIMEOUT

    async def analyze(self, image_data: bytes) -> Dict[str, Any]:
        """
        Analyze certificate using Gemini AI for:
        - Seal/logo authenticity
        - Text quality and OCR
        - Layout professionalism
        - Editing signs
        """
        try:
            # If in demo mode or no API key, return neutral score
            if self.settings.DEMO_MODE or not self.settings.GEMINI_API_KEY:
                return self._get_demo_response()

            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Call Gemini API
            result = await self._call_gemini_api(image_base64)
            score = self._calculate_score(result)

            return {
                "score": score,
                "seal_authentic": result.get("seal_authentic", False),
                "seal_confidence": result.get("seal_confidence", 0.5),
                "extracted_text": result.get("extracted_text", ""),
                "ocr_confidence": result.get("ocr_confidence", 0.5),
                "layout_professional": result.get("layout_professional", True),
                "detected_editing": result.get("detected_editing", False),
                "extracted_details": result.get("extracted_details", {}),
                "details": result,
                "flags": result.get("flags", []),
            }
        except Exception as e:
            logger.error(f"Gemini analysis error: {str(e)}")
            return {
                "score": 10.0,  # Neutral score on error
                "seal_authentic": False,
                "seal_confidence": 0.0,
                "extracted_text": "",
                "ocr_confidence": 0.0,
                "layout_professional": False,
                "detected_editing": False,
                "extracted_details": {},
                "details": {},
                "flags": [f"Gemini analysis failed: {str(e)}"],
            }

    async def _call_gemini_api(self, image_base64: str) -> Dict[str, Any]:
        """Call Google Gemini API with vision model."""
        try:
            # Prepare API request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.GEMINI_MODEL}:generateContent"

            headers = {
                "Content-Type": "application/json",
            }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": self._get_analysis_prompt()
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ]
            }

            # Add API key
            url = f"{url}?key={self.settings.GEMINI_API_KEY}"

            # Call API with timeout
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_gemini_response(data)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Gemini API error: {response.status} - {error_text}")

        except asyncio.TimeoutError:
            logger.warning("Gemini API timeout")
            raise Exception("Gemini API timeout")
        except Exception as e:
            logger.error(f"Gemini API call error: {str(e)}")
            raise

    def _get_analysis_prompt(self) -> str:
        """Get the detailed analysis prompt for Gemini."""
        return """Analyze this certificate image and provide detailed assessment in JSON format with these fields:
1. seal_authentic (boolean): Is the seal/logo authentic and properly placed?
2. seal_confidence (0-1): Confidence in seal assessment
3. extracted_text (string): Main text visible on certificate
4. ocr_confidence (0-1): Confidence in OCR accuracy
5. layout_professional (boolean): Does layout look professional?
6. detected_editing (boolean): Signs of editing or manipulation?
7. extracted_details (object): {degree_type, issue_date, holder_name, institution_name, signatures}
8. flags (array): Any suspicious indicators

Return only valid JSON."""

    def _parse_gemini_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gemini API response."""
        try:
            # Extract text from response
            contents = response.get("candidates", [{}])[0].get("content", {})
            text = contents.get("parts", [{}])[0].get("text", "")

            # Try to parse JSON from response
            import json
            import re

            # Extract JSON from response text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result

            # Fallback to default response
            return {
                "seal_authentic": True,
                "seal_confidence": 0.7,
                "extracted_text": text[:200],
                "ocr_confidence": 0.7,
                "layout_professional": True,
                "detected_editing": False,
                "extracted_details": {},
                "flags": [],
            }
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
            return {
                "seal_authentic": True,
                "seal_confidence": 0.5,
                "extracted_text": "",
                "ocr_confidence": 0.5,
                "layout_professional": True,
                "detected_editing": False,
                "extracted_details": {},
                "flags": ["Failed to parse Gemini response"],
            }

    def _calculate_score(self, result: Dict[str, Any]) -> float:
        """Calculate score from Gemini analysis results."""
        score = 0.0

        # Seal authenticity (0-5 points)
        if result.get("seal_authentic"):
            score += result.get("seal_confidence", 0) * 5

        # Text quality and OCR (0-5 points)
        if result.get("extracted_text"):
            score += result.get("ocr_confidence", 0) * 5

        # Layout professionalism (0-5 points)
        if result.get("layout_professional"):
            score += 5

        # Editing signs (0-5 points, deduct if editing detected)
        if not result.get("detected_editing"):
            score += 5

        return self._validate_score(score)

    def _get_demo_response(self) -> Dict[str, Any]:
        """Return demo response when API is unavailable."""
        return {
            "score": 15.0,  # Assume legitimate in demo
            "seal_authentic": True,
            "seal_confidence": 0.9,
            "extracted_text": "Demo Certificate of Achievement",
            "ocr_confidence": 0.95,
            "layout_professional": True,
            "detected_editing": False,
            "extracted_details": {
                "degree_type": "Bachelor of Science",
                "issue_date": "2024-01-15",
                "holder_name": "Demo Student",
                "institution_name": "Demo University",
                "signatures": 2,
            },
            "details": {},
            "flags": ["Demo mode - no actual API call"],
        }
