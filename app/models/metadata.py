from enum import Enum
from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, AnyHttpUrl


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
    headers: Optional[Dict[str, str]] = None
    cookies: Optional[Dict[str, str]] = None
    page_source: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "headers": {"content-type": "text/html", "server": "nginx"},
                "cookies": {"sessionid": "abc123xyz"},
                "page_source": "<html><body>Hello World</body></html>",
            }
        },
    }


class MetadataPendingResponse(BaseModel):
    """Response model for pending metadata collection."""

    url: str
    message: str = "URL scheduled for metadata collection."
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "url": "https://example.com",
                "message" : "URL scheduled for metadata collection."
            }
        },
    }

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
