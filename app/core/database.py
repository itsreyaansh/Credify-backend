"""MongoDB database connection and initialization."""
from motor.motor_asyncio import AsyncClient, AsyncDatabase
from pymongo import ASCENDING, DESCENDING
import logging
from contextlib import asynccontextmanager
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None
_db: AsyncDatabase | None = None


async def connect_db() -> None:
    """Connect to MongoDB and create indexes."""
    global _client, _db
    settings = get_settings()

    try:
        _client = AsyncClient(settings.MONGODB_URL)
        _db = _client[settings.MONGODB_DB]

        # Verify connection
        await _client.admin.command("ping")
        logger.info("Connected to MongoDB successfully")

        # Create indexes
        await create_indexes()
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise


async def disconnect_db() -> None:
    """Disconnect from MongoDB."""
    global _client
    if _client:
        _client.close()
        logger.info("Disconnected from MongoDB")


async def create_indexes() -> None:
    """Create all required indexes in MongoDB collections."""
    if not _db:
        return

    try:
        # Users collection indexes
        users_col = _db["users"]
        await users_col.create_index("email", unique=True)
        await users_col.create_index("institution_id")
        await users_col.create_index("is_active")
        await users_col.create_index("created_at")

        # Certificates collection indexes
        certs_col = _db["certificates"]
        await certs_col.create_index("certificate_id", unique=True)
        await certs_col.create_index("issuer_id")
        await certs_col.create_index("student_id")
        await certs_col.create_index("institution_id")
        await certs_col.create_index("is_revoked")
        await certs_col.create_index("created_at")
        await certs_col.create_index("holder_name")

        # Verifications collection indexes
        verif_col = _db["verifications"]
        await verif_col.create_index("verification_id", unique=True)
        await verif_col.create_index("certificate_id")
        await verif_col.create_index("created_at")
        await verif_col.create_index("confidence_score")

        # Institutions collection indexes
        inst_col = _db["institutions"]
        await inst_col.create_index("name", unique=True)
        await inst_col.create_index("code", unique=True)
        await inst_col.create_index("email_domain")

        # Fraud Incidents collection indexes
        fraud_col = _db["fraud_incidents"]
        await fraud_col.create_index("certificate_id")
        await fraud_col.create_index("created_at")
        await fraud_col.create_index("ip_address")
        await fraud_col.create_index([("geolocation.latitude", ASCENDING), ("geolocation.longitude", ASCENDING)])

        logger.info("Indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        raise


def get_db() -> AsyncDatabase:
    """Get the MongoDB database connection."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _db


def get_client() -> AsyncClient:
    """Get the MongoDB client."""
    if _client is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _client


@asynccontextmanager
async def get_db_context():
    """Context manager for database operations."""
    db = get_db()
    try:
        yield db
    finally:
        pass  # Motor handles connection pooling


async def drop_db():
    """Drop the entire database (for testing/cleanup)."""
    if _client and _db:
        await _client.drop_database(get_settings().MONGODB_DB)
        logger.warning("Database dropped")
