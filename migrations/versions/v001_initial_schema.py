"""Migration: Initial schema creation.

Version: 001
Date: 2025-01-01
Description: Create initial collections and indexes
"""

from datetime import datetime


async def upgrade(db):
    """Apply the migration."""
    print("Applying migration v001: Initial schema creation")

    # Create collections
    collections = ["users", "certificates", "verifications", "institutions", "fraud_incidents", "audit_logs"]
    for collection_name in collections:
        if collection_name not in await db.list_collection_names():
            await db.create_collection(collection_name)
            print(f"  ✓ Created collection: {collection_name}")

    # Create indexes for users
    users_col = db["users"]
    await users_col.create_index("email", unique=True)
    await users_col.create_index("institution_id")
    await users_col.create_index("is_active")
    print("  ✓ Created indexes for users")

    # Create indexes for certificates
    certificates_col = db["certificates"]
    await certificates_col.create_index("certificate_id", unique=True)
    await certificates_col.create_index("issuer_id")
    await certificates_col.create_index("student_id")
    await certificates_col.create_index("created_at")
    print("  ✓ Created indexes for certificates")

    # Create indexes for verifications
    verifications_col = db["verifications"]
    await verifications_col.create_index("verification_id", unique=True)
    await verifications_col.create_index("certificate_id")
    await verifications_col.create_index("created_at")
    print("  ✓ Created indexes for verifications")

    # Create indexes for institutions
    institutions_col = db["institutions"]
    await institutions_col.create_index("code", unique=True)
    await institutions_col.create_index("email_domain")
    print("  ✓ Created indexes for institutions")

    # Create indexes for audit_logs with TTL (90 days)
    audit_col = db["audit_logs"]
    await audit_col.create_index("timestamp")
    await audit_col.create_index("user_id")
    await audit_col.create_index("action")
    await audit_col.create_index("timestamp", expireAfterSeconds=7776000)
    print("  ✓ Created indexes for audit_logs with TTL")

    # Record schema version
    await db._schema_versions.insert_one({
        "version": 1,
        "name": "Initial schema",
        "timestamp": datetime.utcnow(),
        "applied_at": datetime.utcnow(),
        "status": "applied",
        "description": "Create initial collections and indexes"
    })

    print("✓ Migration v001 applied successfully")


async def downgrade(db):
    """Rollback the migration."""
    print("Rolling back migration v001")

    # Drop collections
    collections = ["users", "certificates", "verifications", "institutions", "fraud_incidents", "audit_logs"]
    for collection_name in collections:
        try:
            await db.drop_collection(collection_name)
            print(f"  ✓ Dropped collection: {collection_name}")
        except Exception as e:
            print(f"  ! Collection {collection_name} not found: {e}")

    # Update schema version
    await db._schema_versions.update_one(
        {"version": 1},
        {"$set": {"status": "rollback", "rolled_back_at": datetime.utcnow()}}
    )

    print("✓ Migration v001 rolled back successfully")
