"""
Redis client for caching, rate limiting, and geo-clustering.
"""
import logging
import asyncio
from typing import Optional, List, Tuple
from redis.asyncio import Redis
from redis.exceptions import RedisError
from .config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    client: Optional[Redis] = None


redis_instance = RedisClient()


async def connect_to_redis():
    """Connect to Redis with connection pooling."""
    logger.info("Connecting to Redis...")
    try:
        redis_instance.client = await Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50
        )
        
        # Test connection
        await redis_instance.client.ping()
        logger.info("Successfully connected to Redis")
        
    except RedisError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def close_redis_connection():
    """Close Redis connection."""
    logger.info("Closing Redis connection...")
    if redis_instance.client:
        await redis_instance.client.close()
        logger.info("Redis connection closed")


def get_redis() -> Redis:
    """Get Redis instance."""
    if redis_instance.client is None:
        raise RuntimeError("Redis not initialized. Call connect_to_redis() first.")
    return redis_instance.client


class RedisService:
    """Redis service with common operations."""
    
    @staticmethod
    async def get(key: str) -> Optional[str]:
        """Get value by key."""
        redis = get_redis()
        try:
            return await redis.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    @staticmethod
    async def set(key: str, value: str, expire: Optional[int] = None):
        """Set key-value pair with optional expiration (seconds)."""
        redis = get_redis()
        try:
            await redis.set(key, value, ex=expire)
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
    
    @staticmethod
    async def incr(key: str, amount: int = 1) -> int:
        """Increment counter."""
        redis = get_redis()
        try:
            return await redis.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return 0
    
    @staticmethod
    async def expire(key: str, seconds: int):
        """Set expiration on key."""
        redis = get_redis()
        try:
            await redis.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
    
    @staticmethod
    async def geoadd(key: str, longitude: float, latitude: float, member: str):
        """Add geo location to sorted set."""
        redis = get_redis()
        try:
            await redis.geoadd(key, (longitude, latitude, member))
        except RedisError as e:
            logger.error(f"Redis GEOADD error: {e}")
    
    @staticmethod
    async def georadius(
        key: str,
        longitude: float,
        latitude: float,
        radius: float,
        unit: str = "km"
    ) -> List[str]:
        """Query locations within radius."""
        redis = get_redis()
        try:
            results = await redis.georadius(
                key,
                longitude,
                latitude,
                radius,
                unit=unit
            )
            return results if results else []
        except RedisError as e:
            logger.error(f"Redis GEORADIUS error: {e}")
            return []
    
    @staticmethod
    async def delete(key: str):
        """Delete key."""
        redis = get_redis()
        try:
            await redis.delete(key)
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
