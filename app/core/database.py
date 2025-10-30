"""
MongoDB connection and lifecycle management.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING
from typing import Optional
from .config import settings

logger = logging.getLogger(__name__)


class Database:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


db_instance = Database()


async def connect_to_mongo():
    """Connect to MongoDB and create indexes."""
    logger.info("Connecting to MongoDB...")
    try:
        db_instance.client = AsyncIOMotorClient(
            settings.DATABASE_URL,
            maxPoolSize=50,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000
        )
        db_instance.db = db_instance.client[settings.DATABASE_NAME]
        
        # Test connection
        await db_instance.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def create_indexes():
    """Create database indexes for optimized queries."""
    if db_instance.db is None:
        return
    
    # Users collection indexes
    await db_instance.db.users.create_index([("email", ASCENDING)], unique=True)
    await db_instance.db.users.create_index([("role", ASCENDING)])
    
    # Certificates collection indexes
    await db_instance.db.certificates.create_index([("certificate_hash", ASCENDING)], unique=True)
    await db_instance.db.certificates.create_index([("user_id", ASCENDING)])
    await db_instance.db.certificates.create_index([("issuer_id", ASCENDING)])
    await db_instance.db.certificates.create_index([("status", ASCENDING)])
    await db_instance.db.certificates.create_index([("created_at", ASCENDING)])
    
    # Verifications collection indexes
    await db_instance.db.verifications.create_index([("certificate_id", ASCENDING)])
    await db_instance.db.verifications.create_index([("verifier_id", ASCENDING)])
    await db_instance.db.verifications.create_index([("confidence_level", ASCENDING)])
    await db_instance.db.verifications.create_index([("manual_review_required", ASCENDING)])
    await db_instance.db.verifications.create_index([("created_at", ASCENDING)])
    
    # Institutions collection indexes
    await db_instance.db.institutions.create_index([("name", ASCENDING)], unique=True)
    await db_instance.db.institutions.create_index([("registration_number", ASCENDING)], unique=True)
    await db_instance.db.institutions.create_index([("is_verified", ASCENDING)])


async def close_mongo_connection():
    """Close MongoDB connection."""
    logger.info("Closing MongoDB connection...")
    if db_instance.client:
        db_instance.client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    if db_instance.db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return db_instance.db
