from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import AnyHttpUrl
from ....dependencies.metadata import get_metadata_service
from ....services import MetadataService
from ....models import MetadataCreateRequest, MetadataResponse

router: APIRouter = APIRouter(tags=["metadata"])


@router.get(
    "/url_metadata",
    status_code=status.HTTP_200_OK,
    summary="Retrieve metadata",
    description="Retrieve metadata for a URL. If not found, triggers background collection.",
    response_model=MetadataResponse,
)
async def get_url_metadata(
    url: AnyHttpUrl, servicer: MetadataService = Depends(get_metadata_service)
):
    try:
        metadata, status_code = await servicer.get_metadata(str(url))
        if metadata is None:
            raise HTTPException(status_code=status_code, detail="Metadata not found")
        return metadata
    except Exception as e:
        print(e)
        raise


@router.post(
    "/url_metadata",
    status_code=status.HTTP_201_CREATED,
    summary="Create metadata record",
    description="Collect and store metadata (headers, cookies, page source) for a given URL.",
    response_model=MetadataResponse,
)
async def create_url_metadata(
    url: MetadataCreateRequest, servicer: MetadataService = Depends(get_metadata_service)
):

    try:
        metadata, status_code = await servicer.create_metadata(str(url))
        if metadata is None:
            raise HTTPException(status_code=status_code, detail="Duplicate URL")
        return metadata
    except Exception as e:
        print(e)
        raise
