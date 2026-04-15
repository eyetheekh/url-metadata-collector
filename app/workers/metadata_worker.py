import uuid
import logging
import asyncio
from fastapi import FastAPI
from datetime import datetime
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection

from ..core.config import Settings
from ..repositories import MetadataRepository
from ..services import MetadataCollector

logger = logging.getLogger(__name__)


class MetadataWorker:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MetadataWorker, cls).__new__(cls)
        return cls._instance

    def __init__(self, repo: MetadataRepository, collector: MetadataCollector):
        # initialize only once
        if not hasattr(self, "_initialized"):
            logger.info(f"MetadataWorker worker started: {str(uuid.uuid4())[:6]}")
            self.repo = repo
            self.collector = collector

            self._initialized: bool = True

    async def process(self, url: str):
        doc = await self.repo.claim_job(url)
        if doc is None:
            return

        try:
            data = await self.collector.collect(url)
            if data is None:
                raise Exception("Collector returned None")

            await self.repo.mark_completed(url, data)
        except Exception:
            await self.repo.mark_failed(url)

    async def __process(self, url):
        # skip if its already in process state
        # if not take task after checkiung process_count < thereshold
        # update task to processing
        # call url visitor to get page source
        # update the record with page source
        # update status to processed & timestamps

        # if failed
        # update process_count +1
        # update status to failed if process_count >= threshold & timestamps
        collection = self.db["url_metadata_collection"]

        # atomic claim
        doc = await collection.find_one_and_update(
            {"url": url, "process_state": "pending"},
            {"$set": {"process_state": "processing"}},
        )

        if doc is None:
            return  # already being processed

        try:
            data = await self.collector.collect(url)
            if data is None:
                raise Exception("Collector returned response as None.")

            await collection.update_one(
                {"url": url},
                {
                    "$set": {
                        **data,
                        "process_state": "completed",
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

        except Exception:
            await collection.update_one(
                {"url": url},
                {
                    "$set": {"process_state": "failed"},
                    "$inc": {"failure_count": 1},
                },
            )
            pass

    async def process_stale_jobs(self):
        # check db for process_count > threshold && timedelta > retry after
        # use self.process to pick task
        # yield & sleep
        pass


async def bind_worker(app: FastAPI, settings: Settings) -> None:
    db = app.state.mongo_database

    repo = MetadataRepository(db[settings.MONGODB_METADATA_COLLECTION_NAME])
    collector = MetadataCollector()

    app.state.worker = MetadataWorker(repo, collector)

    asyncio.create_task(app.state.worker.process_stale_jobs())
