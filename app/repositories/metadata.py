import logging
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
