"""QR code generation utilities."""
import qrcode
import io
import base64
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def generate_qr_code(data: str, size: int = 10) -> Optional[bytes]:
    """
    Generate QR code image.

    Args:
        data: Data to encode in QR code (typically verification URL with JWT)
        size: QR code size (default 10)

    Returns:
        PNG image bytes or None on error
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"QR code generation error: {str(e)}")
        return None


async def generate_qr_code_base64(data: str, size: int = 10) -> Optional[str]:
    """
    Generate QR code and return as base64 string.

    Args:
        data: Data to encode
        size: QR code size

    Returns:
        Base64-encoded PNG or None on error
    """
    try:
        qr_bytes = await generate_qr_code(data, size)
        if qr_bytes:
            return base64.b64encode(qr_bytes).decode()
        return None
    except Exception as e:
        logger.error(f"QR code base64 generation error: {str(e)}")
        return None
