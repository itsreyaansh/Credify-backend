"""Redis client for caching and sessions."""
import redis.asyncio as redis
from redis.asyncio import Redis
import logging
from app.core.config import get_settings
import json
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def connect_redis() -> None:
    """Connect to Redis."""
    global _redis
    settings = get_settings()

    try:
        _redis = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
            socket_connect_timeout=5,
        )

        # Test connection
        await _redis.ping()
        logger.info("Connected to Redis successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise


async def disconnect_redis() -> None:
    """Disconnect from Redis."""
    global _redis
    if _redis:
        await _redis.close()
        logger.info("Disconnected from Redis")


def get_redis() -> Redis:
    """Get the Redis client."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call connect_redis() first.")
    return _redis


async def set_cache(key: str, value: Any, expire: int = 3600) -> None:
    """Set a value in cache with optional expiry."""
    redis_client = get_redis()
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await redis_client.setex(key, expire, str(value))
    except Exception as e:
        logger.error(f"Error setting cache key {key}: {str(e)}")


async def get_cache(key: str) -> Optional[Any]:
    """Get a value from cache."""
    redis_client = get_redis()
    try:
        value = await redis_client.get(key)
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return None
    except Exception as e:
        logger.error(f"Error getting cache key {key}: {str(e)}")
        return None


async def delete_cache(key: str) -> None:
    """Delete a cache key."""
    redis_client = get_redis()
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Error deleting cache key {key}: {str(e)}")


async def clear_cache_pattern(pattern: str) -> None:
    """Clear all keys matching a pattern."""
    redis_client = get_redis()
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
    except Exception as e:
        logger.error(f"Error clearing cache pattern {pattern}: {str(e)}")


async def add_token_to_blacklist(token: str, expire_in_seconds: int) -> None:
    """Add a token to the blacklist."""
    redis_client = get_redis()
    try:
        await redis_client.setex(f"blacklist:{token}", expire_in_seconds, "1")
    except Exception as e:
        logger.error(f"Error adding token to blacklist: {str(e)}")


async def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted."""
    redis_client = get_redis()
    try:
        return await redis_client.exists(f"blacklist:{token}") == 1
    except Exception as e:
        logger.error(f"Error checking token blacklist: {str(e)}")
        return False


async def increment_request_count(ip_address: str, expire: int = 3600) -> int:
    """Increment request count for rate limiting."""
    redis_client = get_redis()
    try:
        key = f"rate_limit:{ip_address}"
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, expire)
        return count
    except Exception as e:
        logger.error(f"Error incrementing request count: {str(e)}")
        return 0


async def add_geo_fraud_cluster(lat: float, lon: float, ip: str, expire: int = 86400) -> None:
    """Add IP to geo-fraud cluster."""
    redis_client = get_redis()
    try:
        grid_size = 0.5  # 0.5 degree grid cells
        grid_lat = int(lat / grid_size)
        grid_lon = int(lon / grid_size)
        key = f"geo_clusters:{grid_lat}:{grid_lon}"

        # Add to set and update metadata
        await redis_client.sadd(f"{key}:ips", ip)
        await redis_client.incr(f"{key}:count")
        await redis_client.expire(f"{key}:ips", expire)
        await redis_client.expire(f"{key}:count", expire)
    except Exception as e:
        logger.error(f"Error adding to geo cluster: {str(e)}")


async def get_geo_cluster_count(lat: float, lon: float) -> int:
    """Get count of IPs in a geo cluster."""
    redis_client = get_redis()
    try:
        grid_size = 0.5
        grid_lat = int(lat / grid_size)
        grid_lon = int(lon / grid_size)
        key = f"geo_clusters:{grid_lat}:{grid_lon}"

        count = await redis_client.get(f"{key}:count")
        return int(count) if count else 0
    except Exception as e:
        logger.error(f"Error getting geo cluster count: {str(e)}")
        return 0


async def is_ip_blacklisted(ip: str) -> bool:
    """Check if an IP is blacklisted for fraud."""
    redis_client = get_redis()
    try:
        return await redis_client.exists(f"fraud_ip_blacklist:{ip}") == 1
    except Exception as e:
        logger.error(f"Error checking IP blacklist: {str(e)}")
        return False


async def add_ip_to_blacklist(ip: str, expire: int = 604800) -> None:
    """Add IP to fraud blacklist (7 days default)."""
    redis_client = get_redis()
    try:
        await redis_client.setex(f"fraud_ip_blacklist:{ip}", expire, "1")
    except Exception as e:
        logger.error(f"Error adding IP to blacklist: {str(e)}")
