import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import AnyHttpUrl

from ....dependencies.metadata import get_metadata_service, get_worker
from ....services import MetadataService
from ....models import MetadataState, MetadataCreateRequest, MetadataResponse, MetadataPendingResponse
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
    url: AnyHttpUrl = Query(..., min_length=10),
    servicer: MetadataService = Depends(get_metadata_service),
    worker: MetadataWorker = Depends(get_worker),
):
    _url = servicer.remove_trailing_slash_to_url(str(url))
    try:
        state, metadata = await servicer.get_metadata(_url)

        if state == MetadataState.FOUND and metadata:
            return metadata

        elif state == MetadataState.ACCEPTED:  # trigger background task with worker
            # wait for the object to be createad in db
            await servicer.create_metadata(_url)
            asyncio.create_task(worker.process(_url))  # trigger task

            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={"message": "URL scheduled for metadata collection."},
            )

    except Exception:
        logger.exception(f"Failed to retreive metadata {_url}")
        raise HTTPException(500, "Server Encountered an Unexpected Error.")


@router.post(
    "/url_metadata",
    status_code=status.HTTP_201_CREATED,
    summary="Create metadata record",
    description="Collect and store metadata (headers, cookies, page source) for a given URL.",
    response_model=MetadataPendingResponse,
)
async def create_url_metadata(
    input_json: MetadataCreateRequest,
    servicer: MetadataService = Depends(get_metadata_service),
    worker: MetadataWorker = Depends(get_worker),
):
    _url = servicer.remove_trailing_slash_to_url(str(input_json.url))
    try:
        state, metadata = await servicer.create_metadata(_url)
        if state == MetadataState.ACCEPTED and metadata:
            asyncio.create_task(worker.process(_url))  # trigger task
            return MetadataPendingResponse(url=_url)

        elif state == MetadataState.DUPLICATE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"url": _url, "message": "URL already exists"},
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to create metadata {_url}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
