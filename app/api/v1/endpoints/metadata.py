from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import AnyHttpUrl
from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime
from bson import ObjectId
from ....dependencies.metadata import get_metadata_service
from app.services import MetadataService
from pydantic import field_validator

router: APIRouter = APIRouter(tags=["metadata"])


# class MetadataResponse(BaseModel):
#     """Response model for metadata retrieval."""

#     id: Optional[str] = Field(None, alias="_id")
#     url: str

#     headers: Optional[Dict[str, str]] = None
#     cookies: Optional[Dict[str, str]] = None
#     page_source: Optional[str] = None
#     status_code: Optional[int] = None

#     created_at: datetime
#     updated_at: datetime

#     @field_validator("id", mode="before")
#     @classmethod
#     def convert_objectid(cls, v):
#         if v is None:
#             return v
#         return str(v)

#     class Config:
#         populate_by_name = True
#         model_config = {
#             "populate_by_name": True,
#             "json_schema_extra": {
#                 "example": {
#                     "url": "http://example.com",
#                     "headers": {},
#                     "cookies": {},
#                     "page_source": "<html>...</html>",
#                     "status_code": 200,
#                     "created_at": "2026-01-01T00:00:00",
#                     "updated_at": "2026-01-01T00:00:00",
#                 }
#             },
#         }

from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional
from datetime import datetime
from bson import ObjectId


class MetadataResponse(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    url: str

    headers: Optional[Dict[str, str]] = None
    cookies: Optional[Dict[str, str]] = None
    page_source: Optional[str] = None
    status_code: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_objectid(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "661f8c9a5f1b2c001234abcd",
                "url": "https://example.com",
                "headers": {"content-type": "text/html", "server": "nginx"},
                "cookies": {"sessionid": "abc123xyz"},
                "page_source": "<html><body>Hello World</body></html>",
                "status_code": 200,
                "created_at": "2026-04-15T16:13:19.490Z",
                "updated_at": "2026-04-15T16:13:19.490Z",
            }
        },
    }


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
    url: AnyHttpUrl, servicer: MetadataService = Depends(get_metadata_service)
):

    try:
        metadata, status_code = await servicer.create_metadata(str(url))
        if metadata is None:
            raise HTTPException(status_code=status_code, detail="Duplicate URL")
        return metadata
    except Exception as e:
        print(e)
        raise
