import uuid
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)


class MetadataWorker:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MetadataWorker, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # initialize only once
        if not hasattr(self, "_initialized"):
            logger.info(f"MetadataWorker worker started: {str(uuid.uuid4())[:6]}")
            self._initialized = True

    async def process(self, url):
        # skip if its already in process state
        # if not take task after checkiung process_count < thereshold
        # update task to processing
        # call url visitor to get page source
        # update the record with page source
        # update status to processed & timestamps

        # if failed
        # update process_count +1
        # update status to failed if process_count >= threshold & timestamps

        pass

    async def process_stale_jobs(self):
        # check db for process_count > threshold && timedelta > retry after
        # use self.process to pick task
        # yield & sleep
        pass


async def bind_worker(app: FastAPI) -> None:
    app.state.worker = MetadataWorker()
    await app.state.worker.process_stale_jobs()
