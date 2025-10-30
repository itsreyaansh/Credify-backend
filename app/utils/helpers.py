"""Helper utility functions."""
import uuid
from datetime import datetime


def generate_certificate_id() -> str:
    """Generate unique certificate ID."""
    return str(uuid.uuid4())


def generate_verification_id() -> str:
    """Generate unique verification ID."""
    return str(uuid.uuid4())


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.utcnow()


def format_timestamp(dt: datetime) -> str:
    """Format datetime as ISO string."""
    return dt.isoformat() if dt else None
