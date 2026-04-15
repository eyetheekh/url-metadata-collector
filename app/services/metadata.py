import asyncio
from ..repositories import MetadataRepository
from ..models import MetadataState, MetadataDocument


class MetadataService:
    def __init__(self, repo: MetadataRepository):
        self.repo = repo

    async def get_metadata(self, url: str):
        record = await self.repo.get_url_metadata(url)
        if not record:
            return MetadataState.ACCEPTED, None

        return MetadataState.FOUND, record

    async def create_metadata(self, url: str):
        record = MetadataDocument(url=url).model_dump()
        _id = await self.repo.create_url_metadata(record)
        if _id is None:  # duplicate record
            return MetadataState.DUPLICATE, None

        return MetadataState.ACCEPTED, {"id": _id, **record}

    async def enque_background_task(self, url: str):
        # check if its already in processing
        pass

