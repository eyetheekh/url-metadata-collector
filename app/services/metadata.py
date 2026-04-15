from datetime import datetime
from app.repositories import MetadataRepository


class MetadataService:
    def __init__(self, repo: MetadataRepository):
        self.repo = repo

    async def get_metadata(self, url: str):
        record = await self.repo.get_url_metadata(url)
        if not record:
            # trigger background worker
            return None, 404
        return record, 200

    async def create_metadata(self, url: str):
        timestamp = datetime.now()
        url_object = {
            "url": url,
            "headers": None,
            "cookies": None,
            "status_code": None,
            "status": "pending",
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        _id = await self.repo.create_url_metadata(url_object)
        if _id is None:
            return None, 208
        
        return {"id": _id, **url_object}, 200
