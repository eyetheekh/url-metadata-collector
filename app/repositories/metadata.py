import logging
from datetime import datetime
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)


class MetadataRepository:
    def __init__(self, collection: AsyncCollection):
        self.collection = collection

    async def create_url_metadata(self, url_metadata: dict):
        try:
            result = await self.collection.insert_one(url_metadata)
        except DuplicateKeyError:
            logging.error(f"DuplicateKeyError {url_metadata.get('url')}")
            return None

        return result.inserted_id

    async def get_url_metadata(self, url: str) -> dict | None:
        url_metadata = await self.collection.find_one({"url": url})
        if not url_metadata:
            return None
        return url_metadata

    async def claim_job(self, url: str):
        return await self.collection.find_one_and_update(
            {"url": url, "process_state": "pending"},
            {"$set": {"process_state": "processing"}},
        )

    async def mark_completed(self, url: str, data: dict):
        await self.collection.update_one(
            {"url": url},
            {
                "$set": {
                    **data,
                    "process_state": "completed",
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    async def mark_failed(self, url: str):
        await self.collection.update_one(
            {"url": url},
            {
                "$set": {"process_state": "failed"},
                "$inc": {"failure_count": 1},
            },
        )
