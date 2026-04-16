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

    def __init__(
        self,
        repo: MetadataRepository,
        collector: MetadataCollector,
        stale_jobs_max_retries: int = 3,
        stale_jobs_max_limit: int = 10,
        stale_jobs_retry_delay: int = 10,
        stale_jobs_pickup_delay: int = 60,
    ):
        # initialize only once
        if not hasattr(self, "_initialized"):
            logger.info(f"MetadataWorker worker started: {str(uuid.uuid4())[:6]}")

            self._processing_urls: Set[str] = (
                set()
            )  # store currently processing urls to avoid duplicates
            self._lock = asyncio.Lock()

            self.repo = repo
            self.collector = collector
            self.stale_jobs_max_retries = stale_jobs_max_retries
            self.stale_jobs_max_limit = stale_jobs_max_limit
            self.stale_jobs_retry_delay = stale_jobs_retry_delay
            self.stale_jobs_pickup_delay = stale_jobs_pickup_delay

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
        Background loop to retry failed jobs.
        """

        logger.info("Starting stale job retry loop...")
        while True:
            try:
                jobs = await self.repo.claim_stale_jobs(
                    max_retries=self.stale_jobs_max_retries,
                    retry_delay_seconds=self.stale_jobs_retry_delay,
                    limit=self.stale_jobs_max_limit,
                )
                if jobs:
                    logger.info(f"Retrying {len(jobs)} failed jobs")

                    for job in jobs:
                        url = job["url"]
                        asyncio.create_task(self.process(url))
                else:
                    logger.info(
                        f"No Stale job to retry. Sleeping for {self.stale_jobs_pickup_delay} seconds."
                    )

            except Exception as e:
                logger.exception(f"Error in stale job processor: {e}")

            await asyncio.sleep(self.stale_jobs_pickup_delay)


async def bind_worker(app: FastAPI, settings: Settings) -> None:
    db = app.state.mongo_database

    repo = MetadataRepository(db[settings.MONGODB_METADATA_COLLECTION_NAME])
    collector = MetadataCollector()

    app.state.worker = MetadataWorker(
        repo=repo,
        collector=collector,
        stale_jobs_pickup_delay=settings.STALE_JOBS_PICKUP_DELAY,
        stale_jobs_retry_delay=settings.STALE_JOBS_RETRY_DELAY,
        stale_jobs_max_limit=settings.STALE_JOBS_MAX_LIMIT,
        stale_jobs_max_retries=settings.STALE_JOBS_MAX_RETRIES,
    )

    if settings.STALE_JOBS_RETRY_WORKER:
        logging.info("BACKGROUND_WORKER_RETRY Enabled.")
        asyncio.create_task(app.state.worker.process_stale_jobs())
    else:
        logging.warning(
            "BACKGROUND_WORKER_RETRY Disabled. Failed jobs will not be retried."
        )
