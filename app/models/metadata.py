from pydantic import BaseModel, Field, AnyHttpUrl, field_validator
from typing import Dict, Optional, Any
from datetime import datetime
from bson import ObjectId
from enum import Enum


class MetadataState(str, Enum):
    ACCEPTED = "accepted"
    CREATED = "created"
    DUPLICATE = "duplicate"
    FOUND = "found"
    NOT_FOUND = "not_found"


class MetadataCreateRequest(BaseModel):
    """Request model for creating metadata."""

    url: AnyHttpUrl = Field(..., description="URL to collect metadata from")

    class Config:
        json_schema_extra = {"example": {"url": "https://example.com"}}


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


class MetadataPendingResponse(BaseModel):
    """Response model for pending metadata collection."""

    url: str
    status: str = "pending"
    message: str = "Metadata collection initiated. Please retry shortly."


class MetadataDocument(BaseModel):
    """Internal document model for MongoDB storage."""

    class ProcessState(str, Enum):
        """track background task"""

        PENDING = "pending"
        PROCESSING = "processing"
        FAILED = "failed"
        COMPLETED = "completed"

    url: str
    headers: Optional[Dict[str, str]] = None
    cookies: Optional[Dict[str, str]] = None
    page_source: Optional[str] = None
    status_code: Optional[int] = None
    process_state: ProcessState = ProcessState.PENDING
    failure_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
