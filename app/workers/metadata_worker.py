import logging
import uuid
import asyncio
from typing import Set
from fastapi import FastAPI

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

            self._processing_urls: Set[str] = set() # store currently processing urls to avoid duplicates
            self._lock = asyncio.Lock()

            self.repo = repo
            self.collector = collector

            self._initialized: bool = True

    async def process(self, url: str):

        async with self._lock:
            if url in self._processing_urls:
                logger.info(f"URL already being processed: {url}")
                return
            self._processing_urls.add(url)
            logger.info(f"Processing URL's: {self._processing_urls}")

        doc = await self.repo.claim_job(url)
        if doc is None:
            return
        logger.info(f"Enqueued background task for: {url}")

        try:
            data = await self.collector.collect(url)
            if data is None:
                logger.info(f"Background collection task for: {url} got None as reponse.")
                raise Exception("Collector returned None")

            await self.repo.mark_completed(url, data)
            logger.info(f"Background collection task for: {url} completed.")
        except Exception:
            await self.repo.mark_failed(url)
            logger.info(f"Background collection task for: {url} failed.")
        
        finally:
            async with self._lock:
                self._processing_urls.discard(url)

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
