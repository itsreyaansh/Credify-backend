"""Database migration runner for Credify."""
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncClient
from datetime import datetime


async def get_current_version(db) -> int:
    """Get current schema version."""
    result = await db._schema_versions.find_one(
        {"status": "applied"},
        sort=[("version", -1)]
    )
    return result["version"] if result else 0


async def run_migrations(connection_string: str, target_version: int = None) -> None:
    """Run migrations up to target version."""
    client = AsyncClient(connection_string)
    db = client["credify"]

    current_version = await get_current_version(db)
    print(f"Current schema version: {current_version}")

    # Import all migration modules
    migration_modules = []
    versions_dir = os.path.join(os.path.dirname(__file__), "versions")

    if not os.path.exists(versions_dir):
        print("No migrations found")
        client.close()
        return

    for filename in sorted(os.listdir(versions_dir)):
        if filename.startswith("v") and filename.endswith(".py"):
            version = int(filename[1:4])
            if version > current_version:
                module_name = f"migrations.versions.{filename[:-3]}"
                try:
                    import importlib
                    module = importlib.import_module(module_name)
                    migration_modules.append((version, module))
                except ImportError as e:
                    print(f"Error importing migration v{version}: {e}")

    # Run migrations
    for version, module in migration_modules:
        if target_version and version > target_version:
            break

        print(f"\n→ Applying migration v{version:03d}...")
        try:
            await module.upgrade(db)
            print(f"✓ Migration v{version:03d} applied")
        except Exception as e:
            print(f"✗ Migration v{version:03d} failed: {str(e)}")
            raise

    client.close()
    print("\n✓ All migrations completed successfully")


async def rollback(connection_string: str, target_version: int) -> None:
    """Rollback to target version."""
    client = AsyncClient(connection_string)
    db = client["credify"]

    current_version = await get_current_version(db)
    print(f"Current schema version: {current_version}")
    print(f"Rolling back to version: {target_version}")

    # Rollback from current to target
    for version in range(current_version, target_version - 1, -1):
        try:
            module_name = f"migrations.versions.v{version:03d}_migration"
            import importlib
            module = importlib.import_module(module_name)
            print(f"\n→ Rolling back migration v{version:03d}...")
            await module.downgrade(db)
            print(f"✓ Migration v{version:03d} rolled back")
        except Exception as e:
            print(f"✗ Rollback failed: {str(e)}")
            raise

    client.close()
    print("\n✓ Rollback completed successfully")


async def get_status(connection_string: str) -> None:
    """Get current migration status."""
    client = AsyncClient(connection_string)
    db = client["credify"]

    current_version = await get_current_version(db)
    print(f"Current schema version: {current_version}")

    # Show migration history
    migrations = await db._schema_versions.find({}).sort("version", -1).to_list(None)
    if migrations:
        print("\nMigration history:")
        for mig in migrations:
            print(f"  v{mig['version']:03d}: {mig['name']} - {mig['status']}")

    client.close()


if __name__ == "__main__":
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    if len(sys.argv) < 2:
        print("Usage: python migrate.py [up|down|status] [target_version]")
        sys.exit(1)

    command = sys.argv[1]
    target_version = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if command == "up":
        asyncio.run(run_migrations(mongo_url, target_version))
    elif command == "down":
        if not target_version:
            print("Rollback requires target version")
            sys.exit(1)
        asyncio.run(rollback(mongo_url, target_version))
    elif command == "status":
        asyncio.run(get_status(mongo_url))
    else:
        print("Unknown command")
        sys.exit(1)
