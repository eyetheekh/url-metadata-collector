import logging
from datetime import datetime
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)


class MetadataRepository:
    """
    Repository for managing URL metadata in MongoDB.
    Handles db operations and process state management for URL metadata documents
    """

    def __init__(self, collection: AsyncCollection):
        self.collection = collection

    async def create_url_metadata(self, url_metadata: dict):
        """
        Create a new URL metadata document in the collection.
        Args:
            url_metadata (dict): Dictionary containing URL metadata to be inserted.
        Returns:
            ObjectId: The inserted document ID on success.
            None: If a DuplicateKeyError occurs (URL already exists).
        """

        try:
            result = await self.collection.insert_one(url_metadata)
        except DuplicateKeyError:
            logging.error(
                f"DuplicateKeyError. Skipping adding URL to collection. {url_metadata.get('url')}"
            )
            return None

        return result.inserted_id

    async def get_url_metadata(self, url: str) -> dict | None:
        """
        Retrieve URL metadata by URL.
        Args:
            url (str): The URL to search for.
        Returns:
            dict: The metadata document if found.
            None: If no metadata exists for the given URL.
        """
        url_metadata = await self.collection.find_one({"url": url})
        if not url_metadata:
            return None
        return url_metadata

    async def claim_job(self, url: str):
        """
        Claim a pending job by updating its state from 'pending' to 'processing'.
        Args:
            url (str): The URL of the job to claim.
        Returns:
            dict: The updated metadata document, or None if no pending job exists.
        """
        return await self.collection.find_one_and_update(
            {"url": url, "process_state": "pending"},
            {"$set": {"process_state": "processing"}},
        )

    async def mark_completed(self, url: str, data: dict):
        """
        Mark a URL processing job as completed and update metadata.
        Args:
            url (str): The URL of the job to mark as completed.
            data (dict): Additional data to update into the metadata document.
        """
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
        """
        Mark a URL processing job as failed and increment the failure counter.
        Args:
            url (str): The URL of the job to mark as failed.
        """
        await self.collection.update_one(
            {"url": url},
            {
                "$set": {"process_state": "failed"},
                "$inc": {"failure_count": 1},
            },
        )
