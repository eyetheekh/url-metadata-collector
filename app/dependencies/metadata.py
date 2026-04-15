from fastapi import Request, Depends
from app.repositories import MetadataRepository
from app.core.config import get_settings
from app.services import MetadataService


def get_database(request: Request):
    return request.app.state.mongo_database


def get_worker(request: Request):
    return request.app.state.worker


def get_metadata_repository(db=Depends(get_database)):
    settings = get_settings()
    collection = db[settings.MONGODB_METADATA_COLLECTION_NAME]
    return MetadataRepository(collection)


def get_metadata_service(
    repo: MetadataRepository = Depends(get_metadata_repository),
) -> MetadataService:
    return MetadataService(repo)
