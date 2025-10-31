"""Layer 4: Database Cross-Verification (0-20 points)."""
from app.fraud_detection.base import FraudDetectionLayer
from motor.motor_asyncio import AsyncDatabase
from difflib import SequenceMatcher
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseLayer(FraudDetectionLayer):
    """Database cross-verification layer using fuzzy matching."""

    def __init__(self, db: AsyncDatabase = None):
        super().__init__(max_score=20.0)
        self.db = db

    async def analyze(
        self,
        image_data: bytes,
        extracted_details: Dict[str, Any] = None,
        db: AsyncDatabase = None
    ) -> Dict[str, Any]:
        """
        Cross-verify certificate details against database.
        Uses fuzzy matching with Levenshtein distance.
        """
        if extracted_details is None:
            extracted_details = {}

        if db is None:
            db = self.db

        if not db:
            return self._get_error_response("No database connection")

        try:
            certificates_col = db["certificates"]

            # Extract search parameters
            holder_name = extracted_details.get("holder_name", "")
            institution_name = extracted_details.get("institution_name", "")
            degree_type = extracted_details.get("degree_type", "")

            # Search in database
            matches = await self._fuzzy_search(
                certificates_col,
                holder_name,
                institution_name,
                degree_type,
            )

            score = self._calculate_score(matches)
            is_revoked = any(m.get("is_revoked") for m in matches)

            flags = []
            if not matches:
                flags.append("No matching certificate found in database")
            elif len(matches) > 1:
                flags.append(f"Multiple matches found ({len(matches)})")
            if is_revoked:
                flags.append("Matched certificate is revoked")

            return {
                "score": score,
                "match_found": len(matches) > 0,
                "matched_certificate": str(matches[0].get("_id")) if matches else None,
                "match_quality": self._get_match_quality(matches),
                "is_revoked": is_revoked,
                "matches_count": len(matches),
                "details": {
                    "search_holder": holder_name,
                    "search_institution": institution_name,
                    "search_degree": degree_type,
                    "matches": len(matches),
                },
                "flags": flags,
            }
        except Exception as e:
            logger.error(f"Database verification error: {str(e)}")
            return self._get_error_response(str(e))

    async def _fuzzy_search(
        self,
        certificates_col,
        holder_name: str,
        institution_name: str,
        degree_type: str,
    ) -> list:
        """Perform fuzzy search for matching certificates."""
        threshold = 0.85  # 85% similarity threshold
        matches = []

        try:
            # Get all certificates
            all_certs = await certificates_col.find({}).to_list(None)

            for cert in all_certs:
                if cert.get("is_revoked"):
                    continue

                # Calculate similarity scores
                holder_similarity = self._fuzzy_match(
                    holder_name.lower(),
                    cert.get("holder_name", "").lower()
                )
                institution_similarity = self._fuzzy_match(
                    institution_name.lower(),
                    cert.get("institution_id", "")
                )

                # Accept if both holder and institution match above threshold
                if holder_similarity >= threshold and institution_similarity >= threshold:
                    matches.append({
                        **cert,
                        "similarity_holder": holder_similarity,
                        "similarity_institution": institution_similarity,
                    })

            # Sort by similarity
            matches.sort(key=lambda x: x.get("similarity_holder", 0), reverse=True)
            return matches[:5]  # Return top 5 matches

        except Exception as e:
            logger.error(f"Fuzzy search error: {str(e)}")
            return []

    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """Calculate fuzzy match similarity (0-1)."""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1, str2).ratio()

    def _calculate_score(self, matches: list) -> float:
        """Calculate score based on matches."""
        if not matches:
            return 0.0  # No match found
        elif len(matches) == 1:
            similarity = matches[0].get("similarity_holder", 0)
            if similarity >= 0.95:
                return 20.0  # Exact match
            elif similarity >= 0.85:
                return 15.0  # Strong match
            else:
                return 8.0
        else:
            # Multiple matches found - slightly suspicious
            return 5.0

    def _get_match_quality(self, matches: list) -> str:
        """Get match quality description."""
        if not matches:
            return "none"
        elif len(matches) == 1:
            similarity = matches[0].get("similarity_holder", 0)
            if similarity >= 0.95:
                return "exact"
            elif similarity >= 0.85:
                return "fuzzy"
            else:
                return "partial"
        else:
            return "partial"

    def _get_error_response(self, error: str) -> Dict[str, Any]:
        """Get error response."""
        return {
            "score": 0.0,
            "match_found": False,
            "matched_certificate": None,
            "match_quality": "none",
            "is_revoked": False,
            "matches_count": 0,
            "details": {},
            "flags": [f"Database verification error: {error}"],
        }
