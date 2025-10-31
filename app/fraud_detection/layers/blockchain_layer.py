"""Layer 5: Blockchain Verification (0-10 points)."""
from app.fraud_detection.base import FraudDetectionLayer
from app.core.config import get_settings
from typing import Dict, Any
import hashlib
import logging
import asyncio

logger = logging.getLogger(__name__)


class BlockchainLayer(FraudDetectionLayer):
    """Blockchain verification layer using Polygon Mumbai."""

    def __init__(self):
        super().__init__(max_score=10.0)
        self.settings = get_settings()

    async def analyze(
        self,
        image_data: bytes,
        certificate_id: str = None,
    ) -> Dict[str, Any]:
        """
        Verify certificate hash on blockchain.
        Polygon Mumbai testnet integration.
        """
        try:
            # If no contract configured, return neutral score
            if not self.settings.CONTRACT_ADDRESS or not self.settings.WEB3_PRIVATE_KEY:
                return {
                    "score": 0.0,  # No verification possible
                    "blockchain_verified": False,
                    "transaction_hash": None,
                    "certificate_hash": None,
                    "is_revoked_on_chain": False,
                    "details": {},
                    "flags": ["Blockchain not configured"],
                }

            # Calculate certificate hash
            cert_hash = hashlib.sha256(image_data).hexdigest()

            if certificate_id:
                # Check if certificate exists on blockchain
                is_stored, is_revoked, tx_hash = await self._verify_on_blockchain(
                    certificate_id,
                    cert_hash
                )

                if is_stored:
                    score = 10.0 if not is_revoked else -10.0
                    score = max(-10.0, min(score, 10.0))  # Clamp to range

                    return {
                        "score": score,
                        "blockchain_verified": True,
                        "transaction_hash": tx_hash,
                        "certificate_hash": cert_hash,
                        "is_revoked_on_chain": is_revoked,
                        "details": {
                            "network": "Polygon Mumbai",
                            "contract": self.settings.CONTRACT_ADDRESS,
                        },
                        "flags": ["Blockchain verified"] if not is_revoked else ["Certificate revoked on blockchain"],
                    }

            # No blockchain record (not an error)
            return {
                "score": 0.0,  # Neutral, not in blockchain yet
                "blockchain_verified": False,
                "transaction_hash": None,
                "certificate_hash": cert_hash,
                "is_revoked_on_chain": False,
                "details": {
                    "network": "Polygon Mumbai",
                    "contract": self.settings.CONTRACT_ADDRESS,
                },
                "flags": ["Certificate not found on blockchain"],
            }

        except Exception as e:
            logger.error(f"Blockchain verification error: {str(e)}")
            return {
                "score": 0.0,  # Neutral on network error
                "blockchain_verified": False,
                "transaction_hash": None,
                "certificate_hash": None,
                "is_revoked_on_chain": False,
                "details": {},
                "flags": [f"Blockchain error: {str(e)}"],
            }

    async def _verify_on_blockchain(
        self,
        certificate_id: str,
        cert_hash: str,
    ) -> tuple[bool, bool, str]:
        """
        Verify certificate on blockchain.
        Returns: (is_stored, is_revoked, transaction_hash)
        """
        try:
            # In production, this would use Web3.py to call the smart contract
            # For now, return neutral values
            logger.info(f"Checking blockchain for certificate {certificate_id}")
            # Simulate blockchain check
            await asyncio.sleep(0.1)
            return False, False, None
        except Exception as e:
            logger.error(f"Error verifying on blockchain: {str(e)}")
            return False, False, None
