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
    """
    Singleton class responsible for processing metadata collection tasks asynchronously.
    This worker manages concurrent URL processing with duplicate prevention, handles job claiming from
    a repository, collects metadata using a collector, and updates the repository with results.

    Attributes:
        _instance (MetadataWorker): Singleton instance of the class.
        _processing_urls (Set[str]): Set of URLs currently being processed to prevent duplicates.
        _lock (asyncio.Lock): Async lock for thread-safe access to shared resources.
        repo (MetadataRepository): Repository instance for job management and persistence.
        collector (MetadataCollector): Collector instance for gathering metadata from URLs.
        _initialized (bool): Flag to ensure __init__ runs only once in singleton pattern.

    Methods:
        __new__(cls, *args, **kwargs) -> MetadataWorker:
            Implements singleton pattern, ensuring only one instance of MetadataWorker exists.
            Returns:
                MetadataWorker: The singleton instance.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MetadataWorker, cls).__new__(cls)
        return cls._instance

    def __init__(self, repo: MetadataRepository, collector: MetadataCollector):
        # initialize only once
        if not hasattr(self, "_initialized"):
            logger.info(f"MetadataWorker worker started: {str(uuid.uuid4())[:6]}")

            self._processing_urls: Set[str] = (
                set()
            )  # store currently processing urls to avoid duplicates
            self._lock = asyncio.Lock()

            self.repo = repo
            self.collector = collector

            self._initialized: bool = True

    async def process(self, url: str):
        """
        Processes a single URL asynchronously by claiming a job, collecting metadata,
        and updating the repository with results or failure status. Prevents duplicate
        processing of the same URL.

        Args:
            url (str): The URL to process.
        """
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
                logger.info(
                    f"Background collection task for: {url} got None as reponse."
                )
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
        """
        Processes jobs that have exceeded retry thresholds and time delays.
        Retrieves stale jobs from the repository and processes them sequentially.
        Raises:
            NotImplementedError: This method is not yet implemented.
        """
        # TODO process_stale_jobs
        # check db for process_count > threshold && timedelta > retry after
        # use self.process to pick task
        # yield & sleep
        raise NotImplementedError()


async def bind_worker(app: FastAPI, settings: Settings) -> None:
    db = app.state.mongo_database

    repo = MetadataRepository(db[settings.MONGODB_METADATA_COLLECTION_NAME])
    collector = MetadataCollector()

    app.state.worker = MetadataWorker(repo, collector)

    asyncio.create_task(app.state.worker.process_stale_jobs())
