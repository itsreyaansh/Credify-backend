"""PDF generation utilities using ReportLab."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from io import BytesIO
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def generate_certificate_pdf(
    certificate_image_path: str,
    certificate_details: dict,
    qr_code_path: str,
    verification_url: str,
) -> Optional[bytes]:
    """
    Generate PDF certificate with embedded QR code.

    Args:
        certificate_image_path: Path to certificate image
        certificate_details: Certificate metadata
        qr_code_path: Path to QR code image
        verification_url: Verification link

    Returns:
        PDF bytes or None on error
    """
    try:
        # Create PDF
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
        )

        # Build content
        story = []

        # Add certificate image
        try:
            cert_image = Image(certificate_image_path, width=7*inch, height=5*inch)
            story.append(cert_image)
            story.append(Spacer(1, 0.2*inch))
        except Exception as e:
            logger.warning(f"Error adding certificate image: {str(e)}")

        # Add QR code
        try:
            qr_image = Image(qr_code_path, width=1*inch, height=1*inch)
            story.append(qr_image)
            story.append(Spacer(1, 0.1*inch))
        except Exception as e:
            logger.warning(f"Error adding QR code: {str(e)}")

        # Add details
        styles = getSampleStyleSheet()
        story.append(Paragraph(f"Verification URL: {verification_url}", styles['Normal']))
        story.append(Paragraph(f"Generated: {certificate_details.get('created_at', '')}", styles['Normal']))

        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        return None
