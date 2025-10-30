"""Core module exports."""
from .config import settings, get_settings
from .database import (
    connect_to_mongo,
    close_mongo_connection,
    get_database
)
from .redis_client import (
    connect_to_redis,
    close_redis_connection,
    get_redis,
    RedisService
)
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    create_verification_token,
    create_password_reset_token
)
from .dependencies import (
    get_db,
    get_redis_client,
    get_current_user,
    get_current_user_optional,
    get_admin_user,
    get_issuer_user,
    get_verifier_user,
    require_role
)

__all__ = [
    "settings",
    "get_settings",
    "connect_to_mongo",
    "close_mongo_connection",
    "get_database",
    "connect_to_redis",
    "close_redis_connection",
    "get_redis",
    "RedisService",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "create_verification_token",
    "create_password_reset_token",
    "get_db",
    "get_redis_client",
    "get_current_user",
    "get_current_user_optional",
    "get_admin_user",
    "get_issuer_user",
    "get_verifier_user",
    "require_role"
]
