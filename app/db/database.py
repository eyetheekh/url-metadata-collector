from fastapi import FastAPI
from pymongo import AsyncMongoClient

from ..core import Settings


async def init_db(app: FastAPI, settings: Settings) -> None:
    client = AsyncMongoClient(
        settings.MONGODB_URL,
        maxPoolSize=settings.MONGODB_MAXPOOL_SIZE,
        minPoolSize=settings.MONGODB_MINPOOL_SIZE,
    )
    db = client[settings.MONGODB_DB_NAME]
    await db.command("ping")
    app.state.mongo_client = client
    app.state.mongo_database = db


async def close_client(app: FastAPI) -> None:
    await app.state.mongo_client.close()
