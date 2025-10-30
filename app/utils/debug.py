"""
Debugging utilities for Credify application.

This module provides helpful debugging tools and utilities for development.
Use these utilities to understand application behavior and troubleshoot issues.

Example:
    >>> from app.utils.debug import log_request_info, format_error
    >>> log_request_info(request)
    >>> print(format_error(error))
"""

import logging
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def format_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        str: ISO formatted timestamp
    """
    return datetime.utcnow().isoformat()


def log_request_info(
    request: Request,
    user_id: Optional[str] = None,
    include_body: bool = False
) -> None:
    """
    Log detailed request information.

    Args:
        request: FastAPI Request object
        user_id: Optional user ID for tracking
        include_body: Whether to log request body (careful with sensitive data)

    Example:
        >>> from fastapi import Request
        >>> log_request_info(request, user_id="507f1f77bcf86cd799439011")
    """
    logger.debug(
        f"Request: {request.method} {request.url.path} | "
        f"IP: {request.client.host if request.client else 'unknown'} | "
        f"User: {user_id or 'anonymous'}"
    )

    # Log query parameters
    if request.query_params:
        logger.debug(f"Query params: {dict(request.query_params)}")

    # Log headers (excluding sensitive ones)
    sensitive_headers = {'authorization', 'cookie', 'x-api-key', 'password'}
    safe_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in sensitive_headers
    }
    if safe_headers:
        logger.debug(f"Headers: {dict(safe_headers)}")


def log_response_info(
    status_code: int,
    response_time_ms: float,
    user_id: Optional[str] = None
) -> None:
    """
    Log response information.

    Args:
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        user_id: Optional user ID

    Example:
        >>> import time
        >>> start = time.time()
        >>> # ... do work ...
        >>> elapsed = (time.time() - start) * 1000
        >>> log_response_info(200, elapsed, user_id="507f1f77bcf86cd799439011")
    """
    log_level = logging.WARNING if status_code >= 400 else logging.DEBUG

    logger.log(
        log_level,
        f"Response: {status_code} | "
        f"Time: {response_time_ms:.2f}ms | "
        f"User: {user_id or 'anonymous'}"
    )


def format_error(
    error: Exception,
    include_traceback: bool = True
) -> Dict[str, Any]:
    """
    Format exception into readable error information.

    Args:
        error: Exception to format
        include_traceback: Whether to include full traceback

    Returns:
        dict: Formatted error information

    Example:
        >>> try:
        ...     1 / 0
        ... except ZeroDivisionError as e:
        ...     error_info = format_error(e)
        ...     print(error_info)
    """
    error_dict = {
        "error_type": type(error).__name__,
        "message": str(error),
        "timestamp": format_timestamp(),
    }

    if include_traceback:
        error_dict["traceback"] = traceback.format_exc()

    return error_dict


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
) -> None:
    """
    Log exception with context information.

    Args:
        error: Exception to log
        context: Optional context dictionary
        user_id: Optional user ID

    Example:
        >>> try:
        ...     db.users.insert_one(user_data)
        ... except Exception as e:
        ...     log_error(
        ...         e,
        ...         context={"operation": "user_insert"},
        ...         user_id="507f1f77bcf86cd799439011"
        ...     )
    """
    error_info = format_error(error)

    log_message = f"Error: {error_info['error_type']} - {error_info['message']}"

    if context:
        log_message += f" | Context: {json.dumps(context)}"

    if user_id:
        log_message += f" | User: {user_id}"

    logger.error(log_message)
    logger.debug(f"Full traceback: {error_info.get('traceback', 'N/A')}")


def debug_pydantic_model(model: BaseModel, title: str = "Model") -> None:
    """
    Debug print a Pydantic model.

    Args:
        model: Pydantic model to debug
        title: Title for debug output

    Example:
        >>> user = UserCreate(email="test@example.com", ...)
        >>> debug_pydantic_model(user, "New User")
    """
    logger.debug(f"=== {title} ===")
    logger.debug(json.dumps(model.model_dump(), indent=2, default=str))


def debug_dict(data: Dict[str, Any], title: str = "Data") -> None:
    """
    Debug print a dictionary.

    Args:
        data: Dictionary to print
        title: Title for debug output

    Example:
        >>> user_data = {"email": "test@example.com", "name": "John"}
        >>> debug_dict(user_data, "User Data")
    """
    logger.debug(f"=== {title} ===")
    logger.debug(json.dumps(data, indent=2, default=str))


def get_health_check_report() -> Dict[str, Any]:
    """
    Generate a health check report for debugging.

    Returns:
        dict: Health check information

    Example:
        >>> report = get_health_check_report()
        >>> print(json.dumps(report, indent=2))
    """
    import os
    import sys

    report = {
        "timestamp": format_timestamp(),
        "python_version": sys.version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_mode": os.getenv("DEBUG", "False") == "True",
    }

    return report


def profile_function(func):
    """
    Decorator to profile a function's execution time.

    Args:
        func: Function to profile

    Returns:
        Decorated function

    Example:
        >>> @profile_function
        ... def my_function():
        ...     # Do work
        ...     pass
    """
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        result = func(*args, **kwargs)

        elapsed_time = (time.time() - start_time) * 1000

        logger.debug(
            f"Function '{func.__name__}' took {elapsed_time:.2f}ms"
        )

        return result

    return wrapper


def validate_env_variables(required_vars: list) -> bool:
    """
    Validate that required environment variables are set.

    Args:
        required_vars: List of required variable names

    Returns:
        bool: True if all required variables are set

    Raises:
        ValueError: If any required variables are missing

    Example:
        >>> validate_env_variables(["MONGODB_URL", "JWT_SECRET"])
    """
    import os

    missing = []

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.debug(f"All required environment variables are set: {required_vars}")
    return True


def create_debug_snapshot() -> Dict[str, Any]:
    """
    Create a comprehensive debug snapshot of the application state.

    Returns:
        dict: Application state snapshot

    Example:
        >>> snapshot = create_debug_snapshot()
        >>> with open("debug_snapshot.json", "w") as f:
        ...     json.dump(snapshot, f, indent=2, default=str)
    """
    import psutil
    import os

    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent(interval=0.1)

        snapshot = {
            "timestamp": format_timestamp(),
            "system": {
                "python_version": __import__('sys').version,
                "platform": __import__('platform').platform(),
                "pid": os.getpid(),
            },
            "process": {
                "memory_mb": memory_info.rss / 1024 / 1024,
                "cpu_percent": cpu_percent,
                "num_threads": process.num_threads(),
            },
            "environment": {
                "debug": os.getenv("DEBUG"),
                "environment": os.getenv("ENVIRONMENT"),
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
            }
        }

        return snapshot

    except Exception as e:
        logger.error(f"Failed to create debug snapshot: {str(e)}")
        return {"error": str(e)}


class DebugMiddleware:
    """
    Middleware for debugging requests and responses.

    Can be added to FastAPI app:
        app.add_middleware(DebugMiddleware)
    """

    def __init__(self, app):
        """Initialize middleware."""
        self.app = app

    async def __call__(self, request: Request, call_next):
        """Process request and response."""
        import time

        # Log request
        start_time = time.time()
        log_request_info(request, include_body=False)

        # Process request
        response = await call_next(request)

        # Log response
        elapsed_time = (time.time() - start_time) * 1000
        log_response_info(response.status_code, elapsed_time)

        return response
