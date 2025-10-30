"""Helper utility functions."""
import uuid
import re
from datetime import datetime
from bson import ObjectId


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


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> bool:
    """
    Validate password strength.
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",<>.?/\\|`~]', password):
        return False
    return True


def validate_mongodb_id(id_string: str) -> bool:
    """Validate MongoDB ObjectId."""
    try:
        ObjectId(id_string)
        return True
    except:
        return False


def sanitize_string(text: str) -> str:
    """Sanitize string input."""
    if not text:
        return ''
    # Remove leading/trailing whitespace
    text = text.strip()
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def convert_to_dict(obj):
    """Convert object to dictionary."""
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    elif hasattr(obj, 'dict'):
        return obj.dict()
    return obj


def paginate(items: list, page: int = 1, page_size: int = 10) -> dict:
    """Paginate list of items."""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        'items': items[start:end],
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
    }
