import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import AnyHttpUrl

from ..dependencies.metadata import get_metadata_service, get_worker
from ....services import MetadataService
from ....models import (
    MetadataState,
    MetadataCreateRequest,
    MetadataResponse,
    MetadataPendingResponse,
)
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
    """
    Retrieves metadata for a given URL.

    If metadata is already available and completed, it returns the stored metadata immediately.
    If the metadata record exists but is pending or processing, it returns a 202 Accepted response.
    If the URL is not yet tracked, it creates a metadata record, schedules background collection,
    and returns a 202 Accepted response.

    Args:
        url (AnyHttpUrl): The URL to fetch metadata for. Must be a valid HTTP/HTTPS URL
            with a minimum length of 10 characters.
        servicer (MetadataService): The metadata service instance for retrieving and
            managing metadata operations.
        worker (MetadataWorker): The metadata worker instance for processing metadata
            collection tasks.
    Returns:
        MetadataResponse|JSONResponse: The metadata object when available, or a JSONResponse
            with a 202 Accepted status when metadata collection is pending, processing, or newly scheduled.
    Raises:
        HTTPException: A 500 Internal Server Error if an unexpected error occurs during
            metadata retrieval or processing.
    Status Codes:
        200: Metadata found and returned successfully.
        202: Metadata retrieval is pending, processing, or newly scheduled for collection.
        503: Metadata collection failed for the requested URL.
        500: Server encountered an unexpected error.
    Note:
        - Normalizes the input URL by removing trailing slashes for consistency.
    """
    _url = servicer.remove_trailing_slash_to_url(str(url))
    try:
        state, metadata = await servicer.get_metadata(_url)

        if state == MetadataState.FOUND and metadata: # metadata found in db, return it according to process_state
            process_state = metadata.get("process_state")
            if process_state in ["pending", "processing"]:
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    content={"message": "Metadata collection in progress."},
                )

            if process_state == "failed":
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"message": "Metadata collection failed."},
                )

            if process_state == "completed":
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
    """
    Create metadata for a given URL.

    Initiates the metadata creation process for a provided URL. 
    Validates the URL, checks for duplicates, and queues the metadata processing as an asyc background task if the URL is accepted.

    Args:
        input_json (MetadataCreateRequest): Request object containing the URL to create metadata for.
        servicer (MetadataService): Dependency-injected service for metadata operations.
        worker (MetadataWorker): Dependency-injected worker for background task processing.
    Returns:
        MetadataPendingResponse: Response object containing the normalized URL when metadata
            creation is accepted and queued for processing.
    Raises:
        HTTPException:
            - Status 409 CONFLICT: If the URL already exists in the system (DUPLICATE state).
            - Status 500 INTERNAL_SERVER_ERROR: If an unexpected error occurs during metadata creation.
    Note:
        - Normalizes the input URL by removing trailing slashes for consistency.
        - Triggers an asynchronous background task via MetadataWorker to process the URL metadata.
    """

    _url = servicer.remove_trailing_slash_to_url(str(input_json.url))
    try:
        state, metadata = await servicer.create_metadata(_url)
        if state == MetadataState.ACCEPTED and metadata:
            asyncio.create_task(worker.process(_url))  # trigger task
            return MetadataPendingResponse(url=_url)

        elif state == MetadataState.DUPLICATE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"url": _url, "message": "URL already exists."},
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to create metadata {_url}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
