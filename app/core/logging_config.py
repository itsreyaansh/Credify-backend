"""Logging configuration for Credify."""
import logging
import logging.handlers
import os
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(__file__), '../../logs')
os.makedirs(logs_dir, exist_ok=True)

# Log file path
log_file = os.path.join(logs_dir, f'credify_{datetime.now().strftime("%Y%m%d")}.log')

# Logging format
log_format = (
    '[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s'
)

# Create logger
def setup_logging(level=logging.INFO):
    """Setup logging configuration."""
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return root_logger


# Application-specific loggers
auth_logger = logging.getLogger('credify.auth')
verification_logger = logging.getLogger('credify.verification')
fraud_logger = logging.getLogger('credify.fraud')
blockchain_logger = logging.getLogger('credify.blockchain')
database_logger = logging.getLogger('credify.database')
