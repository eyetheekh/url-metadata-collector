import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import AnyHttpUrl
from ....dependencies.metadata import get_metadata_service, get_worker
from ....services import MetadataService
from ....models import MetadataState, MetadataCreateRequest, MetadataResponse
from ....workers import MetadataWorker

logger = logging.getLogger(__name__)


router: APIRouter = APIRouter(tags=["metadata"])


@router.get(
    "/url_metadata",
    status_code=status.HTTP_200_OK,
    summary="Retrieve metadata",
    description="Retrieve metadata for a URL. If not found, triggers background collection.",
    response_model=MetadataResponse,
)
async def get_url_metadata(
    url: AnyHttpUrl,
    servicer: MetadataService = Depends(get_metadata_service),
    worker: MetadataWorker = Depends(get_worker),
):
    try:
        state, metadata = await servicer.get_metadata(str(url))

        if state == MetadataState.FOUND and metadata:
            return metadata

        elif state == MetadataState.ACCEPTED and not metadata:
            # trigger background task with worker
            asyncio.create_task(worker.process(str(url)))

            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content="URL Scheduled for Metadata Collection.",
            )

    except Exception:
        logger.exception("Failed to retreive metadata")
        raise HTTPException(500, "Server Encountered an Unexpected Error.")


@router.post(
    "/url_metadata",
    status_code=status.HTTP_201_CREATED,
    summary="Create metadata record",
    description="Collect and store metadata (headers, cookies, page source) for a given URL.",
    response_model=MetadataResponse,
)
async def create_url_metadata(
    input_json: MetadataCreateRequest,
    servicer: MetadataService = Depends(get_metadata_service),
    worker: MetadataWorker = Depends(get_worker),
):
    try:
        state, metadata = await servicer.create_metadata(str(input_json.url))
        if state == MetadataState.ACCEPTED and metadata:
            res = await worker.process(str(input_json.url))
            return res

        elif state == MetadataState.DUPLICATE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"url": str(input_json.url), "message": "URL already exists"},
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create metadata")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
