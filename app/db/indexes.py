from fastapi import FastAPI


async def create_indexes(app: FastAPI, collection_name: str) -> None:
    """Create indexes on startup."""
    db = app.state.mongo_database

    # Unique index for fast lookups
    await db[collection_name].create_index("url", unique=True)

    # TTL index for auto-cleanup (30 days)
    await db[collection_name].create_index("created_at", expireAfterSeconds=2592000)
